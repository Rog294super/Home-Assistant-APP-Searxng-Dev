import unittest

try:
    from searxng.validate_base_url import validate_base_url
except ModuleNotFoundError:  # pragma: no cover - the test is meant to fail until the helper exists
    validate_base_url = None


class TestValidateBaseUrl(unittest.TestCase):
    def test_accepts_valid_http_url(self):
        self.assertEqual(validate_base_url("http://searxng.local/"), "http://searxng.local/")

    def test_accepts_valid_https_url_with_path(self):
        self.assertEqual(validate_base_url("https://example.com/searxng/"), "https://example.com/searxng/")

    def test_rejects_missing_scheme(self):
        with self.assertRaises(ValueError):
            validate_base_url("searxng.local/")

    def test_rejects_double_slash_path(self):
        with self.assertRaises(ValueError):
            validate_base_url("https://example.com//")


if __name__ == "__main__":
    unittest.main()
