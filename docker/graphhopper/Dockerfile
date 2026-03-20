FROM graphhopper/graphhopper:9.1

# Bake in the routing config so no bind mount is needed on the server.
COPY config.yml /graphhopper/config.yml

# Entrypoint downloads the OSM PBF from GH_OSM_URL on first start if not cached.
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
