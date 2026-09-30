import unittest
import json
import tempfile
from pathlib import Path

import yaml

from generate_settings import generate_settings, write_settings


class TestGenerateSettings(unittest.TestCase):
    def test_settings_keep_search_options_and_use_upstream_engines(self):
        settings = generate_settings(
            {"autocomplete": "google", "safesearch": 2}, "secret", "metrics"
        )

        self.assertEqual(settings["search"]["formats"], ["html", "json"])
        self.assertEqual(settings["search"]["autocomplete"], "google")
        self.assertEqual(settings["search"]["safesearch"], 2)
        self.assertNotIn("engines", settings)
        self.assertEqual(yaml.safe_load(yaml.safe_dump(settings)), settings)

    def test_write_settings_creates_one_search_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            options_path = Path(directory) / "options.json"
            settings_path = Path(directory) / "settings.yml"
            options_path.write_text(
                json.dumps({"autocomplete": "google", "safesearch": 1}),
                encoding="utf-8",
            )

            write_settings(str(options_path), str(settings_path), "secret", "metrics")

            contents = settings_path.read_text(encoding="utf-8")
            settings = yaml.safe_load(contents)

        self.assertEqual(contents.count("\nsearch:"), 1)
        self.assertEqual(settings["search"]["formats"], ["html", "json"])
        self.assertEqual(settings["search"]["autocomplete"], "google")

    def test_per_category_engines_are_deduplicated(self):
        settings = generate_settings(
            {"disabled_engines_general": "google, bing", "disabled_engines_news": "google"},
            "secret",
            "metrics",
        )

        self.assertEqual(
            settings["engines"],
            [
                {"name": "google", "disabled": True},
                {"name": "bing", "disabled": True},
            ],
        )

    def test_legacy_engine_overrides_remain_supported(self):
        settings = generate_settings(
            {"engines": {"google": True, "reddit": False}}, "secret", "metrics"
        )

        self.assertEqual(
            settings["engines"],
            [
                {"name": "google", "disabled": False},
                {"name": "reddit", "disabled": True},
            ],
        )


if __name__ == "__main__":
    unittest.main()