# We build straight on top of the official multi-arch SearXNG image rather
# than a Home Assistant base image, since it already ships the full Python
# search engine stack, PyYAML, and Granian. This image is a multi-arch
# manifest, so the same FROM line resolves correctly on amd64/aarch64 hosts.
FROM searxng/searxng:2026.7.31-057a77168

COPY run.sh /run.sh

RUN sed -i 's/\r$//' /run.sh && \
    chmod 755 /run.sh

ENTRYPOINT ["/bin/sh", "/run.sh"]
