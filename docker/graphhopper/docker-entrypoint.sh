#!/bin/sh
# docker-entrypoint.sh — GraphHopper startup wrapper
#
# Downloads the OSM PBF extract on first start if GH_OSM_URL is set.
# The graph cache persists in the named Docker volume (ghdata) so subsequent
# restarts reuse it and start in seconds.
#
# The cache only fits the configuration it was built with: GraphHopper refuses to
# start when profiles or encoded values changed. The image carries a fingerprint
# of everything that shapes the graph (config.yml, custom models, the patches to
# OpenRailRouting); a cache built with another fingerprint — or with none, i.e. by
# an older image — is dropped and rebuilt from the OSM file. That takes several
# minutes for Germany, during which routing is unavailable.
set -e

# GH_CONFIG / GH_OSM_FILE are only set by test/smoke.sh; the OSM file path must match
# datareader.file in the config.
CONFIG=${GH_CONFIG:-/graphhopper/config.yml}
OSM_FILE=${GH_OSM_FILE:-/data/map.osm.pbf}
GRAPH_CACHE=/data/graph-cache
FINGERPRINT_FILE=/data/graph-cache.fingerprint
IMAGE_FINGERPRINT=$(cat /graphhopper/fingerprint)

if [ ! -f "$OSM_FILE" ]; then
  if [ -z "${GH_OSM_URL:-}" ]; then
    echo "ERROR: $OSM_FILE not found and GH_OSM_URL is not set." >&2
    echo "Set GH_OSM_URL in .env to an OSM PBF URL." >&2
    echo "Example: https://download.geofabrik.de/europe/germany-latest.osm.pbf" >&2
    exit 1
  fi
  echo "Downloading OSM extract from ${GH_OSM_URL} ..."
  wget -q -O "${OSM_FILE}.tmp" "${GH_OSM_URL}" \
    && mv "${OSM_FILE}.tmp" "${OSM_FILE}"
  echo "Download complete."
fi

if [ -d "$GRAPH_CACHE" ] && [ "$(cat "$FINGERPRINT_FILE" 2>/dev/null || true)" != "$IMAGE_FINGERPRINT" ]; then
  echo "Routing configuration changed — dropping the graph cache, it is rebuilt now."
  rm -rf "$GRAPH_CACHE"
fi
echo "$IMAGE_FINGERPRINT" > "$FINGERPRINT_FILE"

exec java ${JAVA_OPTS:-} -jar /railway_routing.jar server "$CONFIG"
