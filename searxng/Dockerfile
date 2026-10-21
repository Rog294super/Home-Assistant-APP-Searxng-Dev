# We build straight on top of the official multi-arch SearXNG image rather
# than a Home Assistant base image, since it already ships the full Python
# search engine stack, PyYAML, Granian, and the searxng user. This is a multi-arch
# manifest, so the same FROM line resolves correctly on amd64/aarch64 hosts.
# This image version should be updated with every version increase of the project. 
# https://docs.searxng.org/#
FROM searxng/searxng:2026.10.17-decdfa6f7@sha256:9611ad42d304f5111c72b6c57e675c7b7735705a69b69faf63a8cb8d6d0b18ee

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
    chmod 755 /monitor.py && \
    chmod 755 /generate_settings.py && \
    chmod 755 /validate_base_url.py

ENTRYPOINT ["/bin/sh", "/run.sh"]
