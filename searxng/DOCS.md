# SearXNG for Home Assistant

This app installs SearXNG as a self-hosted search engine for Home Assistant OS or Supervised installations. It is designed to run directly on your host network, expose per-engine switches in the app configuration UI, and be reached through your own local domain names such as `searxng.lan` or `searxng.local` rather than through Home Assistant ingress.

## What this app provides

- Direct access at your Home Assistant host IP and port, without the usual Home Assistant ingress path.
- Per-category configuration for search engines to disable by default.
- A local, privacy-friendly alternative to public search services.
- Compatibility with a custom DNS setup or reverse proxy for cleaner URLs.
- Optional MQTT Discovery sensors for SearXNG statistics, using an MQTT broker such as Mosquitto.

## Installation

1. Add this repository URL to your Home Assistant app store:
   `https://github.com/Rog294super/Home-Assistant-APP-Searxng`
2. Open Home Assistant and go to **Settings → apps → app Store**.
3. Use **Check for updates**, then look for **SearXNG** under **Local apps**.
4. Install the app, configure its options, and then click **Start**.
5. Open the **Log** tab to confirm that the generated `settings.yml` was created correctly.

The first installation may take some time because the image is built on the device from the included Dockerfile.

## Accessing SearXNG

This app does not create hostnames for you. It runs on the host network, but you still need DNS or local name resolution to make names like `searxng.lan` or `searxng.local` point to your Home Assistant host.

SearXNG has no built-in user authentication in this app. Anyone who can reach its web port can use the search interface and API. Do not forward this port from the internet. For remote access, put it behind a reverse proxy that enforces authentication and TLS.

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

Windows clients often treat `.local` as a reserved multicast name suffix and may try to resolve it via mDNS or LLMNR before consulting your DNS server. This can make `searxng.local` unreliable on some machines. If you run into issues, `searxng.lan` is usually the more dependable choice.

For more background, see this article: [Why using .local as a domain name extension is a bad idea](https://community.veeam.com/blogs-and-podcasts-57/why-using-local-as-your-domain-name-extension-is-a-bad-idea-4828).

## Port and URL notes

The app listens on the fixed internal port `18080`. Home Assistant uses the host-network interface directly, so the service is available on `http://<HOME_ASSISTANT_HOST>:18080/` unless you place a reverse proxy in front of it. The **Open Web UI** link and watchdog use the same fixed port, which keeps the app metadata and runtime behavior consistent.

If you want a cleaner URL such as `http://searxng.lan/`, consider using a reverse proxy such as Nginx Proxy Manager or Caddy and forward traffic to your Home Assistant host IP on port `18080`.

## JSON search API

The app enables both the HTML interface and JSON search API by default. Disable **Enable JSON API** when the service should expose only the HTML interface. The generated SearXNG settings are updated immediately when the option changes and the app is restarted.

## Configuring search engines

Use the `disabled_engines_<category>` options to disable engines by default in a category. Available categories are `general`, `images`, `videos`, `news`, `maps`, `music`, `it`, `science`, `files`, and `social_media`. Enter exact SearXNG engine names as a comma-separated list, for example `google, bing` in `disabled_engines_general`. Engine names can contain spaces and may be case-sensitive; use the names from the [SearXNG engine list](https://docs.searxng.org/user/configured_engines.html).

Engines not listed in these options keep their upstream SearXNG defaults. The legacy `disabled_engines` list and `engines` switch map remain available for compatibility, but are planned for removal in version `1.4.0`. Move any legacy settings to the per-category `disabled_engines_<category>` options before upgrading to that version. If at least one per-category list is non-empty, it takes precedence over both legacy options.

## Troubleshooting

- If the app starts but the web UI is not reachable, check your firewall rules and confirm that the host network setup is working.
- The app always listens on port `18080`. Keep the reverse proxy or DNS entry aligned with that port.
- If `searxng.local` does not resolve reliably, switch to `searxng.lan`.
- If an engine does not appear as expected, verify that its name in the configuration exactly matches the engine name in SearXNG.
- If something looks wrong, review the app logs, which print the generated settings on every boot.

## Home Assistant MQTT Discovery

This app publishes SearXNG statistics through Home Assistant MQTT Discovery, which is its entity registration method. The MQTT broker must be reachable from the app container.

### Enabling MQTT Discovery

1. Install and configure the Mosquitto broker app with a user(searxng) and password.
2. Make sure the MQTT integration is configured in Home Assistant.
3. Install or restart SearXNG. When discovery is enabled, the monitor reads the broker host, port, username, and password from the optional Supervisor MQTT service requested by `mqtt:want`.
4. Enable all three options: **Enable Stats Entities**, **Enable Metrics Endpoint**, and **Enable MQTT Discovery**.

The monitor starts only when all three options are enabled. **Enable Stats Entities** controls whether the monitor runs, **Enable Metrics Endpoint** enables the authenticated SearXNG endpoint it reads, and **Enable MQTT Discovery** allows it to publish entities. If any one is disabled, SearXNG itself continues running, but the monitor does not start.

No MQTT username, password, host, or port can be entered in the SearXNG app configuration. These values are supplied exclusively by the HAOS MQTT service. When the Supervisor MQTT service requests SSL, the monitor enables TLS automatically. The default Discovery prefix is `homeassistant` and the state prefix is `searxng`.

The statistics monitor uses the authenticated metrics endpoint. Keep **Enable
metrics endpoint** enabled to receive stats entities. If metrics are disabled,
the app keeps SearXNG running and skips the statistics monitor until metrics
are enabled again. The app stores
the metrics password separately from SearXNG's `server.secret_key`; it is
generated automatically and is not shown in the app configuration.

Metrics can be disabled with **Enable metrics endpoint** even when stats
entities remain enabled. Those entities will not update until metrics are
enabled again; the search service remains available.

### Available Entities

Once enabled and connected to the broker, the following entities will be automatically created in Home Assistant:

- `sensor.searxng_requests` - Total number of search requests
- `sensor.searxng_average_response_time` - Median per-engine response time, averaged across engines, in milliseconds. The entity ID is retained for compatibility.
- `sensor.searxng_engine_count` - Number of active search engines
- `sensor.searxng_last_checked` - Time of the most recent metrics check
- `sensor.searxng_engine_*` - Per-engine statistics (one sensor per enabled engine)

Per-engine sensors are discovered but disabled by default in Home Assistant. Enable the individual entities in the entity settings if you want to use them.

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

To disable MQTT entity publishing, set **Enable MQTT Discovery** to `off` and restart the app. You can also stop the monitor by disabling **Enable Stats Entities** or **Enable Metrics Endpoint**. Existing MQTT entities may remain in Home Assistant; remove their discovery entries manually if needed.

The entity monitor process will not start if stats entities or MQTT Discovery are disabled, saving system resources.

### Troubleshooting Entity Registration

- **Entities not appearing**: Check the app logs for broker connection errors and confirm that the MQTT integration uses the same discovery prefix.
- **Update delays**: Entities are refreshed every 60 seconds. This is the monitor polling interval; dashboard and Recorder refresh behavior is controlled by Home Assistant.
- **Missing engine entities**: Only engines that are enabled in the app configuration will have corresponding entities.
- **Supervisor MQTT service unavailable at startup**: The monitor retries fetching the service configuration up to 12 times, waiting 5 seconds between attempts. If it still cannot get a broker host, MQTT is disabled for that monitor process; restart the app after fixing the service.
- **Broker disconnects after a successful connection**: Paho's network loop attempts to reconnect. The retained MQTT Last Will marks the entities offline while disconnected; they return online after reconnection.