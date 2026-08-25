# We build straight on top of the official multi-arch SearXNG image rather
# than a Home Assistant base image, since it already ships the full Python
# search engine stack, PyYAML, and Granian. This image is a multi-arch
# manifest, so the same FROM line resolves correctly on amd64/aarch64 hosts.
FROM searxng/searxng:2026.8.17-374939b88

RUN /usr/local/searxng/.venv/bin/python -m ensurepip --upgrade && \
    /usr/local/searxng/.venv/bin/python -m pip install --no-cache-dir paho-mqtt

COPY run.sh /run.sh
COPY monitor.py /monitor.py

RUN sed -i 's/\r$//' /run.sh && \
    chmod 755 /run.sh && \
    chmod 755 /monitor.py

ENTRYPOINT ["/bin/sh", "/run.sh"]
