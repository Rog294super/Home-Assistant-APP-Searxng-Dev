"""Generate SearXNG settings from Home Assistant app options."""

import ipaddress
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
    """Normalize comma-separated strings and lists of engine names."""
    if isinstance(values, str):
        return [part.strip() for part in values.split(",") if part.strip()]
    if isinstance(values, list):
        return [str(value).strip() for value in values if str(value).strip()]
    return []


def parse_trusted_proxies(values: Any) -> list[str]:
    """Validate and normalize comma-separated proxy IPs and CIDR networks."""
    if values is None or values == "":
        return []
    if not isinstance(values, str):
        raise ValueError("limiter_trusted_proxies must be a comma-separated string")

    proxies: list[str] = []
    for candidate in values.split(","):
        candidate = candidate.strip()
        if not candidate:
            continue
        try:
            proxy_network = str(ipaddress.ip_network(candidate, strict=False))
        except ValueError as error:
            raise ValueError(
                f"Invalid trusted proxy {candidate!r}; use an IP address or CIDR network"
            ) from error
        if proxy_network not in proxies:
            proxies.append(proxy_network)
    return proxies


def generate_limiter_config(options: dict[str, Any]) -> str:
    """Build a botdetection override, leaving SearXNG's schema defaults intact."""
    proxies = parse_trusted_proxies(options.get("limiter_trusted_proxies", ""))
    lines = ["[botdetection]", "trusted_proxies = ["]
    lines.extend(f"  {json.dumps(proxy)}," for proxy in proxies)
    lines.append("]")
    return "\n".join(lines) + "\n"


def generate_settings(
    options: dict[str, Any], secret_key: str, metrics_secret: str
) -> dict[str, Any]:
    """Build SearXNG settings, applying app options and legacy engine fallbacks."""
    base_url = options.get("base_url") or ""
    if base_url:
        try:
            base_url = validate_base_url(base_url)
        except ValueError as error:
            print(f"[searxng-app] WARNING: Invalid base_url. {error}")
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
            "port": 18080,
            "limiter": bool(options.get("enable_rate_limiter", False)),
        },
        "search": {
            "safesearch": int(options.get("safesearch", 0)),
            "formats": ["html"],
        },
    }

    for option_name, output_format in (
        ("enable_json_api", "json"),
        ("enable_csv_api", "csv"),
        ("enable_rss_api", "rss"),
    ):
        if bool(options.get(option_name, False)):
            settings["search"]["formats"].append(output_format)

    if settings["server"]["limiter"]:
        settings["valkey"] = {
            "url": "unix:///data/searxng-valkey/valkey.sock?db=0"
        }

    # Omitting the key preserves SearXNG's upstream behavior when no provider is selected.
    autocomplete = options.get("autocomplete")
    if autocomplete and autocomplete != "disabled":
        settings["search"]["autocomplete"] = options["autocomplete"]

    disabled_engine_names = [
        name
        for key in DISABLED_ENGINE_KEYS
        for name in parse_engine_names(options.get(key, ""))
    ]
    if disabled_engine_names:
        # Category fields take precedence over the legacy global engine options.
        print("[searxng-app] Using per-category disabled_engines configuration")
        settings["engines"] = [
            {"name": name, "disabled": True}
            for name in dict.fromkeys(disabled_engine_names)
        ]
        return settings

    # Apply legacy values only when no category-specific engine list was supplied.
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
    """Load app options and serialize the generated settings as YAML."""
    with Path(options_path).open(encoding="utf-8") as options_file:
        options = json.load(options_file)
    settings = generate_settings(options, secret_key, metrics_secret)
    limiter_config = generate_limiter_config(options)
    limiter_path = Path(settings_path).with_name("limiter.toml")
    with Path(settings_path).open("w", encoding="utf-8") as settings_file:
        yaml.safe_dump(settings, settings_file, sort_keys=False, allow_unicode=True)
    limiter_path.write_text(limiter_config, encoding="utf-8")
    print(f"[searxng-app] Wrote {settings_path}")
    print(f"[searxng-app] Wrote {limiter_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: generate_settings.py OPTIONS_FILE SETTINGS_FILE")
    write_settings(
        sys.argv[1],
        sys.argv[2],
        os.environ["SECRET_KEY"],
        os.environ["METRICS_SECRET"],
    )