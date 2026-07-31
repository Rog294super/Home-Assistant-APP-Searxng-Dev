# Changelog

All notable changes to this Home Assistant SearXNG App are documented here.

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
