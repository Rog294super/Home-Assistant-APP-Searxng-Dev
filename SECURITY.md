# Security Policy
The security of this project is taken seriously. We appreciate your efforts to responsibly disclose any findings and will make every effort to acknowledge your contributions.

## Supported Versions

Use this section to tell people about which versions of your project are
currently being supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| Latest release   | :white_check_mark: |
| Older releases   | :x:                |


## Reporting a Vulnerability

Please do not report security vulnerabilities through public GitHub issues, discussions, or pull requests.

Instead, report them privately through GitHub's private vulnerability reporting: 
[Report a vulnerability](https://github.com/Rog294super/Home-Assistant-APP-Searxng-Dev/security/advisories/new)

If for any reason you are unable to use GitHub's private vulnerability reporting, you may also reach out to the maintainer by email at rog294super@gmail.com.

When reporting, please include as much of the following as possible:

- A clear description of the vulnerability and its potential impact.
- Steps to reproduce, or a proof of concept.
- Affected version(s) of the app.
- Any known mitigations or workarounds.

## Disclosure Timeline

- Acknowledgement: you will receive an acknowledgement of your report within 96 hours is the project target, But acknowledgement can take longer.
- Initial assessment: a triage and initial severity assessment will be shared within 7 days of the acknowledgement.
- Fix and disclosure: valid reports are targeted for resolution and coordinated public disclosure within 90 days of the initial report, depending on complexity and impact.

You will be kept informed throughout the process and credited in the release notes for the fix, unless you prefer to remain anonymous.

## Out of Scope

The following are not considered security vulnerabilities in this project:

- Vulnerabilities in upstream or transitive dependencies. These are handled continuously by Renovate and addressed through regular dependency updates.
- Issues in Searxng itself; please report those directly to the [Searxng](https://github.com/searxng/searxng/security) project.
- Issues in Home Assistant, its Supervisor, or the operating system the app runs on; please report those to the [Home Assistant](https://github.com/home-assistant/core/security/policy) project.
- Issues only reproducible on app versions older than the latest release.
- Exposure resulting from deliberately publishing the app's ports to an untrusted network without further protection. The app assumes the administrator controls how it is exposed.
