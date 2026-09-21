# SearXNG for Home Assistant

This app installs SearXNG as a self-hosted search engine for Home Assistant OS or Supervised installations. It is designed to run directly on your host network, let the server owner set category-specific default-disabled engines, and be reached through your own local domain names such as `searxng.lan` or `searxng.local` rather than through Home Assistant ingress.

## What this app provides

- Direct access at your Home Assistant host IP and port, without the usual Home Assistant ingress path.
- Per-category engine blacklists that disable selected engines by default while leaving all other engines to keep SearXNG's upstream defaults.
- A local, privacy-friendly alternative to public search services.
- Compatibility with a custom DNS setup or reverse proxy for cleaner URLs.
- Optional MQTT Discovery sensors for SearXNG statistics, depending on an MQTT broker like `Mosquitto broker`.

## Installation

1. Add this repository URL to your Home Assistant app store:
   `https://github.com/Rog294super/Home-Assistant-APP-Searxng`
2. Open Home Assistant and go to **Settings → apps → app Store**.
3. Use **Check for updates**, then look for **SearXNG** under **Local apps**.
4. Install the app, configure the per-category default-disabled engine lists under **Configuration**, and then click **Start**.
5. Open the **Log** tab to confirm that the generated `settings.yml` was created correctly.

The first installation may take some time because the image is built on the device from the included Dockerfile.

## Accessing SearXNG

This app does not create hostnames for you. It runs on the host network, but you still need DNS or local name resolution to make names like `searxng.lan` or `searxng.local` point to your Home Assistant host.

### Using AdGuard Home or equivalant as DNS

If you already run AdGuard Home or equivalant, the easiest option is to add DNS rewrites:

1. Open **AdGuard Home**.
2. Go to **Filters → DNS rewrites**.
3. Add a rewrite for `searxng.lan` pointing to your Home Assistant host LAN IP.
4. Repeat for `searxng.local`.

You can then browse to:

- `http://searxng.lan:<PORT>/`
- `http://searxng.local:<PORT>/`

or use the built-in **Open Web UI** option from the app page.

### Important note about `.local`

Windows clients often treat `.local` as a reserved multicast name suffix and may try to resolve it via mDNS or LLMNR before consulting your DNS server. This can make `searxng.local` unreliable on some machines. If you run into issues, `searxng.lan` is usually the more dependable choice, Except edge will see `searxng.lan` as a search querry and won't go to the domain.

For more background, see this article: [Why using .local as a domain name extension is a bad idea](https://community.veeam.com/blogs-and-podcasts-57/why-using-local-as-your-domain-name-extension-is-a-bad-idea-4828).

## Port and URL notes

The SearXNG container listens internally on port `18080`, and the app exposes that directly through the host network. Because of that, the URL usually includes a port unless you place it behind a reverse proxy.

If you want a cleaner URL such as `http://searxng.lan/`, consider using a reverse proxy such as `Nginx Proxy manager` or Caddy and forward traffic to your Home Assistant host IP and the SearXNG port.

## Configuring default-disabled engines per category

The app exposes per-category lists that let the server owner disable selected engines by default for each SearXNG category while leaving all other engines untouched.

Available fields in the Home Assistant configuration are:

- `disabled_engines_general`
- `disabled_engines_images`
- `disabled_engines_videos`
- `disabled_engines_news`
- `disabled_engines_maps`
- `disabled_engines_music`
- `disabled_engines_it`
- `disabled_engines_science`
- `disabled_engines_files`
- `disabled_engines_social`

Each field is a list of SearXNG engine names. If an engine is not listed in that category, SearXNG keeps using its upstream default behavior for that engine.

Example:

```yaml
disabled_engines_general:
  - google
  - bing
  - duckduckgo

disabled_engines_images:
  - google images
  - bing images
```

You can add multiple engine names to the same category list. Engine names must match the names used by SearXNG exactly, including spaces where applicable.

For the full list of engines supported by SearXNG, see: [Configured engines](https://docs.searxng.org/user/configured_engines.html).

## Deprecated engine toggles

Older versions used per-engine type fields such as `engine_general` or `engine_images` with `enabled`/`disabled` style values. Those are deprecated in the current configuration model. The active model is the list-based default-disable approach described above.

Examples of valid engine names include:

- `google`
- `bing`
- `duckduckgo`
- `wikipedia`
- `github`
- `youtube`
- `reddit`
- `stackoverflow`
- `apple maps`
- `openstreetmap`
- `google_play_apps`

Names such as `startpage`, `qwant`, and `wolframalpha` should be double-checked before relying on them.

Engines not listed in a category remain enabled according to the upstream SearXNG defaults.

## Troubleshooting

- If the app starts but the web UI is not reachable, check your firewall rules and confirm that the host network setup is working.
- ⚠️ If you changed the port to something else then the standard 18080 the web UI button won't work correctly.⚠️
- If `searxng.local` does not resolve reliably, switch to `searxng.lan`.
- If an engine does not appear as expected, verify that its name in the configuration exactly matches the engine name in SearXNG.
- If something looks wrong, review the app logs, which print the generated settings on every boot.

## Home Assistant MQTT Discovery

This app publishes SearXNG statistics through Home Assistant MQTT Discovery. MQTT Discovery is the only entity registration method in version 1.2.0. The MQTT broker must be reachable from the app container.

### Enabling MQTT Discovery

1. Install and configure the Mosquitto broker app with a user(searxng) and password.
2. Make sure the MQTT integration is configured in Home Assistant.
3. Install or restart SearXNG. The app reads the broker host, port, username, and password from the Supervisor MQTT service granted by `mqtt:need`.
4. Keep **Enable Stats Entities** and **Enable Metrics Endpoint** enabled.

No MQTT username, password, host, or port can be entered in the SearXNG app configuration. These values are supplied exclusively by the HAOS `mqtt:need` service. The default Discovery prefix is `homeassistant` and the state prefix is `searxng`.

The statistics monitor uses the authenticated metrics endpoint. Keep **Enable
metrics endpoint** enabled when MQTT Discovery is enabled. The app stores
the metrics password separately from SearXNG's `server.secret_key`; it is
generated automatically and is not shown in the app configuration.

Metrics can be disabled with **Enable metrics endpoint**, for example when
entity registration is not needed. The endpoint is enabled by default for
backwards compatibility.

### Available Entities

Once enabled and connected to the broker, the following entities will be automatically created in Home Assistant:

- `sensor.searxng_requests` - Total number of search requests
- `sensor.searxng_average_response_time` - Average response time in milliseconds
- `sensor.searxng_engine_count` - Number of active search engines
- `sensor.searxng_engine_*` - Per-engine statistics (one sensor per enabled engine)
- `sensor.searxng_last_checked` - Time of the last metrics poll

Each sensor also has a `last_checked` attribute containing the UTC time of the
last metrics poll. The monitor polls every 60 seconds, so this attribute keeps
updating even when no new search has been performed and the metric values stay
the same.

### Using Entities in Home Assistant

#### In Dashboards
Display search statistics on your Home Assistant dashboard:
```yaml
type: entities
entities:
  - entity: sensor.searxng_requests
  - entity: sensor.searxng_average_response_time
```

#### In Automations
Create automations based on search activity:
```yaml
automation:
  - alias: "Alert on high response times"
    trigger:
      platform: numeric_state
      entity_id: sensor.searxng_average_response_time
      above: 500
    action:
      service: notify.mobile_app_phone
      data:
        message: "SearXNG response time is high: {{ states('sensor.searxng_average_response_time') }}ms"
```

#### In Templates
Use SearXNG stats in templates:
```yaml
template:
  - sensor:
      - name: "Search Activity Status"
        state: >
          {% if states('sensor.searxng_requests') | int > 100 %}
            High Activity
          {% elif states('sensor.searxng_requests') | int > 50 %}
            Medium Activity
          {% else %}
            Low Activity
          {% endif %}
```

### Disabling MQTT Discovery

To disable the monitor, set **Enable Stats Entities** to `off` and restart the app. MQTT Discovery is enabled automatically whenever the statistics monitor is enabled. Existing MQTT entities remain in Home Assistant until their discovery entries are removed manually.

The entity monitor process will not start if this option is disabled, saving system resources.

### Troubleshooting Entity Registration

- **Entities not appearing**: Check the app logs for broker connection errors and confirm that the MQTT integration uses the same discovery prefix.
- **Update delays**: Entities are refreshed every 60 seconds. This is the monitor polling interval; dashboard and Recorder refresh behavior is controlled by Home Assistant.
- **Missing engine entities**: Only engines that are enabled in the app configuration will have corresponding entities.
- **Broker unavailable**: The monitor keeps retrying through Paho's network loop. Entities show unavailable while the monitor is disconnected because the MQTT Last Will publishes `offline`.