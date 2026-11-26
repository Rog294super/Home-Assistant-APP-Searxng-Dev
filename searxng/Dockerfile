FROM valkey/valkey:9.2.0@sha256:1c2b25b09f354c66fe994733acdf12fcfd4bdf6f3bd92b88a93a70378d884056 AS valkey-runtime

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN mkdir -p /opt/valkey/bin /opt/valkey/lib && \
        cp /usr/local/bin/valkey-server /opt/valkey/bin/valkey-server && \
        ldd /usr/local/bin/valkey-server | \
            awk '/=> \// { print $3 } /ld-linux/ { print $1 }' | \
            sort -u | while read -r library; do cp -L "$library" /opt/valkey/lib/; done && \
        case "$(uname -m)" in \
            x86_64) test -x /opt/valkey/lib/ld-linux-x86-64.so.2 ;; \
            aarch64) test -x /opt/valkey/lib/ld-linux-aarch64.so.1 ;; \
            *) echo "Unsupported Valkey architecture: $(uname -m)" >&2; exit 1 ;; \
        esac

# We build straight on top of the official multi-arch SearXNG image rather
# than a Home Assistant base image, since it already ships the full Python
# search engine stack, PyYAML, Granian, and the searxng user. This is a multi-arch
# manifest, so the same FROM line resolves correctly on amd64/aarch64 hosts.
# This image version should be updated with every version increase of the project. 
# https://hub.docker.com/r/searxng/searxng/
# https://hub.docker.com/r/searxng/searxng/tags
FROM searxng/searxng:2026.11.23-a7163d091@sha256:a7fc607aa6723f5a8982105bcc5ffba4d1b9fc7c6922a31a88d6e4cba49ef12a

COPY --from=valkey-runtime /opt/valkey /opt/valkey
COPY valkey-server.sh /valkey-server.sh

ARG BUILD_ARCH
ARG BUILD_VERSION
LABEL io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}" \
    org.opencontainers.image.source="https://github.com/Rog294super/Home-Assistant-APP-Searxng"

COPY requirements.txt /tmp/searxng-requirements.txt
RUN /usr/local/searxng/.venv/bin/python -m ensurepip --upgrade && \
    /usr/local/searxng/.venv/bin/python -m pip install --require-hashes --no-cache-dir -r /tmp/searxng-requirements.txt && \
    rm /tmp/searxng-requirements.txt

COPY run.sh /run.sh
COPY monitor.py /monitor.py
COPY generate_settings.py /generate_settings.py
COPY validate_base_url.py /validate_base_url.py

RUN sed -i 's/\r$//' /run.sh && \
    chmod 755 /run.sh && \
    chmod 755 /valkey-server.sh && \
    chmod 755 /monitor.py && \
    chmod 755 /generate_settings.py && \
    chmod 755 /validate_base_url.py

ENTRYPOINT ["/bin/sh", "/run.sh"]