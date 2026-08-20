import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_get_stats_parses_json(self):
        payload = b'{"requests": 7, "engines": {}}'
        with patch.object(monitor_module.urllib.request, "urlopen", return_value=FakeResponse(payload)):
            self.assertEqual(self.monitor._get_stats(), {"requests": 7, "engines": {}})

    def test_get_stats_rejects_non_json_html(self):
        payload = b"<html><body>Service unavailable</body></html>"
        with patch.object(monitor_module.urllib.request, "urlopen", return_value=FakeResponse(payload, "text/html")):
            self.assertIsNone(self.monitor._get_stats())


if __name__ == "__main__":
    unittest.main()
