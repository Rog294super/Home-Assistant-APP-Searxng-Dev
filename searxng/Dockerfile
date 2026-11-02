FROM valkey/valkey:9.1.2@sha256:418652cfb58ef879d4978c33553735d7147016032d5aefaa14c828e611eb9dfd AS valkey-runtime

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN mkdir -p /opt/valkey/bin /opt/valkey/lib && \
        cp /usr/local/bin/valkey-server /opt/valkey/bin/valkey-server && \
        ldd /usr/local/bin/valkey-server | \
            awk '/=> \// { print $3 } /^\/.*ld-linux/ { print $1 }' | \
            sort -u | while read -r library; do cp -L "$library" /opt/valkey/lib/; done

# We build straight on top of the official multi-arch SearXNG image rather
# than a Home Assistant base image, since it already ships the full Python
# search engine stack, PyYAML, Granian, and the searxng user. This is a multi-arch
# manifest, so the same FROM line resolves correctly on amd64/aarch64 hosts.
# This image version should be updated with every version increase of the project. 
# https://hub.docker.com/r/searxng/searxng/
# https://hub.docker.com/r/searxng/searxng/tags
FROM searxng/searxng:2026.10.29-cff884f98@sha256:dc2f7ed8a215b2f8244eaed083acdd50406f0de18bf43410cc460a4b511b7424

COPY --from=valkey-runtime /opt/valkey /opt/valkey
COPY valkey-server.sh /valkey-server.sh

ARG BUILD_ARCH
ARG BUILD_VERSION
LABEL io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}"

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
