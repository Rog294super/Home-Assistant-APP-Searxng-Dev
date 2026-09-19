# We build straight on top of the official multi-arch SearXNG image rather
# than a Home Assistant base image, since it already ships the full Python
# search engine stack, PyYAML, and Granian. This image is a multi-arch
# manifest, so the same FROM line resolves correctly on amd64/aarch64 hosts.
# This image version should be updated with every version increase of the project. 
# https://docs.searxng.org/#
FROM searxng/searxng:2026.9.18-1f7711ef1

RUN /usr/local/searxng/.venv/bin/python -m ensurepip --upgrade && \
    /usr/local/searxng/.venv/bin/python -m pip install --no-cache-dir paho-mqtt

COPY run.sh /run.sh
COPY monitor.py /monitor.py
COPY validate_base_url.py /validate_base_url.py

RUN sed -i 's/\r$//' /run.sh && \
    chmod 755 /run.sh && \
    chmod 755 /monitor.py && \
    chmod 755 /validate_base_url.py

ENTRYPOINT ["/bin/sh", "/run.sh"]
