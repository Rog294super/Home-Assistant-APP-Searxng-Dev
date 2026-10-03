#!/bin/sh
set -e
umask 077

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
METRICS_SECRET_FILE="/data/generated_metrics_secret"

mkdir -p /etc/searxng

if [ ! -f "$OPTIONS_FILE" ]; then
    echo "[searxng-app] ERROR: $OPTIONS_FILE not found."
    exit 1
fi

PORT=$("$PYTHON" -c "import json; print(json.load(open('$OPTIONS_FILE')).get('port', 18080))")
ENABLE_MQTT_DISCOVERY=$("$PYTHON" -c "import json; print(str(bool(json.load(open('$OPTIONS_FILE')).get('enable_mqtt_discovery', True))).lower())")
ENABLE_STATS_ENTITIES=$("$PYTHON" -c "import json; print(str(bool(json.load(open('$OPTIONS_FILE')).get('enable_stats_entities', True))).lower())")
ENABLE_METRICS=$("$PYTHON" -c "import json; print(str(bool(json.load(open('$OPTIONS_FILE')).get('enable_metrics', True))).lower())")

# ---------------------------------------------------------
# Persistent secret key — keep it stable across restarts
# instead of regenerating (and invalidating sessions) every boot.
# ---------------------------------------------------------

if [ -f "$SECRET_FILE" ]; then
    SECRET_KEY=$(cat "$SECRET_FILE")
else
    SECRET_KEY=$(head -c 32 /dev/urandom | sha256sum | cut -d' ' -f1)
    echo "$SECRET_KEY" > "$SECRET_FILE"
    echo "[searxng-app] Generated and stored a new secret_key"
fi

if [ ! -f "$METRICS_SECRET_FILE" ]; then
    head -c 32 /dev/urandom | sha256sum | cut -d' ' -f1 > "$METRICS_SECRET_FILE"
    echo "[searxng-app] Generated and stored a separate metrics password"
fi
chmod 600 "$SECRET_FILE" "$METRICS_SECRET_FILE"

# Settings generation contains only app options and stays independent from
# MQTT service credentials, which the monitor retrieves directly.

SECRET_KEY="$SECRET_KEY" METRICS_SECRET="$(cat "$METRICS_SECRET_FILE")" \
    "$PYTHON" /generate_settings.py "$OPTIONS_FILE" "$SETTINGS_FILE"
chmod 600 "$SETTINGS_FILE"

echo "[searxng-app] Generated settings:"
sed -E 's/^([[:space:]]*(secret_key|open_metrics):).*/\1 "<redacted>"/' "$SETTINGS_FILE"

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

# Start SearXNG in the background
SUPERVISOR_TOKEN='' "$GRANIAN" \
    --interface wsgi \
    --host 0.0.0.0 \
    --port "$PORT" \
    searx.webapp:app &

GRANIAN_PID=$!
echo "[searxng-app] SearXNG started with PID $GRANIAN_PID"

# ---------------------------------------------------------
# Start Home Assistant entity monitor (if enabled)
# The monitor registers SearXNG stats as Home Assistant entities
# ---------------------------------------------------------

MONITOR_PID=""
if [ "$ENABLE_STATS_ENTITIES" = "true" ] && [ "$ENABLE_METRICS" = "true" ] && \
    [ "$ENABLE_MQTT_DISCOVERY" = "true" ] && \
    { command -v python3 >/dev/null 2>&1 || command -v "$PYTHON" >/dev/null 2>&1; }; then
    export OPTIONS_FILE="$OPTIONS_FILE"
    
    echo "[searxng-app] Starting entity monitor service"
    
    PYTHON_BIN="$PYTHON"
    if [ ! -x "$PYTHON_BIN" ]; then
        PYTHON_BIN="python3"
    fi
    
    "$PYTHON_BIN" /monitor.py &
    MONITOR_PID=$!
    echo "[searxng-app] Monitor supervisor started with PID $MONITOR_PID"
else
    if [ "$ENABLE_STATS_ENTITIES" != "true" ]; then
        echo "[searxng-app] Stats entities are disabled; skipping entity monitor"
    elif [ "$ENABLE_METRICS" != "true" ]; then
        echo "[searxng-app] WARNING: Metrics are disabled; skipping entity monitor while keeping SearXNG running"
    elif [ "$ENABLE_MQTT_DISCOVERY" != "true" ]; then
        echo "[searxng-app] MQTT Discovery is disabled; skipping entity monitor"
    else
        echo "[searxng-app] Python not found, skipping entity monitor"
    fi
    MONITOR_PID=""
fi

# ---------------------------------------------------------
# Stop both child processes promptly when Supervisor stops the app.
# ---------------------------------------------------------

# shellcheck disable=SC2317,SC2329
shutdown() {
    trap - TERM INT
    kill "$GRANIAN_PID" 2>/dev/null || true
    if [ -n "$MONITOR_PID" ]; then
        kill "$MONITOR_PID" 2>/dev/null || true
    fi
    wait "$GRANIAN_PID" 2>/dev/null || true
    if [ -n "$MONITOR_PID" ]; then
        wait "$MONITOR_PID" 2>/dev/null || true
    fi
}
trap shutdown TERM INT

if wait "$GRANIAN_PID"; then
    GRANIAN_STATUS=0
else
    GRANIAN_STATUS=$?
fi
if [ -n "$MONITOR_PID" ]; then
    kill "$MONITOR_PID" 2>/dev/null || true
    wait "$MONITOR_PID" 2>/dev/null || true
fi
echo "[searxng-app] SearXNG service stopped"
exit "$GRANIAN_STATUS"