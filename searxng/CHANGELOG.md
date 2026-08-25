# Changelog

All notable changes to this Home Assistant SearXNG App are documented here.

## 1.2.0

### Added
- **MQTT Discovery**: Statistics sensors are published with retained discovery and state messages.
  - Added configurable discovery prefix and state topic prefix; broker host, port, 
    and credentials are supplied automatically by HAOS.
  - Added MQTT availability with an `online` state and retained Last Will `offline` state.
  - Per-engine discovery topics are stable and stale engine configurations are cleared.
  - MQTT broker connection details are obtained automatically from the HAOS `mqtt:need` service.
  - **Home Assistant Entity Registration**: Automatic registration of SearXNG statistics as 
    Home Assistant entities (sensor platforms).
  - New `enable_stats_entities` configuration option to enable/disable entity registration 
    (default: enabled).
  - Entities created include: total requests, average response time, engine count, and per-engine
    statistics.
  - Entity monitor runs as a background service alongside SearXNG, similar to other HA integrations.
  - Entities can be used in Home Assistant automations, dashboards, and templates.
  - Added comprehensive documentation for entity usage and troubleshooting.
  - Added optional `disabled_engines` configuration for explicitly disabling
    SearXNG engines while preserving upstream defaults for all other engines.
  - Added translations for `enable_stats_entities` and `disabled_engines`
  - Use the Home Assistant Core API token for entity registration.
  - Enable Home Assistant API access for the add-on.


### Changed
- Modified `run.sh` to start both SearXNG and the MQTT statistics monitor service.
- Removed direct Home Assistant Core API entity registration; 
  MQTT Discovery is now the primary and only registration path.
- Entity polling uses a fixed 60-second interval; dashboard and Recorder
  refresh behavior remains controlled by Home Assistant.
- `run.sh` now uses `disabled_engines` only when the list is non-empty.
- Existing `engines` configuration remains supported for backwards
  compatibility and is used when `disabled_engines` is empty or absent.
- The legacy `engines` configuration will not be considered for deprecation
  before version 1.4.0.
- `Icon.png` changed to size: 128 x 128.
- `Logo.png` added with size 256 x 256
## 1.1.0

### Fixed
- Use the current `SUPERVISOR_TOKEN` environment variable for Home Assistant
  Core API entity registration.
- Store a separately generated password for the authenticated metrics endpoint
  instead of reusing SearXNG's `server.secret_key`.
- Add an `enable_metrics` option and use POSIX-compatible shell redirections.
- URL-encode entity IDs before sending Home Assistant API requests.
- Fixed a bug where `settings.yml` ended up with two top-level `search:` keys
  (one from the template for `safesearch`/`formats`, one appended for
  `autocomplete`). YAML doesn't merge duplicate keys, so the second one
  silently replaced the first — `safesearch` and the JSON API (`formats`)
  were being dropped on every boot where `autocomplete` was set, which is
  the default. Settings generation is now a single Python dict dumped once,
  so this class of bug can't happen again.
- `brave` and `wikidata` were still hardcoded into the `run.sh` engine loop
  even after being intentionally removed from `config.yaml`/`schema`/
  translations (see 1.0.9 notes below). They were silently force-enabled
  with no user control. The engine override list is now generated directly
  from whatever keys exist under `options.engines`, so `run.sh` can't drift
  out of sync with `config.yaml` again.
- `image_proxy` was present in `config.yaml`, `schema`, and translations but
  never actually read anywhere — the toggle did nothing. It's now wired
  into `server.image_proxy`(run.sh).

### Changed
- Switched the server process from `python -m searx.webapp --host ... --port
  ...` (Flask's built-in development server — the flags were silently
  ignored since that entry point doesn't parse CLI args at all) to Granian,
  the production WSGI server the official SearXNG container itself uses.
- `webui` now defaults to `http` instead of `https`, since this app doesn't
  terminate TLS anywhere. Fork the repo for yourself and change it back to `[PROTO:https]` if you're
  fronting it with a TLS-terminating reverse proxy.
- Removed `settings.yml.template` — settings generation now lives entirely
  in `run.sh` as a single YAML dump, removing the sed-substitution step.

## 1.0.9 Not publicly released

### Added
- Added a warning about port change to DOCS.md, Changing port will brake the Webui Button.
- Every app version comes now with a static version from searxng image, This makes everyone use the same version

### Changed
- Changed the wording from add-on to app in documentation to be persistent with Home assistant system.
- Wikidata is removed from config see [issue](https://github.com/searxng/searxng/issues/6454) and [commit.](https://github.com/Jodre11/cloud-searxng/commit/5e0e42b408d8adce8167d0665a6ebbef2af30c44)
- brave is removed from config because too many requests issues: [Example 1](https://github.com/searxng/searxng/issues/1651#event-24217888004), [Example 2.](https://github.com/searxng/searxng/issues/4653)

### Fixed


## 1.0.8

### Added
- Configurable SearXNG port.
- Configurable autocomplete provider.
- Additional search-engine configuration.
- Icon added.
- Changelog added.
- Install button README added.

### Changed
- Translation changed so as autocomplete.
- DOCS.md changed to fit better the situation.

### Fixed
- SearXNG now listens on the configured port.
- Changed default autocomplete because issue around duckduckgo as default Advice to use default Brave.
