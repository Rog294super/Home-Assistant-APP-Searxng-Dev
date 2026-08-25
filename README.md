# SearXNG Home Assistant app

[![Open your Home Assistant instance and show the add app repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FRog294super%2FHome-Assistant-APP-Searxng)

A Home Assistant OS app that runs the official [**SearXNG**](https://github.com/searxng/searxng) metasearch engine while staying as close as possible to the upstream project.

This app is designed to provide a lightweight, easy-to-maintain integration for Home Assistant users without modifying the core SearXNG application.

## Features

* Uses the official SearXNG Docker image.
* Runs directly on the Home Assistant host network.
* Automatically generates and persists a secure `secret_key`.
* Keeps configuration as close as possible to the upstream defaults.
* Supports enabling and disabling search engines through the Home Assistant configuration.
* **Automatic entity registration** — SearXNG statistics are registered as Home Assistant entities.
* Designed for minimal maintenance across future SearXNG releases.

## Design Philosophy

This app intentionally avoids maintaining a full copy of SearXNG's default `settings.yml`.

Instead it uses:

```yaml
use_default_settings: true
```

Only Home Assistant specific settings are generated during startup. This means future SearXNG updates automatically benefit from upstream improvements without requiring large configuration changes inside the app.

## Installation
Click the button above to add this repository to Home Assistant.

Alternatively, add the following repository manually:

https://github.com/Rog294super/Home-Assistant-APP-Searxng

1. Open **Settings → apps → app Store**.
2. Add this repository as a custom repository.
3. Install **SearXNG**.
4. Configure the app.
5. For entities also install a MQTT broker like MQTT Mosquitto broker and configure.
6. Start the app.

## Configuration

The app automatically generates a persistent `secret_key` during the first startup.

Common configuration options include:

* Base URL
* Instance name
* Search engine configuration
* **Enable Metrics** — Enable the authenticated metrics endpoint used by the SearXNG statistics monitor (default: enabled)
* **Enable Stats Entities** — Enable automatic registration of SearXNG statistics as Home Assistant entities (default: enabled)

For detailed information about entity registration and usage examples, see the [DOCS.md](searxng/DOCS.md#home-assistant-entity-registration) file.

## Project Goals

* Stay as close as possible to upstream SearXNG.
* Minimize maintenance.
* Avoid unnecessary dependencies.
* Keep configuration simple.
* Integrate cleanly with Home Assistant OS.

## License

MIT License

Copyright (c) 2026 Rog294super

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
