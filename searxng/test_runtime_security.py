import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import importlib.util

module_path = Path(__file__).with_name("monitor.py")
module_spec = importlib.util.spec_from_file_location("searxng_monitor", module_path)
monitor_module = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(monitor_module)


class TestRuntimeSecurity(unittest.TestCase):
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

    def test_mqtt_uses_tls_when_service_requests_it(self):
        mqtt_module = types.ModuleType("paho.mqtt.client")
        mqtt_module.CallbackAPIVersion = types.SimpleNamespace(VERSION2="version2")
        mqtt_module.Client = MagicMock(return_value=self.monitor.mqtt_client)
        mqtt_package = types.ModuleType("paho.mqtt")
        mqtt_package.client = mqtt_module
        paho_package = types.ModuleType("paho")
        paho_package.mqtt = mqtt_package

        with patch.dict(
            "sys.modules",
            {"paho": paho_package, "paho.mqtt": mqtt_package, "paho.mqtt.client": mqtt_module},
        ):
            self.monitor._connect_mqtt({
                "host": "core-mosquitto",
                "port": 8883,
                "username": "searxng",
                "password": "secret",
                "ssl": True,
            })

        self.monitor.mqtt_client.tls_set.assert_called_once_with()
        self.monitor.mqtt_client.connect_async.assert_called_once_with(
            "core-mosquitto", 8883, keepalive=60
        )

    def test_removed_engine_state_and_discovery_topics_are_cleaned_up(self):
        self.monitor._published_engines = {"request", "engine_google"}
        self.monitor._save_published_engines = MagicMock()

        self.monitor._process_stats({
            "requests": 5,
            "median_response_time": 42,
            "engines": {"Google": {"total": 2, "median_response_time": 12}},
        })

        publications = [call.args for call in self.monitor.mqtt_client.publish.call_args_list]
        removed_topic = next(
            publication[0]
            for publication in publications
            if publication[0] == "homeassistant/sensor/request/config"
        )
        self.assertEqual(
            self.monitor.mqtt_client.publish.call_args_list[-1].args[1],
            "",
        )
        self.assertEqual(self.monitor._published_engines, {"engine_google"})
        self.assertEqual(removed_topic, "homeassistant/sensor/request/config")

    def test_published_state_file_is_written_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            state_path.write_text("[]", encoding="utf-8")
            self.monitor._published_engines = {"engine_google"}
            self.monitor._state_path = str(state_path)

            self.monitor._save_published_engines()

            self.assertEqual(json.loads(state_path.read_text(encoding="utf-8")), ["engine_google"])
            self.assertFalse(state_path.with_name("state.json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
