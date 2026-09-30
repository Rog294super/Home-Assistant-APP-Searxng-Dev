"""Generate SearXNG settings from Home Assistant app options."""

import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

from validate_base_url import validate_base_url

DISABLED_ENGINE_KEYS = (
    "disabled_engines_general",
    "disabled_engines_images",
    "disabled_engines_videos",
    "disabled_engines_news",
    "disabled_engines_maps",
    "disabled_engines_music",
    "disabled_engines_it",
    "disabled_engines_science",
    "disabled_engines_files",
    "disabled_engines_social_media",
)


def parse_engine_names(values: Any) -> list[str]:
    if isinstance(values, str):
        return [part.strip() for part in values.split(",") if part.strip()]
    if isinstance(values, list):
        return [str(value).strip() for value in values if str(value).strip()]
    return []


def generate_settings(
    options: dict[str, Any], secret_key: str, metrics_secret: str
) -> dict[str, Any]:
    base_url = options.get("base_url") or ""
    if base_url:
        try:
            base_url = validate_base_url(base_url)
        except ValueError as error:
            print(f"[searxng-app] WARNING: Invalid base_url '{base_url}'. {error}")
            print(
                "[searxng-app] WARNING: SearXNG will continue without a configured "
                "base_url to avoid broken redirects and CSRF errors."
            )
            base_url = ""

    settings: dict[str, Any] = {
        "use_default_settings": True,
        "general": {
            "instance_name": options.get("instance_name") or "SearXNG",
            "enable_metrics": bool(options.get("enable_metrics", True)),
            "open_metrics": metrics_secret,
        },
        "server": {
            "secret_key": secret_key,
            "base_url": base_url,
            "image_proxy": bool(options.get("image_proxy", True)),
            "port": int(options.get("port", 18080)),
        },
        "search": {
            "safesearch": int(options.get("safesearch", 0)),
            "formats": ["html", "json"],
        },
    }

    if options.get("autocomplete"):
        settings["search"]["autocomplete"] = options["autocomplete"]

    disabled_engine_names = [
        name
        for key in DISABLED_ENGINE_KEYS
        for name in parse_engine_names(options.get(key, ""))
    ]
    if disabled_engine_names:
        print("[searxng-app] Using per-category disabled_engines configuration")
        settings["engines"] = [
            {"name": name, "disabled": True}
            for name in dict.fromkeys(disabled_engine_names)
        ]
        return settings

    parsed_legacy = parse_engine_names(options.get("disabled_engines"))
    if parsed_legacy:
        print("[searxng-app] Using legacy disabled_engines configuration")
        settings["engines"] = [
            {"name": name, "disabled": True}
            for name in dict.fromkeys(parsed_legacy)
        ]
        return settings

    legacy_engines = options.get("engines")
    if isinstance(legacy_engines, dict) and legacy_engines:
        print("[searxng-app] Using legacy engines configuration")
        settings["engines"] = [
            {"name": str(name), "disabled": not bool(enabled)}
            for name, enabled in legacy_engines.items()
        ]
    else:
        print(
            "[searxng-app] No engine overrides configured; "
            "using SearXNG upstream defaults"
        )
    return settings


def write_settings(
    options_path: str, settings_path: str, secret_key: str, metrics_secret: str
) -> None:
    with Path(options_path).open(encoding="utf-8") as options_file:
        options = json.load(options_file)
    settings = generate_settings(options, secret_key, metrics_secret)
    with Path(settings_path).open("w", encoding="utf-8") as settings_file:
        yaml.safe_dump(settings, settings_file, sort_keys=False, allow_unicode=True)
    print(f"[searxng-app] Wrote {settings_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: generate_settings.py OPTIONS_FILE SETTINGS_FILE")
    write_settings(
        sys.argv[1],
        sys.argv[2],
        os.environ["SECRET_KEY"],
        os.environ["METRICS_SECRET"],
    )