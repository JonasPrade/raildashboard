#!/bin/sh
# End-to-end check of the image: real entrypoint, real config.yml, real custom models,
# against the small network in planned-tracks.osm. Run by the `test` stage of the
# Dockerfile (part of `make test`).
#
# Test network (planned-tracks.osm; GraphHopper wants <osm> as the very first XML event,
# so the file carries no declaration and no comment):
#
# West to east along 50.0° N:
#   W - J1 = existing detour north (N1 N2 N3) = J2 - E - J3 = existing detour south (S1 S2 S3) = J4 - F
#        \________ proposed, via P ________/         \____ under construction, via C ____/
#
# The proposed track uses railway=proposed + proposed=rail, the one under construction
# the lifecycle prefix construction:railway=rail without a railway=* tag. Way 8 is a
# proposed way without a track type and must stay out of the graph.
#
# The rule it guards: routing on the existing network never uses, and never snaps to,
# a track that is proposed or under construction. Both are only used when asked for.
set -eu

BASE=http://localhost:8989
WEST="50.0,10.0"
EAST="50.0,10.2"
# 220 m north of the proposed track, 440 m south of the existing detour.
NEAR_PROPOSED="50.002,10.05"

mkdir -p /data
cp /test/planned-tracks.osm /data/planned-tracks.osm

# The production config with two changes: the test network as input, and no minimum
# network size (the test network is smaller than the 200 edges below which the
# production config drops a network as an unconnected fragment).
sed -e 's|datareader.file: /data/map.osm.pbf|datareader.file: /data/planned-tracks.osm|' \
    -e 's|prepare.min_network_size: 200|prepare.min_network_size: 0|' \
    /graphhopper/config.yml > /tmp/smoke-config.yml
grep -q 'planned-tracks.osm' /tmp/smoke-config.yml || { echo "FAIL: config.yml layout changed" >&2; exit 1; }
grep -q 'min_network_size: 0' /tmp/smoke-config.yml || { echo "FAIL: config.yml layout changed" >&2; exit 1; }

GH_CONFIG=/tmp/smoke-config.yml GH_OSM_FILE=/data/planned-tracks.osm \
    /docker-entrypoint.sh > /tmp/graphhopper.log 2>&1 &
SERVER=$!

fail() {
    echo "FAIL: $1" >&2
    echo "--- last server log lines ---" >&2
    tail -n 60 /tmp/graphhopper.log >&2 || true
    kill "$SERVER" 2>/dev/null || true
    exit 1
}

tries=0
until curl -fsS "$BASE/health" > /dev/null 2>&1; do
    tries=$((tries + 1))
    [ "$tries" -le 90 ] || fail "server did not come up within 180 s"
    kill -0 "$SERVER" 2>/dev/null || fail "server exited during start"
    sleep 2
done

route_default() { # from to
    curl -sS "$BASE/route?profile=rail_default&point=$1&point=$2&points_encoded=false&instructions=false&details=railway_status"
}

# The same request the backend sends for the network switches
# (dashboard_backend/services/routing_networks.py; tests/unit/test_routing_networks.py
# pins the statements below).
route_flex() { # construction proposed  (each true/false)
    statements='{ "if": "railway_status == EXISTING", "multiply_by": "0.1" }'
    [ "$1" = true ] || statements='{ "if": "railway_status == CONSTRUCTION", "multiply_by": "0" }, '"$statements"
    [ "$2" = true ] || statements='{ "if": "railway_status == PROPOSED", "multiply_by": "0" }, '"$statements"
    curl -sS -X POST "$BASE/route" -H 'Content-Type: application/json' -d '{
      "profile": "rail_flex",
      "points": [[10.0, 50.0], [10.2, 50.0]],
      "points_encoded": false, "instructions": false, "details": ["railway_status"],
      "custom_model": { "priority": ['"$statements"'] }
    }'
}

# expect <label> <response> <status that must appear ...> -- <status that must not appear ...>
expect() {
    label=$1; response=$2; shift 2
    echo "$response" | grep -q '"paths"' || fail "$label: no route: $response"
    must=1
    for status in "$@"; do
        if [ "$status" = "--" ]; then must=0; continue; fi
        if [ "$must" = 1 ]; then
            echo "$response" | grep -q "\"$status\"" || fail "$label: expected a section on $status tracks: $response"
        else
            if echo "$response" | grep -q "\"$status\""; then
                fail "$label: must not use $status tracks: $response"
            fi
        fi
    done
    echo "ok: $label"
}

expect "rail_default stays on the existing network" \
    "$(route_default "$WEST" "$EAST")" existing -- proposed construction
expect "rail_default does not snap to a proposed track" \
    "$(route_default "$NEAR_PROPOSED" "$EAST")" existing -- proposed construction
expect "rail_flex without switches stays on the existing network" \
    "$(route_flex false false)" existing -- proposed construction
expect "rail_flex with construction uses tracks under construction only" \
    "$(route_flex true false)" existing construction -- proposed
expect "rail_flex with proposed uses proposed tracks only" \
    "$(route_flex false true)" existing proposed -- construction
expect "rail_flex with both uses both" \
    "$(route_flex true true)" existing proposed construction --

# The graph cache carries the fingerprint of the configuration it was built with.
[ "$(cat /data/graph-cache.fingerprint)" = "$(cat /graphhopper/fingerprint)" ] \
    || fail "graph cache fingerprint was not written"

kill "$SERVER" 2>/dev/null || true
echo "smoke test passed"
