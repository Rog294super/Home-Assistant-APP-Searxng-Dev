# SearXNG for Home Assistant

This app installs SearXNG as a self-hosted search engine for Home Assistant OS or Supervised installations. It is designed to run directly on your host network, expose per-engine switches in the app configuration UI, and be reached through your own local domain names such as `searxng.lan` or `searxng.local` rather than through Home Assistant ingress.

## What this app provides

- Direct access at your Home Assistant host IP and port, without the usual Home Assistant ingress path
- Simple on/off toggles for individual search engines
- A local, privacy-friendly alternative to public search services
- Compatibility with a custom DNS setup or reverse proxy for cleaner URLs

## Installation

1. Add this repository URL to your Home Assistant app store:
   `https://github.com/Rog294super/Home-Assistant-APP-Searxng`
2. Open Home Assistant and go to **Settings → apps → app Store**.
3. Use **Check for updates**, then look for **SearXNG** under **Local apps**.
4. Install the app, configure the engine switches under **Configuration**, and then click **Start**.
5. Open the **Log** tab to confirm that the generated `settings.yml` was created correctly.

The first installation may take some time because the image is built on the device from the included Dockerfile.

## Accessing SearXNG

This app does not create hostnames for you. It runs on the host network, but you still need DNS or local name resolution to make names like `searxng.lan` or `searxng.local` point to your Home Assistant host.

### Using AdGuard Home as DNS

If you already run AdGuard Home, the easiest option is to add DNS rewrites:

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

The SearXNG container listens internally on port `18080`, and the app exposes that directly through the host network. Because of that, the URL usually includes a port unless you place it behind a reverse proxy.

If you want a cleaner URL such as `http://searxng.lan/`, consider using a reverse proxy such as Nginx or Caddy and forward traffic to your Home Assistant host IP and the SearXNG port.

## Configuring search engines

Each engine toggle in the app configuration must match the engine name used by SearXNG exactly. Some names contain spaces and are case-sensitive, so the value must be an exact match.

Examples that are commonly safe to use include:

- `google`
- `bing`
- `duckduckgo`
- `wikipedia`
- `github`
- `youtube`
- `reddit`
- `stackoverflow`

Names such as `startpage`, `qwant`, and `wolframalpha` should be double-checked before relying on them.

Engines not named in config.yaml but used by searxng default settings.yml will use their default value.

## Troubleshooting

- If the app starts but the web UI is not reachable, check your firewall rules and confirm that the host network setup is working.
- ⚠️ If you changed the port to something else then the standard 18080 the web UI button won't work correctly.⚠️
- If `searxng.local` does not resolve reliably, switch to `searxng.lan`.
- If an engine does not appear as expected, verify that its name in the configuration exactly matches the engine name in SearXNG.
- If something looks wrong, review the app logs, which print the generated settings on every boot.