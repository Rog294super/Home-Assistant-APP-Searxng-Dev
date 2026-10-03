# We build straight on top of the official multi-arch SearXNG image rather
# than a Home Assistant base image, since it already ships the full Python
# search engine stack, PyYAML, and Granian. This image is a multi-arch
# manifest, so the same FROM line resolves correctly on amd64/aarch64 hosts.
# This image version should be updated with every version increase of the project. 
# https://docs.searxng.org/#
FROM searxng/searxng:2026.10.2-19ffbcd30@sha256:c642712fcedcdaa78fac44f71eada86aff510745826ba1bd1a368211fea2ce7f

ARG BUILD_ARCH
ARG BUILD_VERSION
LABEL io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}"

COPY requirements.txt /tmp/searxng-requirements.txt
RUN /usr/local/searxng/.venv/bin/python -m ensurepip --upgrade && \
    /usr/local/searxng/.venv/bin/python -m pip install --no-cache-dir -r /tmp/searxng-requirements.txt && \
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
