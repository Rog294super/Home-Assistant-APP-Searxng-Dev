# We build straight on top of the official multi-arch SearXNG image rather
# than a Home Assistant base image, since it already ships the full Python
# search engine stack. This image is a multi-arch manifest, so the same
# FROM line resolves correctly on amd64/aarch64/armv7 hosts.
FROM searxng/searxng:2026.7.31-057a77168

COPY run.sh /run.sh
COPY settings.yml.template /settings.yml.template

RUN sed -i 's/\r$//' /run.sh && \
    chmod 755 /run.sh

RUN ls -la /run.sh && head -n 1 /run.sh

ENTRYPOINT ["/bin/sh", "/run.sh"]
