#!/bin/bash
set -e

OPTIONS_FILE="/data/options.json"
SETTINGS_FILE="/etc/searxng/settings.yml"
SECRET_FILE="/data/generated_secret"

mkdir -p /etc/searxng

if [ ! -f "$OPTIONS_FILE" ]; then
    echo "[searxng-addon] ERROR: $OPTIONS_FILE not found."
    exit 1
fi

BASE_URL=$(python3 -c "
import json
print(json.load(open('$OPTIONS_FILE')).get('base_url', ''))
")

INSTANCE_NAME=$(python3 -c "
import json
print(json.load(open('$OPTIONS_FILE')).get('instance_name', 'SearXNG'))
")

PORT=$(python3 -c "
import json
print(json.load(open('$OPTIONS_FILE')).get('port', 18080))
")

SECRET_KEY=$(python3 -c "
import json
print(json.load(open('$OPTIONS_FILE')).get('secret_key', ''))
")

AUTOCOMPLETE=$(python3 -c "
import json
print(json.load(open('$OPTIONS_FILE')).get('autocomplete', ''))
")

# ---------------------------------------------------------
# Generate persistent secret key
# ---------------------------------------------------------

if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "None" ] || [ "$SECRET_KEY" = "null" ]; then
    if [ -f "$SECRET_FILE" ]; then
        SECRET_KEY=$(cat "$SECRET_FILE")
    else
        SECRET_KEY=$(head -c 32 /dev/urandom | sha256sum | cut -d' ' -f1)
        echo "$SECRET_KEY" > "$SECRET_FILE"

        echo "[searxng-addon] Generated and stored a new secret_key"
    fi
fi

export BASE_URL INSTANCE_NAME SECRET_KEY PORT

# ---------------------------------------------------------
# Generate base SearXNG configuration
# ---------------------------------------------------------

sed \
    -e "s|\${BASE_URL}|${BASE_URL}|g" \
    -e "s|\${INSTANCE_NAME}|${INSTANCE_NAME}|g" \
    -e "s|\${SECRET_KEY}|${SECRET_KEY}|g" \
    -e "s|\${PORT}|${PORT}|g" \
    /settings.yml.template > "$SETTINGS_FILE"

# ---------------------------------------------------------
# Optional autocomplete configuration
# ---------------------------------------------------------

if [ -n "$AUTOCOMPLETE" ]; then
    cat >> "$SETTINGS_FILE" <<EOF

search:
  autocomplete: "$AUTOCOMPLETE"
EOF
fi

# ---------------------------------------------------------
# Engine overrides
# ---------------------------------------------------------

ENGINES_YAML=""

for engine in \
    google \
    bing \
    duckduckgo \
    brave \
    startpage \
    qwant \
    wikipedia \
    github \
    youtube \
    reddit \
    stackoverflow \
    wolframalpha \
    wikidata
do

    enabled=$(python3 -c "
import json
data = json.load(open('$OPTIONS_FILE'))
print(data.get('engines', {}).get('$engine', True))
")

    if [ "$enabled" = "True" ]; then
        disabled="false"
    else
        disabled="true"
    fi

    ENGINES_YAML="${ENGINES_YAML}  - name: \"${engine}\"
    disabled: ${disabled}
"
done

{
    echo ""
    echo "engines:"
    echo "$ENGINES_YAML"
} >> "$SETTINGS_FILE"

# ---------------------------------------------------------
# Debug output
# ---------------------------------------------------------

echo "[searxng-addon] Generated settings:"
cat "$SETTINGS_FILE"

export SEARXNG_SETTINGS_PATH="$SETTINGS_FILE"

# ---------------------------------------------------------
# Start SearXNG
# ---------------------------------------------------------

echo "[searxng-addon] Starting SearXNG on port $PORT"

exec /usr/local/searxng/.venv/bin/python \
    -m searx.webapp \
    --host 0.0.0.0 \
    --port "$PORT"