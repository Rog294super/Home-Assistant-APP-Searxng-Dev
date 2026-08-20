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


if __name__ == "__main__":
    unittest.main()
