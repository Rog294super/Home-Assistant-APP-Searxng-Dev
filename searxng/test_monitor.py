import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

module_path = Path(__file__).with_name("monitor.py")
spec = importlib.util.spec_from_file_location("searxng_monitor", module_path)
monitor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor_module)


class FakeResponse:
    def __init__(self, payload: bytes, content_type: str = "application/json"):
        self._payload = payload
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class TestMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = monitor_module.SearXNGMonitor.__new__(monitor_module.SearXNGMonitor)
        self.monitor.port = 18080
        self.monitor.mqtt_enabled = True
        self.monitor.mqtt_connected = True
        self.monitor.mqtt_base_topic = "searxng"
        self.monitor.discovery_prefix = "homeassistant"
        self.monitor.instance_name = "SearXNG"
        self.monitor.mqtt_client = MagicMock()
        self.monitor.mqtt_client.publish.return_value.rc = 0
        self.monitor._published_engines = set()

    def test_parse_metrics(self):
        payload = """\
searxng_engines_request_count_total{engine_name="google"} 7
searxng_engines_response_time_total_seconds{engine_name="google"} 0.42
searxng_engines_request_count_total{engine_name="bing"} 3
"""
        self.assertEqual(
            self.monitor._parse_metrics(payload),
            {
                "requests": 10,
                "engines": {
                    "google": {"total": 7, "avg_response_time": 420.0},
                    "bing": {"total": 3},
                },
                "average_response_time": 420.0,
            },
        )

    def test_get_stats_rejects_non_json_html(self):
        self.assertEqual(
            self.monitor._parse_metrics("<html>Service unavailable</html>"),
            {"requests": 0, "average_response_time": 0, "engines": {}},
        )

    def test_process_stats_publishes_discovery_and_state_topics(self):
        self.monitor._save_published_engines = MagicMock()
        self.assertTrue(self.monitor._process_stats({
            "requests": 10,
            "average_response_time": 42.5,
            "engines": {"Google News": {"total": 7, "avg_response_time": 12.0}},
        }))

        publications = [call.args for call in self.monitor.mqtt_client.publish.call_args_list]
        topics = {publication[0] for publication in publications}
        self.assertIn("homeassistant/sensor/requests/config", topics)
        self.assertIn("searxng/sensor/requests/state", topics)
        self.assertIn("searxng/sensor/engine_google_news/state", topics)

        discovery = next(publication[1] for publication in publications if publication[0] == "homeassistant/sensor/requests/config")
        payload = json.loads(discovery)
        self.assertEqual(payload["unique_id"], "searxng_requests")
        self.assertEqual(payload["object_id"], "searxng_requests")
        self.assertEqual(payload["default_entity_id"], "sensor.searxng_requests")
        self.assertEqual(payload["availability_topic"], "searxng/status")
        self.assertEqual(payload["state_class"], "total_increasing")

    def test_publish_mqtt_is_noop_when_disabled(self):
        self.monitor.mqtt_enabled = False
        self.assertFalse(self.monitor._publish_mqtt("test/topic", "payload"))
        self.monitor.mqtt_client.publish.assert_not_called()

    def test_availability_changes_with_broker_connection(self):
        self.monitor._last_stats = None
        self.monitor._on_mqtt_connect(self.monitor.mqtt_client, None, {}, 0)
        self.assertTrue(self.monitor.mqtt_connected)
        self.monitor._on_mqtt_disconnect(self.monitor.mqtt_client, None, None, 1)
        self.assertFalse(self.monitor.mqtt_connected)
        availability = [call.args for call in self.monitor.mqtt_client.publish.call_args_list]
        self.assertEqual(availability[0][0], "searxng/status")
        self.assertEqual(availability[0][1], "online")

    def test_reconnect_republishes_last_stats(self):
        self.monitor._last_stats = {"requests": 3, "average_response_time": 10, "engines": {}}
        self.monitor._process_stats = MagicMock()
        self.monitor._on_mqtt_connect(self.monitor.mqtt_client, None, {}, 0)
        self.monitor._process_stats.assert_called_once_with(self.monitor._last_stats)

    @patch.dict("os.environ", {"MQTT_HOST": "mosquitto", "MQTT_PORT": "1884"}, clear=False)
    def test_haos_mqtt_service_values_override_options(self):
        self.monitor.options = {"mqtt_host": "legacy-host", "mqtt_port": 1883}
        self.assertEqual(self.monitor._mqtt_option("mqtt_host", "MQTT_HOST", "core-mosquitto"), "mosquitto")
        self.assertEqual(self.monitor._mqtt_option("mqtt_port", "MQTT_PORT", "1883"), "1884")


if __name__ == "__main__":
    unittest.main()
