# Changelog

All notable changes to this Home Assistant SearXNG App are documented here.

## 1.3.0

### Message DEV
**LEGACY ENGINES**: It has been decided that the legacy `engines` configuration will be removed earlier than
  1.4.0.
  Possibly already by the next big update which as major update will be named V1.4.0.
  If there is no next big update but enough small updates, To the level that the app will reach V1.4.0 because incrementations, it will also be removed.
  If the removal happens earlier this will possibly be announced one update before.
**LEGACY DISABLED_ENGINES**: With the addition of seperate category disabled engines, The following
    configuration `disabled_engines` will be removed at the same time as `engines`.
    Save your disabled engines in the specific category for the engines.

### Added
- Added separate comma-separated disabled-engine fields for the general, images,
  videos, news, maps, music, IT, science, files, and social media categories.
  These are plain text fields in the Home Assistant configuration, and the
  translations list the valid engine names for each category.
- Engine settings generation now reads the per-category fields and removes
  duplicate engine names. If none are configured, the existing global
  `disabled_engines` option is used; if that is also empty, the legacy
  `engines` options are used. With no engine overrides, SearXNG defaults apply.
- Extracted settings generation into a separately tested Python module.
- Added Dependabot updates for the Docker base image, Python dependencies, and
  GitHub Actions.

### Changed
- Added a startup sanity check for the `base_url` option. Values without an
  `http://` or `https://` prefix, or with a malformed double-slash path,
  are now rejected with a clear warning in the logs instead of silently
  starting SearXNG with a broken base URL that can trigger CSRF and redirect
  issues in the browser.
- The `autocomplete` provider is now selected from a dropdown.
- The default `base_url` is now empty. When no engine overrides are set,
  SearXNG uses its upstream engine defaults; legacy engine options remain
  supported for compatibility.
- MQTT service details are now fetched by the monitor with retries instead
  of delaying SearXNG startup or exporting broker credentials to Granian.
  MQTT is requested as an optional service.
- MQTT statistics are marked as diagnostic; per-engine sensors are disabled
  by default and expire after three polling intervals. The response-time
  sensor is now named Median Response Time; its existing entity ID is kept.
- Updated Home Assistant metadata with application startup, an MQTT `want`
  dependency, and a health watchdog. Removed the unused writable configuration
  mapping and unnecessary Supervisor API permission.
- Pinned the SearXNG base image by multi-architecture digest and `paho-mqtt`
  to version 2.1.0. Added the required Home Assistant Docker labels.
- Pinned CI actions to commit SHAs, limited workflow permissions, and added
  LF line endings for shell scripts. The redundant scheduled issue-comment
  workflow was removed.

### Fixed
- Redacted `secret_key` and `open_metrics` from startup logs and restricted
  permissions on generated secrets and settings files.
- Fixed the monitor restart loop when stats entities are disabled and added
  graceful SIGTERM/SIGINT cleanup, including retained MQTT offline status.
- The app now rejects enabled stats entities when the metrics endpoint is
  disabled, avoiding repeated failed metrics requests.
- Added a warning in the documentation not to expose the unauthenticated search
  service directly to the internet.

## 1.2.1

### Added
- Added per-category disabled-engine fields while retaining the existing
  `disabled_engines` list and `engines` switches for compatibility.

### Fixed
- The statistics monitor no longer restarts when stats entities are disabled.
- Disabling metrics while stats entities are enabled now skips the monitor
  without stopping the SearXNG search service.

## 1.2.0

### Added
- **MQTT Discovery**: Statistics sensors are published with retained discovery and state messages.
  - Added configurable discovery prefix and state topic prefix; broker host, port, 
    and credentials are supplied automatically by HAOS.
  - Added `enable_mqtt_discovery` configuration option to enable/disable MQTT Discovery
    (default: enabled).
  - Added MQTT availability with an `online` state and retained Last Will `offline` state.
  - Per-engine discovery topics are stable and stale engine configurations are cleared.
  - MQTT broker connection details are obtained automatically from the HAOS `mqtt:need` service.
  - Added translations for `enable_mqtt_discovery`.
- **Home Assistant Entity Registration**: Automatic registration of SearXNG statistics as Home Assistant entities (sensor platforms).
  - New `enable_stats_entities` configuration option to enable/disable entity registration 
    (default: enabled).
  - Entities created include: total requests, average response time, engine count, and per-engine
    statistics.
  - Entity monitor runs as a background service alongside SearXNG, similar to other HA integrations.
  - Entities can be used in Home Assistant automations, dashboards, and templates.
  - Added comprehensive documentation for entity usage and troubleshooting.
  - Added optional `disabled_engines` configuration for explicitly disabling
    SearXNG engines while preserving upstream defaults for all other engines.
  - Added translations for `enable_stats_entities` and `disabled_engines`.

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
