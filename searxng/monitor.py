#!/usr/bin/env python3
"""
SearXNG Home Assistant Entity Monitor
Monitors SearXNG stats and registers them as Home Assistant entities
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import requests
import yaml

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("searxng-monitor")


class SearXNGMonitor:
    """Monitor SearXNG stats and register entities with Home Assistant"""

    def __init__(self, options_file: str):
        self.options_file = options_file
        self.options = self._load_options()
        
        # Check if entity registration is enabled
        self.enabled = self.options.get("enable_stats_entities", True)
        if not self.enabled:
            logger.info("Entity registration is disabled in config")
            return
        
        self.ha_url = self._get_ha_url()
        self.ha_token = self._get_ha_token()
        self.port = self.options.get("port", 18080)
        self.instance_name = self.options.get("instance_name", "SearXNG")
        self.update_interval = self.options.get("entity_update_interval", 60)
        
        logger.info(f"Initialized SearXNG Monitor for {self.instance_name}")
        logger.info(f"Home Assistant URL: {self.ha_url}")
        logger.info(f"Update interval: {self.update_interval}s")

    def _load_options(self) -> Dict[str, Any]:
        """Load options from JSON file"""
        try:
            with open(self.options_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load options: {e}")
            return {}

    def _get_ha_url(self) -> str:
        """Get Home Assistant URL from environment"""
        # Inside Home Assistant app, use internal URL
        return os.environ.get("HA_URL", "http://supervisor/core")

    def _get_ha_token(self) -> Optional[str]:
        """Get Home Assistant API token from supervisor"""
        token_file = "/var/run/supervisor/homeassistant.auth.json"
        try:
            if os.path.exists(token_file):
                with open(token_file, "r") as f:
                    return json.load(f).get("access_token")
        except Exception as e:
            logger.warning(f"Failed to read HA token: {e}")
        return None

    def _get_stats(self) -> Optional[Dict[str, Any]]:
        """Fetch stats from SearXNG"""
        try:
            url = f"http://localhost:{self.port}/stats"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch stats: {e}")
            return None

    def _create_entity_id(self, stat_name: str) -> str:
        """Create a valid Home Assistant entity ID"""
        # Convert to lowercase, replace spaces with underscores
        return f"sensor.searxng_{stat_name.lower().replace(' ', '_').replace('-', '_')}"

    def _register_entity(self, entity_id: str, state: str, attributes: Dict[str, Any]) -> bool:
        """Register or update an entity in Home Assistant via API"""
        if not self.ha_token:
            return False

        try:
            url = f"{self.ha_url}/api/states/{entity_id}"
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "state": str(state),
                "attributes": attributes,
            }
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to register entity {entity_id}: {e}")
            return False

    def _publish_mqtt(self, topic: str, payload: str) -> bool:
        """Publish to MQTT if configured"""
        try:
            import paho.mqtt.publish as publish  # type: ignore

            mqtt_host = os.environ.get("MQTT_HOST", "localhost")
            mqtt_port = int(os.environ.get("MQTT_PORT", "1883"))
            
            publish.single(
                topic,
                payload,
                hostname=mqtt_host,
                port=mqtt_port,
                retain=True,
            )
            return True
        except Exception as e:
            logger.debug(f"MQTT publish failed: {e}")
            return False

    def _process_stats(self, stats: Dict[str, Any]) -> bool:
        """Process and register stats as entities"""
        success_count = 0
        
        # Extract key metrics
        metrics = {
            "requests": stats.get("requests", 0),
            "average_response_time": round(stats.get("average_response_time", 0), 2),
            "engine_count": len(stats.get("engines", {})),
            "uptime_seconds": stats.get("uptime", 0),
        }

        # Register main metrics
        for metric_name, value in metrics.items():
            entity_id = self._create_entity_id(metric_name)
            attributes = {
                "friendly_name": metric_name.replace("_", " ").title(),
                "icon": "mdi:magnify",
                "last_updated": datetime.now().isoformat(),
            }

            if metric_name == "average_response_time":
                attributes["unit_of_measurement"] = "ms"
            elif metric_name == "requests":
                attributes["unit_of_measurement"] = "count"
            elif metric_name == "uptime_seconds":
                attributes["unit_of_measurement"] = "s"

            if self._register_entity(entity_id, value, attributes):
                success_count += 1
                logger.debug(f"Registered entity {entity_id}: {value}")

        # Register per-engine stats
        engines = stats.get("engines", {})
        for engine_name, engine_stats in engines.items():
            entity_id = self._create_entity_id(f"engine_{engine_name}")
            attributes = {
                "friendly_name": f"SearXNG Engine {engine_name}",
                "icon": "mdi:cog",
                "requests": engine_stats.get("total", 0),
                "avg_response_time": round(engine_stats.get("avg_response_time", 0), 2),
            }
            
            if self._register_entity(entity_id, engine_stats.get("total", 0), attributes):
                success_count += 1
                logger.debug(f"Registered engine entity {entity_id}")

        logger.info(f"Registered {success_count} entities")
        return success_count > 0

    def run(self) -> None:
        """Main monitoring loop"""
        if not self.enabled:
            logger.info("Entity monitor is disabled, exiting")
            return
        
        logger.info(f"Starting monitor with {self.update_interval}s interval")
        
        consecutive_failures = 0
        max_failures = 5

        while True:
            try:
                stats = self._get_stats()
                if stats:
                    self._process_stats(stats)
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

            time.sleep(self.update_interval)


if __name__ == "__main__":
    options_file = os.environ.get("OPTIONS_FILE", "/data/options.json")
    
    # Wait for SearXNG to start
    logger.info("Waiting for SearXNG to be ready...")
    time.sleep(5)

    monitor = SearXNGMonitor(options_file)
    try:
        monitor.run()
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
        sys.exit(0)
