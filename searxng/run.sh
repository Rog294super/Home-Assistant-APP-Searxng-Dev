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
LIMITER_SETTINGS_FILE="/etc/searxng/limiter.toml"
SECRET_FILE="/data/generated_secret"
METRICS_SECRET_FILE="/data/generated_metrics_secret"

mkdir -p /etc/searxng

if [ ! -f "$OPTIONS_FILE" ]; then
    echo "[searxng-app] ERROR: $OPTIONS_FILE not found."
    exit 1
fi

# Keep the runtime port aligned with the app's web UI and watchdog metadata.
PORT=18080
ENABLE_MQTT_DISCOVERY=$("$PYTHON" -c "import json; print(str(bool(json.load(open('$OPTIONS_FILE')).get('enable_mqtt_discovery', True))).lower())")
ENABLE_STATS_ENTITIES=$("$PYTHON" -c "import json; print(str(bool(json.load(open('$OPTIONS_FILE')).get('enable_stats_entities', True))).lower())")
ENABLE_METRICS=$("$PYTHON" -c "import json; print(str(bool(json.load(open('$OPTIONS_FILE')).get('enable_metrics', True))).lower())")
ENABLE_RATE_LIMITER=$("$PYTHON" -c "import json; print(str(bool(json.load(open('$OPTIONS_FILE')).get('enable_rate_limiter', False))).lower())")
VALKEY_DATA_DIR="/data/searxng-valkey"
VALKEY_SOCKET="$VALKEY_DATA_DIR/valkey.sock"
VALKEY_PID=""

# ---------------------------------------------------------
# Persistent secret key — keep it stable across restarts
# instead of regenerating (and invalidating sessions) every boot.
# ---------------------------------------------------------

if [ -f "$SECRET_FILE" ]; then
    SECRET_KEY=$(cat "$SECRET_FILE")
    if ! printf '%s' "$SECRET_KEY" | grep -Eq '^[0-9a-fA-F]{64}$'; then
        echo "[searxng-app] WARNING: Replacing invalid secret_key file"
        SECRET_KEY=$(head -c 32 /dev/urandom | sha256sum | cut -d' ' -f1)
        SECRET_TMP="$SECRET_FILE.tmp"
        printf '%s\n' "$SECRET_KEY" > "$SECRET_TMP"
        mv -f "$SECRET_TMP" "$SECRET_FILE"
    fi
else
    # Hash random bytes to create a fixed-length key without storing raw entropy.
    SECRET_KEY=$(head -c 32 /dev/urandom | sha256sum | cut -d' ' -f1)
    SECRET_TMP="$SECRET_FILE.tmp"
    printf '%s\n' "$SECRET_KEY" > "$SECRET_TMP"
    mv -f "$SECRET_TMP" "$SECRET_FILE"
    echo "[searxng-app] Generated and stored a new secret_key"
fi

if [ -f "$METRICS_SECRET_FILE" ]; then
    METRICS_SECRET=$(cat "$METRICS_SECRET_FILE")
    if ! printf '%s' "$METRICS_SECRET" | grep -Eq '^[0-9a-fA-F]{64}$'; then
        METRICS_SECRET=$(head -c 32 /dev/urandom | sha256sum | cut -d' ' -f1)
        METRICS_TMP="$METRICS_SECRET_FILE.tmp"
        printf '%s\n' "$METRICS_SECRET" > "$METRICS_TMP"
        mv -f "$METRICS_TMP" "$METRICS_SECRET_FILE"
        echo "[searxng-app] Replaced invalid metrics password"
    fi
else
    METRICS_SECRET=$(head -c 32 /dev/urandom | sha256sum | cut -d' ' -f1)
    METRICS_TMP="$METRICS_SECRET_FILE.tmp"
    printf '%s\n' "$METRICS_SECRET" > "$METRICS_TMP"
    mv -f "$METRICS_TMP" "$METRICS_SECRET_FILE"
    echo "[searxng-app] Generated and stored a separate metrics password"
fi
chmod 600 "$SECRET_FILE" "$METRICS_SECRET_FILE"
chown searxng:searxng "$METRICS_SECRET_FILE"

# Settings generation contains only app options and stays independent from
# MQTT service credentials, which the monitor retrieves directly.

SECRET_KEY="$SECRET_KEY" METRICS_SECRET="$(cat "$METRICS_SECRET_FILE")" \
    "$PYTHON" /generate_settings.py "$OPTIONS_FILE" "$SETTINGS_FILE"
chmod 600 "$SETTINGS_FILE"
chown searxng:searxng "$SETTINGS_FILE"
chmod 600 "$LIMITER_SETTINGS_FILE"
chown searxng:searxng "$LIMITER_SETTINGS_FILE"

echo "[searxng-app] Generated settings:"
# Settings contain credentials; mask them before writing the generated YAML to logs.
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

SEARXNG_UID=$( "$PYTHON" -c 'import pwd; print(pwd.getpwnam("searxng").pw_uid)' )
SEARXNG_GID=$( "$PYTHON" -c 'import pwd; print(pwd.getpwnam("searxng").pw_gid)' )
if [ -z "$SEARXNG_UID" ] || [ -z "$SEARXNG_GID" ]; then
    echo "[searxng-app] ERROR: Could not resolve the searxng user"
    exit 1
fi

echo "[searxng-app] Starting SearXNG on port $PORT via Granian"

run_as_searxng() {
    # Drop supplementary groups, primary group, and uid before execing the server.
    SUPERVISOR_TOKEN='' "$PYTHON" -c \
        'import os, sys; uid=int(sys.argv[1]); gid=int(sys.argv[2]); os.setgroups([gid]); os.setgid(gid); os.setuid(uid); os.execv(sys.argv[3], sys.argv[3:])' \
        "$SEARXNG_UID" "$SEARXNG_GID" \
        "$@"
}

run_monitor_as_searxng() {
    SUPERVISOR_TOKEN="$SUPERVISOR_TOKEN" "$PYTHON" -c \
        'import os, sys; uid=int(sys.argv[1]); gid=int(sys.argv[2]); os.setgroups([gid]); os.setgid(gid); os.setuid(uid); os.execv(sys.argv[3], sys.argv[3:])' \
        "$SEARXNG_UID" "$SEARXNG_GID" \
        "$@"
}

wait_for_valkey() {
    # Probe through the same private socket SearXNG will use; never open TCP.
    "$PYTHON" -c 'import sys, time, valkey
client = valkey.Valkey.from_url("unix://" + sys.argv[1] + "?db=0", socket_connect_timeout=1, socket_timeout=1)
for _ in range(30):
    try:
        client.ping()
        break
    except Exception:
        time.sleep(0.5)
else:
    raise SystemExit("Valkey did not become ready")' "$VALKEY_SOCKET"
}

start_valkey() {
    # Keep the limiter backend private to the app: the socket lives under the
    # app's own data directory and is never exposed as a host TCP port.
    echo "[searxng-app] Starting private Valkey for the rate limiter"
    mkdir -p "$VALKEY_DATA_DIR"
    chown -R "$SEARXNG_UID:$SEARXNG_GID" "$VALKEY_DATA_DIR"
    chmod 700 "$VALKEY_DATA_DIR"
    run_as_searxng /valkey-server.sh \
        --port 0 \
        --unixsocket "$VALKEY_SOCKET" \
        --unixsocketperm 700 \
        --dir "$VALKEY_DATA_DIR" \
        --appendonly no \
        --save "" \
        --maxmemory 64mb \
        --maxmemory-policy allkeys-lru \
        --logfile "" &
    VALKEY_PID=$!
    if ! wait_for_valkey; then
        echo "[searxng-app] ERROR: Private Valkey failed to start; refusing to start SearXNG with the rate limiter enabled."
        kill "$VALKEY_PID" 2>/dev/null || true
        wait "$VALKEY_PID" 2>/dev/null || true
        exit 1
    fi
    echo "[searxng-app] Private Valkey is ready on its protected Unix socket"
}

if [ "$ENABLE_RATE_LIMITER" = "true" ]; then
    start_valkey
fi

# Start SearXNG as the unprivileged app user without the Supervisor token.
run_as_searxng "$GRANIAN" \
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
    MONITOR_OPTIONS_FILE="/tmp/searxng-monitor-options.json"
    "$PYTHON" -c \
        'import sys; sys.path.insert(0, "/"); from monitor import write_monitor_options; write_monitor_options(sys.argv[1], sys.argv[2])' \
        "$OPTIONS_FILE" "$MONITOR_OPTIONS_FILE"
    chown "$SEARXNG_UID:$SEARXNG_GID" "$MONITOR_OPTIONS_FILE"
    chmod 600 "$MONITOR_OPTIONS_FILE"
    export OPTIONS_FILE="$MONITOR_OPTIONS_FILE"

    MONITOR_STATE_DIR="/data/searxng-monitor"
    MONITOR_STATE_FILE="$MONITOR_STATE_DIR/engine-state.json"
    mkdir -p "$MONITOR_STATE_DIR"
    chown "$SEARXNG_UID:$SEARXNG_GID" "$MONITOR_STATE_DIR"
    chmod 700 "$MONITOR_STATE_DIR"
    if [ -f /data/searxng_mqtt_engines.json ] && [ ! -e "$MONITOR_STATE_FILE" ]; then
        mv /data/searxng_mqtt_engines.json "$MONITOR_STATE_FILE"
    fi
    if [ -f "$MONITOR_STATE_FILE" ]; then
        chown "$SEARXNG_UID:$SEARXNG_GID" "$MONITOR_STATE_FILE"
        chmod 600 "$MONITOR_STATE_FILE"
    fi
    export SEARXNG_MONITOR_STATE_PATH="$MONITOR_STATE_FILE"
    
    echo "[searxng-app] Starting entity monitor service"
    
    PYTHON_BIN="$PYTHON"
    if [ ! -x "$PYTHON_BIN" ]; then
        PYTHON_BIN="python3"
    fi
    
    supervise_monitor() {
        MONITOR_CHILD_PID=""
        # shellcheck disable=SC2317,SC2329
        stop_monitor_supervisor() {
            trap - TERM INT
            if [ -n "$MONITOR_CHILD_PID" ]; then
                kill "$MONITOR_CHILD_PID" 2>/dev/null || true
                wait "$MONITOR_CHILD_PID" 2>/dev/null || true
            fi
            exit 0
        }
        trap stop_monitor_supervisor TERM INT

        while kill -0 "$GRANIAN_PID" 2>/dev/null; do
            run_monitor_as_searxng "$PYTHON_BIN" /monitor.py &
            MONITOR_CHILD_PID=$!
            if wait "$MONITOR_CHILD_PID"; then
                MONITOR_STATUS=0
            else
                MONITOR_STATUS=$?
            fi
            MONITOR_CHILD_PID=""
            if kill -0 "$GRANIAN_PID" 2>/dev/null; then
                echo "[searxng-app] WARNING: Entity monitor exited with status $MONITOR_STATUS; restarting in 10 seconds"
                sleep 10
            fi
        done
    }

    supervise_monitor &
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
    # Stop and reap both children so neither outlives the app container.
    trap - TERM INT
    kill "$GRANIAN_PID" 2>/dev/null || true
    if [ -n "$VALKEY_PID" ]; then
        kill "$VALKEY_PID" 2>/dev/null || true
    fi
    if [ -n "$MONITOR_PID" ]; then
        kill "$MONITOR_PID" 2>/dev/null || true
    fi
    wait "$GRANIAN_PID" 2>/dev/null || true
    if [ -n "$VALKEY_PID" ]; then
        wait "$VALKEY_PID" 2>/dev/null || true
    fi
    if [ -n "$MONITOR_PID" ]; then
        wait "$MONITOR_PID" 2>/dev/null || true
    fi
    exit 0
}
trap shutdown TERM INT

while kill -0 "$GRANIAN_PID" 2>/dev/null; do
    if [ -n "$VALKEY_PID" ] && ! kill -0 "$VALKEY_PID" 2>/dev/null; then
        echo "[searxng-app] ERROR: Private Valkey stopped; stopping SearXNG so the supervisor can restart the app."
        kill "$GRANIAN_PID" 2>/dev/null || true
        break
    fi
    sleep 2
done

if wait "$GRANIAN_PID"; then
    GRANIAN_STATUS=0
else
    GRANIAN_STATUS=$?
fi
if [ -n "$MONITOR_PID" ]; then
    kill "$MONITOR_PID" 2>/dev/null || true
    wait "$MONITOR_PID" 2>/dev/null || true
fi
if [ -n "$VALKEY_PID" ]; then
    kill "$VALKEY_PID" 2>/dev/null || true
    wait "$VALKEY_PID" 2>/dev/null || true
fi
echo "[searxng-app] SearXNG service stopped"
exit "$GRANIAN_STATUS"