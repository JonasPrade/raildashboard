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
# proposed way without a track type: in the graph as railway_class OTHER, never used
# unless the request asks for it.
#
# Track classes, a bundle of parallel straight lines from 10.0 to 10.1, not connected:
#   50.0512 tram · 50.0506 light_rail · 50.0500 rail · 50.0494 subway · 50.0488 narrow_gauge
# A chain at 50.06: light_rail 10.0-10.05, then tram 10.05-10.1.
# At 50.07: rail 10.0-10.03, an untyped proposed track 10.03-10.07 (way 302), rail
# 10.07-10.1, and an existing detour north of the proposed track.
# Combined mode (bridge_gaps, EK-2026-389):
#   50.08: rail 10.0-10.1 straight and a slower light_rail line bowing north between
#          the same two nodes;
#   50.09: light_rail 10.0-10.04, rail 10.04-10.06 (track shared with main line
#          trains, as at Birkenwerder), light_rail 10.06-10.1.
#
# The rules it guards: routing on the existing network never uses, and never snaps to,
# a track that is proposed or under construction, nor one of another track class
# (light_rail, subway, tram, narrow_gauge, untyped). Each is only used when asked for,
# and then only the classes asked for.
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
    curl -sS "$BASE/route?profile=rail_default&point=$1&point=$2&points_encoded=false&instructions=false&details=railway_status&details=railway_class"
}

# The query custom model the backend builds (dashboard_backend/services/routing_networks.py;
# tests/unit/test_routing_networks.py pins the same statements):
# statements <track classes, comma-separated> <construction true/false> <proposed true/false>
#            [<bridge_gaps true/false>]
statements() {
    out=""
    for class in rail light_rail subway tram narrow_gauge unknown; do
        case ",$1," in
            *",$class,"*) ;;
            *)
                enum=$(echo "$class" | tr 'a-z' 'A-Z')
                factor=0
                [ "${4:-false}" = true ] && factor=0.01
                [ "$class" = unknown ] && enum=OTHER && factor=0
                out="$out{ \"if\": \"railway_class == $enum\", \"multiply_by\": \"$factor\" }, " ;;
        esac
    done
    [ "$2" = true ] || out="$out{ \"if\": \"railway_status == CONSTRUCTION\", \"multiply_by\": \"0\" }, "
    [ "$3" = true ] || out="$out{ \"if\": \"railway_status == PROPOSED\", \"multiply_by\": \"0\" }, "
    if [ "$2" = true ] || [ "$3" = true ]; then
        out="$out{ \"if\": \"railway_status == EXISTING\", \"multiply_by\": \"0.1\" }, "
    fi
    echo "${out%, }"
}

# route_flex <from lon,lat> <to lon,lat> <classes> <construction> <proposed> [<bridge_gaps>]
route_flex() {
    curl -sS -X POST "$BASE/route" -H 'Content-Type: application/json' -d '{
      "profile": "rail_flex", "ch.disable": true,
      "points": [['"$1"'], ['"$2"']],
      "points_encoded": false, "instructions": false,
      "details": ["railway_status", "railway_class"],
      "custom_model": { "priority": ['"$(statements "$3" "$4" "$5" "${6:-false}")"'] }
    }'
}

# expect <label> <response> <value that must appear ...> -- <value that must not appear ...>
# Values are path detail values (status or track class), matched as quoted JSON strings.
expect() {
    label=$1; response=$2; shift 2
    echo "$response" | grep -q '"paths"' || fail "$label: no route: $response"
    must=1
    for value in "$@"; do
        if [ "$value" = "--" ]; then must=0; continue; fi
        if [ "$must" = 1 ]; then
            echo "$response" | grep -q "\"$value\"" || fail "$label: expected a section on $value tracks: $response"
        else
            if echo "$response" | grep -q "\"$value\""; then
                fail "$label: must not use $value tracks: $response"
            fi
        fi
    done
    echo "ok: $label"
}

# expect_no_path <label> <response>
expect_no_path() {
    echo "$2" | grep -q '"paths"' && fail "$1: expected no route: $2"
    echo "ok: $1"
}

OTHER_CLASSES="light_rail subway tram narrow_gauge other"

# --- lifecycle status (50.0) ---
W=10.0,50.0
E=10.2,50.0
expect "rail_default stays on the existing network" \
    "$(route_default "$WEST" "$EAST")" existing rail -- proposed construction $OTHER_CLASSES
expect "rail_default does not snap to a proposed track" \
    "$(route_default "$NEAR_PROPOSED" "$EAST")" existing -- proposed construction
expect "rail_flex without switches stays on the existing network" \
    "$(route_flex $W $E rail false false)" existing -- proposed construction $OTHER_CLASSES
expect "rail_flex with construction uses tracks under construction only" \
    "$(route_flex $W $E rail true false)" existing construction -- proposed $OTHER_CLASSES
expect "rail_flex with proposed uses proposed tracks only" \
    "$(route_flex $W $E rail false true)" existing proposed -- construction $OTHER_CLASSES
expect "rail_flex with both uses both" \
    "$(route_flex $W $E rail true true)" existing proposed construction --

# --- track classes (bundle at 50.05; points on the rail line) ---
BW=10.0,50.05
BE=10.1,50.05
expect "rail_default stays on rail next to parallel tracks of other classes" \
    "$(route_default 50.0504,10.0 50.0504,10.1)" rail -- $OTHER_CLASSES
for class in light_rail subway tram narrow_gauge; do
    expect "rail_flex with $class uses $class only, snapped next to a rail track" \
        "$(route_flex $BW $BE $class false false)" "$class" -- rail other $(echo "$OTHER_CLASSES" | tr ' ' '\n' | grep -vx "$class")
done
expect "rail_flex with light_rail + tram combines both" \
    "$(route_flex 10.0,50.06 10.1,50.06 light_rail,tram false false)" light_rail tram -- rail
expect_no_path "rail_flex with light_rail alone does not switch to tram" \
    "$(route_flex 10.0,50.06 10.1,50.06 light_rail false false)"

# --- planned tracks without a type (50.07) ---
UW=10.0,50.07
UE=10.1,50.07
expect "rail_default avoids the untyped proposed track" \
    "$(route_default 50.07,10.0 50.07,10.1)" rail -- other proposed
expect "rail_flex with proposed but without unknown avoids the untyped track" \
    "$(route_flex $UW $UE rail false true)" rail -- other
expect "rail_flex with proposed + unknown uses the untyped track" \
    "$(route_flex $UW $UE rail,unknown false true)" rail other proposed --
expect "rail_flex with light_rail + proposed stays off rail" \
    "$(route_flex 10.0,50.06 10.1,50.06 light_rail,tram false true)" light_rail tram -- rail

# --- combined mode: bridge gaps over other classes (50.08, 50.09) ---
expect "bridge_gaps keeps to light_rail where it runs parallel to a faster rail line" \
    "$(route_flex 10.0,50.08 10.1,50.08 light_rail false false true)" light_rail -- rail
expect_no_path "light_rail alone stops at a stretch mapped as rail" \
    "$(route_flex 10.0,50.09 10.1,50.09 light_rail false false)"
expect "bridge_gaps crosses the rail stretch between two light_rail lines" \
    "$(route_flex 10.0,50.09 10.1,50.09 light_rail false false true)" light_rail rail -- tram subway
expect "bridge_gaps from rail crosses a light_rail stretch" \
    "$(route_flex 10.05,50.09 10.1,50.09 rail false false true)" rail light_rail --

# The graph cache carries the fingerprint of the configuration it was built with.
[ "$(cat /data/graph-cache.fingerprint)" = "$(cat /graphhopper/fingerprint)" ] \
    || fail "graph cache fingerprint was not written"

kill "$SERVER" 2>/dev/null || true
echo "smoke test passed"
