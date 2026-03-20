#!/bin/sh
# docker-entrypoint.sh — GraphHopper startup wrapper
#
# Downloads the OSM PBF extract on first start if GH_OSM_URL is set.
# The graph cache persists in the named Docker volume (ghdata) so subsequent
# restarts reuse it and start in seconds.
set -e

OSM_FILE=/data/map.osm.pbf

if [ ! -f "$OSM_FILE" ]; then
  if [ -z "${GH_OSM_URL:-}" ]; then
    echo "ERROR: /data/map.osm.pbf not found and GH_OSM_URL is not set." >&2
    echo "Set GH_OSM_URL in .env to an OSM PBF URL." >&2
    echo "Example: https://download.geofabrik.de/europe/germany-latest.osm.pbf" >&2
    exit 1
  fi
  echo "Downloading OSM extract from ${GH_OSM_URL} ..."
  wget -q -O "${OSM_FILE}.tmp" "${GH_OSM_URL}" \
    && mv "${OSM_FILE}.tmp" "${OSM_FILE}"
  echo "Download complete."
fi

exec java ${JAVA_OPTS:-} -jar /graphhopper.jar server /graphhopper/config.yml
