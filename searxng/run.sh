#!/bin/sh
set -e

# The image ships its own venv with python + PyYAML (SearXNG needs both to
# load its own settings), so we reuse that interpreter instead of relying
# on a bare system python3 having PyYAML available.
PYTHON="/usr/local/searxng/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    PYTHON="python3"
fi

OPTIONS_FILE="/data/options.json"
SETTINGS_FILE="/etc/searxng/settings.yml"
SECRET_FILE="/data/generated_secret"

mkdir -p /etc/searxng

if [ ! -f "$OPTIONS_FILE" ]; then
    echo "[searxng-app] ERROR: $OPTIONS_FILE not found."
    exit 1
fi

PORT=$("$PYTHON" -c "import json; print(json.load(open('$OPTIONS_FILE')).get('port', 18080))")
SECRET_KEY=$("$PYTHON" -c "import json; print(json.load(open('$OPTIONS_FILE')).get('secret_key') or '')")

# ---------------------------------------------------------
# Persistent secret key — keep it stable across restarts
# instead of regenerating (and invalidating sessions) every boot.
# ---------------------------------------------------------

if [ -z "$SECRET_KEY" ]; then
    if [ -f "$SECRET_FILE" ]; then
        SECRET_KEY=$(cat "$SECRET_FILE")
    else
        SECRET_KEY=$(head -c 32 /dev/urandom | sha256sum | cut -d' ' -f1)
        echo "$SECRET_KEY" > "$SECRET_FILE"
        echo "[searxng-app] Generated and stored a new secret_key"
    fi
fi

# ---------------------------------------------------------
# Build settings.yml as a single Python dict -> YAML dump.
#
# This replaces the old sed-template + cat-append approach, which produced
# TWO top-level `search:` keys whenever `autocomplete` was set (the default).
# YAML doesn't merge duplicate keys — the second one silently won, which
# meant `safesearch` and the JSON API (`formats`) were dropped on every
# normal boot. Building one dict and dumping it once makes that class of
# bug structurally impossible.
#
# The engines list is built from whatever keys exist under options.engines
# in config.yaml — NOT a hardcoded list in this script. That's what used to
# let `brave`/`wikidata` stay force-enabled here after they were removed
# from config.yaml/schema/translations (see CHANGELOG). Now this script
# automatically stays in sync with config.yaml with no separate list to
# maintain or forget to update.
# ---------------------------------------------------------

SECRET_KEY="$SECRET_KEY" "$PYTHON" - "$OPTIONS_FILE" "$SETTINGS_FILE" <<'PYEOF'
import json
import os
import sys

import yaml

options_path, settings_path = sys.argv[1], sys.argv[2]

with open(options_path) as f:
    options = json.load(f)

secret_key = os.environ["SECRET_KEY"]

settings = {
    "use_default_settings": True,
    "general": {
        "instance_name": options.get("instance_name") or "SearXNG",
    },
    "server": {
        "secret_key": secret_key,
        "base_url": options.get("base_url") or "",
        "image_proxy": bool(options.get("image_proxy", True)),
    },
    "search": {
        "safesearch": int(options.get("safesearch", 0)),
        "formats": ["html", "json"],
    },
}

autocomplete = options.get("autocomplete")
if autocomplete:
    settings["search"]["autocomplete"] = autocomplete

engines = options.get("engines", {})
settings["engines"] = [
    {"name": name, "disabled": not bool(enabled)}
    for name, enabled in engines.items()
]

with open(settings_path, "w") as f:
    yaml.safe_dump(settings, f, sort_keys=False, allow_unicode=True)

print(f"[searxng-app] Wrote {settings_path}")
PYEOF

echo "[searxng-app] Generated settings:"
cat "$SETTINGS_FILE"

export SEARXNG_SETTINGS_PATH="$SETTINGS_FILE"

# ---------------------------------------------------------
# Start SearXNG via Granian — the production WSGI server the official
# SearXNG container itself uses (see container/entrypoint.sh upstream),
# rather than `python -m searx.webapp`, which launches Flask's built-in
# development server (single-worker, not meant for continuous use).
# Calling Granian directly with explicit --host/--port also avoids relying
# on internal entrypoint script paths, which have moved between SearXNG
# releases.
# ---------------------------------------------------------

GRANIAN="/usr/local/searxng/.venv/bin/granian"
if [ ! -x "$GRANIAN" ]; then
    GRANIAN="granian"
fi

echo "[searxng-app] Starting SearXNG on port $PORT via Granian"

exec "$GRANIAN" \
    --interface wsgi \
    --host 0.0.0.0 \
    --port "$PORT" \
    searx.webapp:app
