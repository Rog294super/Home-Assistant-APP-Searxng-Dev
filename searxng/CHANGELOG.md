# Changelog

All notable changes to this Home Assistant SearXNG App are documented here.

## 1.1.0

### Fixed
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
  into `server.image_proxy`.

### Changed
- Switched the server process from `python -m searx.webapp --host ... --port
  ...` (Flask's built-in development server — the flags were silently
  ignored since that entry point doesn't parse CLI args at all) to Granian,
  the production WSGI server the official SearXNG container itself uses.
- `webui` now defaults to `http` instead of `https`, since this app doesn't
  terminate TLS anywhere. Fork the repo and change it back to `[PROTO:https]` if you're
  fronting it with a TLS-terminating reverse proxy.
- Removed `settings.yml.template` — settings generation now lives entirely
  in `run.sh` as a single YAML dump, removing the sed-substitution step.

## 1.0.9

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
