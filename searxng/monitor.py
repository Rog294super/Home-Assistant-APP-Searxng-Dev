#!/usr/bin/env python3
"""
SearXNG Home Assistant Entity Monitor
Monitors SearXNG stats and registers them as Home Assistant entities
"""

import json
import logging
import os
import signal
import sys
from threading import Event
import time
import urllib.request
import urllib.error
import base64
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("searxng-monitor")


class SearXNGMonitor:
    """Monitor SearXNG stats and expose them through MQTT Discovery."""

    update_interval = 60

    def __init__(self, options_file: str):
        self.options_file = options_file
        self.options = self._load_options()
        self.stop_event = Event()
        self.mqtt_client = None
        self.mqtt_connected = False
        self.metrics_enabled = self.options.get("enable_metrics", True)
        
        # Check if entity registration is enabled
        self.enabled = self.options.get("enable_stats_entities", True)
        if not self.enabled:
            logger.info("Entity registration is disabled in config")
            return
        
        self.port = self.options.get("port", 18080)
        self.instance_name = self.options.get("instance_name", "SearXNG")
        self.metrics_password = self._get_metrics_password()
        self.mqtt_enabled = self.options.get("enable_mqtt_discovery", True)
        self.discovery_prefix = self.options.get("mqtt_discovery_prefix", "homeassistant")
        self.mqtt_base_topic = self.options.get("mqtt_base_topic", "searxng").strip("/")
        self._published_engines: Set[str] = self._load_published_engines()
        self._last_stats: Optional[Dict[str, Any]] = None
        
        logger.info(f"Initialized SearXNG Monitor for {self.instance_name}")
        if self.mqtt_enabled:
            mqtt_service = self._get_mqtt_service_config()
            if mqtt_service:
                self._connect_mqtt(mqtt_service)
            else:
                self.mqtt_enabled = False
        logger.info(f"Update interval: {self.update_interval}s")

    def _load_options(self) -> Dict[str, Any]:
        """Load options from JSON file"""
        try:
            with open(self.options_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load options: {e}")
            return {}

    def _get_metrics_password(self) -> str:
        """Read the metrics password shared with the SearXNG server."""
        try:
            with open("/data/generated_metrics_secret", "r") as secret_file:
                return secret_file.read().strip()
        except OSError:
            return ""

    def _get_mqtt_service_config(self) -> Optional[Dict[str, Any]]:
        """Fetch MQTT connection details from Supervisor without exporting them."""
        token = os.environ.get("SUPERVISOR_TOKEN", "")
        if not token:
            logger.error("Cannot query Supervisor MQTT service: token is missing")
            return None

        for attempt in range(1, 13):
            request = urllib.request.Request(
                "http://supervisor/services/mqtt",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Supervisor-Token": token,
                    "Accept": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    service = json.loads(response.read().decode("utf-8"))
                    service = service.get("data", service)
                    if isinstance(service, dict) and service.get("host"):
                        logger.info("Loaded MQTT service configuration from Supervisor")
                        return service
                    raise ValueError("Supervisor returned no MQTT host")
            except (
                OSError,
                urllib.error.URLError,
                json.JSONDecodeError,
                ValueError,
            ) as error:
                logger.warning(
                    "Could not load MQTT service configuration "
                    f"({attempt}/12): {error}"
                )
                if attempt < 12:
                    time.sleep(5)
        return None

    def _get_stats(self) -> Optional[Dict[str, Any]]:
        """Fetch engine metrics from SearXNG's authenticated metrics endpoint."""
        if not getattr(self, "metrics_enabled", True):
            return None
        url = f"http://localhost:{self.port}/metrics"
        try:
            request = urllib.request.Request(url)
            credentials = f":{getattr(self, 'metrics_password', '')}".encode("utf-8")
            request.add_header(
                "Authorization",
                f"Basic {base64.b64encode(credentials).decode('ascii')}",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                text = response.read().decode("utf-8", errors="replace")
                if not text.strip():
                    logger.warning("SearXNG metrics endpoint returned empty content")
                    return None
                return self._parse_metrics(text)
        except urllib.error.HTTPError as e:
            logger.warning(f"SearXNG metrics endpoint returned HTTP {e.code}: {e.reason}")
            return None
        except urllib.error.URLError as e:
            logger.warning(f"SearXNG metrics endpoint unreachable: {e.reason}")
            return None

    def _parse_metrics(self, text: str) -> Dict[str, Any]:
        """Convert SearXNG OpenMetrics output into the monitor's stats shape."""
        engines: Dict[str, Dict[str, Any]] = {}
        pattern = re.compile(
            r"^searxng_engines_(request_count_total|response_time_total_seconds)"
            r'\{engine_name="([^"]+)"\}\s+([0-9.eE+-]+)$'
        )
        for line in text.splitlines():
            match = pattern.match(line.strip())
            if not match:
                continue
            metric_name, engine_name, value = match.groups()
            engine = engines.setdefault(engine_name, {})
            if "request_count" in metric_name:
                engine["total"] = int(float(value))
            else:
                engine["median_response_time"] = round(float(value) * 1000, 2)

        response_times = [
            engine["median_response_time"]
            for engine in engines.values()
            if "median_response_time" in engine
        ]
        return {
            "requests": sum(engine.get("total", 0) for engine in engines.values()),
            "median_response_time": round(sum(response_times) / len(response_times), 2)
            if response_times
            else 0,
            "engines": engines,
        }

    def _load_published_engines(self) -> Set[str]:
        """Remember engine discovery topics so removed engines can be cleared."""
        try:
            with open("/data/searxng_mqtt_engines.json") as state_file:
                return set(json.load(state_file))
        except (OSError, TypeError, json.JSONDecodeError):
            return set()

    def _save_published_engines(self) -> None:
        try:
            with open("/data/searxng_mqtt_engines.json", "w") as state_file:
                json.dump(sorted(self._published_engines), state_file)
        except OSError as error:
            logger.warning(f"Could not persist MQTT engine state: {error}")

    def _availability_topic(self) -> str:
        return f"{self.mqtt_base_topic}/status"

    def _connect_mqtt(self, service: Dict[str, Any]) -> None:
        """Start Paho's network loop; it reconnects after broker outages."""
        host = str(service.get("host", "")).strip()
        if not host:
            logger.error("MQTT Discovery requires an available Supervisor MQTT service")
            self.mqtt_enabled = False
            return
        try:
            import paho.mqtt.client as mqtt  # type: ignore

            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=f"searxng-{self.instance_name.lower().replace(' ', '-')}"
            )
            username = service.get("username")
            if username:
                client.username_pw_set(username, service.get("password", ""))
            client.will_set(self._availability_topic(), "offline", qos=1, retain=True)
            client.on_connect = self._on_mqtt_connect
            client.on_disconnect = self._on_mqtt_disconnect
            port = int(service.get("port", 1883))
            client.connect_async(host, port, keepalive=60)
            self.mqtt_client = client
            client.loop_start()
        except Exception as error:
            logger.error(f"MQTT broker connection failed ({host}): {error}")

    def _on_mqtt_connect(self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any = None) -> None:
        if reason_code != 0:
            logger.error(f"MQTT broker rejected connection: {reason_code}")
            return
        self.mqtt_connected = True
        self._publish_mqtt(self._availability_topic(), "online", retain=True, qos=1)
        if self._last_stats:
            self._process_stats(self._last_stats)
        logger.info("Connected to MQTT broker")

    def _on_mqtt_disconnect(self, client: Any, userdata: Any, disconnect_flags: Any = None, reason_code: Any = None, properties: Any = None) -> None:
        self.mqtt_connected = False
        logger.warning("Disconnected from MQTT broker; waiting for reconnect")

    def _publish_mqtt(self, topic: str, payload: Any, retain: bool = False, qos: int = 0) -> bool:
        if not self.mqtt_enabled or not self.mqtt_client or not self.mqtt_connected:
            return False
        try:
            message = json.dumps(payload) if not isinstance(payload, str) else payload
            return self.mqtt_client.publish(topic, message, qos=qos, retain=retain).rc == 0
        except Exception as error:
            logger.warning(f"MQTT publish failed for {topic}: {error}")
            return False

    def stop(self) -> None:
        """Publish retained offline status and stop the MQTT network loop."""
        self.stop_event.set()
        if not self.mqtt_client:
            return
        try:
            if self.mqtt_connected:
                message = self.mqtt_client.publish(
                    self._availability_topic(), "offline", qos=1, retain=True
                )
                if message.rc == 0:
                    message.wait_for_publish(timeout=5)
            self.mqtt_client.disconnect()
            self.mqtt_client.loop_stop()
        except Exception as error:
            logger.warning(f"Error while stopping MQTT monitor: {error}")

    def _publish_discovery(self, key: str, name: str, state: Any, attributes: Dict[str, Any], unit: Optional[str] = None, state_class: Optional[str] = None, device_class: Optional[str] = None, enabled_by_default: bool = True) -> bool:
        state_topic = f"{self.mqtt_base_topic}/sensor/{key}/state"
        discovery_topic = f"{self.discovery_prefix}/sensor/{key}/config"
        payload: Dict[str, Any] = {
            "unique_id": f"searxng_{key}",
            "default_entity_id": f"sensor.searxng_{key}",
            "name": name,
            "state_topic": state_topic,
            "json_attributes_topic": f"{self.mqtt_base_topic}/sensor/{key}/attributes",
            "availability_topic": self._availability_topic(),
            "payload_available": "online",
            "payload_not_available": "offline",
            "entity_category": "diagnostic",
            "enabled_by_default": enabled_by_default,
            "expire_after": self.update_interval * 3,
            "device": {
                "identifiers": ["searxng"],
                "name": self.instance_name,
                "manufacturer": "SearXNG",
                "model": "SearXNG statistics",
            },
        }
        if unit:
            payload["unit_of_measurement"] = unit
        if state_class:
            payload["state_class"] = state_class
        if device_class:
            payload["device_class"] = device_class
        configured = self._publish_mqtt(discovery_topic, payload, retain=True)
        published = self._publish_mqtt(state_topic, state, retain=True)
        published = self._publish_mqtt(f"{self.mqtt_base_topic}/sensor/{key}/attributes", attributes, retain=True) or published
        return configured and published

    def _process_stats(self, stats: Dict[str, Any]) -> bool:
        """Process and register stats as entities"""
        self._last_stats = stats
        checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        # Extract key metrics
        metrics = {
            "requests": stats.get("requests", 0),
            "median_response_time": round(stats.get("median_response_time", 0), 2),
            "engine_count": len(stats.get("engines", {})),
        }

        success_count = 0
        definitions = {
            "requests": ("SearXNG Requests", metrics["requests"], "count", "total_increasing", None),
            "average_response_time": ("SearXNG Median Response Time", metrics["median_response_time"], "ms", "measurement", "duration"),
            "engine_count": ("SearXNG Engine Count", metrics["engine_count"], None, "measurement", None),
            "last_checked": ("SearXNG Last Metrics Check", checked_at, None, None, "timestamp"),
        }
        for key, (name, value, unit, state_class, device_class) in definitions.items():
            if self._publish_discovery(key, name, value, {"last_checked": checked_at}, unit, state_class, device_class):
                success_count += 1

        current_engines: Set[str] = set()
        for engine_name, engine_stats in stats.get("engines", {}).items():
            key = "engine_" + re.sub(r"[^a-z0-9_]+", "_", engine_name.lower()).strip("_")
            current_engines.add(key)
            attributes = {
                "requests": engine_stats.get("total", 0),
                "median_response_time": round(engine_stats.get("median_response_time", 0), 2),
                "last_checked": checked_at,
            }
            if self._publish_discovery(key, f"SearXNG Engine {engine_name}", engine_stats.get("total", 0), attributes, "count", "total_increasing", enabled_by_default=False):
                success_count += 1

        for removed_key in self._published_engines - current_engines:
            self._publish_mqtt(f"{self.discovery_prefix}/sensor/{removed_key}/config", "", retain=True)
        self._published_engines = current_engines
        self._save_published_engines()
        logger.info(f"Published {success_count} MQTT sensors")
        return success_count > 0

    def run(self) -> None:
        """Main monitoring loop"""
        if not self.enabled:
            logger.info("Entity monitor is disabled, exiting")
            return
        
        logger.info(f"Starting monitor with {self.update_interval}s interval")
        
        consecutive_failures = 0
        max_failures = 5

        while not self.stop_event.is_set():
            try:
                stats = self._get_stats()
                if stats:
                    self._last_stats = stats
                    if self.mqtt_connected:
                        self._process_stats(stats)
                    else:
                        logger.info("MQTT is not connected yet; waiting to publish stats")
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        logger.error(
                            f"Failed to get stats {max_failures} times, retrying..."
                        )
                        consecutive_failures = 0
            except Exception as e:
                logger.error(f"Unexpected error in monitor loop: {e}")
                consecutive_failures += 1

            self.stop_event.wait(self.update_interval)


if __name__ == "__main__":
    options_file = os.environ.get("OPTIONS_FILE", "/data/options.json")
    
    # Wait for SearXNG to start
    logger.info("Waiting for SearXNG to be ready...")
    time.sleep(5)

    monitor = SearXNGMonitor(options_file)
    signal.signal(signal.SIGTERM, lambda _signum, _frame: monitor.stop_event.set())
    signal.signal(signal.SIGINT, lambda _signum, _frame: monitor.stop_event.set())
    try:
        monitor.run()
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    finally:
        monitor.stop()
