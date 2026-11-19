"""OSM stops of S-Bahn/Stadtbahn, U-Bahn and tram → operational points (services/osm_stops.py)."""

from __future__ import annotations

from dashboard_backend.services.osm_stops import (
    KnownPoint,
    normalize_name,
    stop_network,
    stops_from_overpass,
)


def node(id_, lat, lon, **tags):
    return {"type": "node", "id": id_, "lat": lat, "lon": lon, "tags": tags}


def test_network_from_tags():
    assert stop_network({"railway": "station", "station": "subway"}) == "subway"
    assert stop_network({"railway": "halt", "station": "light_rail"}) == "light_rail"
    assert stop_network({"railway": "tram_stop"}) == "tram"
    assert stop_network({"railway": "station"}) is None
    assert stop_network({"railway": "station", "station": "train"}) is None


def test_tram_stop_directions_merge_to_one_point():
    stops = stops_from_overpass(
        [
            node(20, 52.5000, 13.4000, railway="tram_stop", name="Alexanderplatz"),
            node(10, 52.5004, 13.4004, railway="tram_stop", name="Alexanderplatz"),
            node(30, 52.5200, 13.4000, railway="tram_stop", name="Alexanderplatz"),
        ]
    )
    assert [(s.op_id, s.network) for s in stops] == [("OSM-n10", "tram"), ("OSM-n30", "tram")]
    assert stops[0].latitude == 52.5002
    assert stops[0].longitude == 13.4002


def test_same_name_in_other_network_stays_separate():
    stops = stops_from_overpass(
        [
            node(1, 52.5, 13.4, railway="station", station="subway", name="Alexanderplatz"),
            node(2, 52.5, 13.4, railway="tram_stop", name="Alexanderplatz"),
        ]
    )
    assert sorted(s.network for s in stops) == ["subway", "tram"]


def test_way_center_and_unnamed_skipped():
    stops = stops_from_overpass(
        [
            {
                "type": "way",
                "id": 7,
                "center": {"lat": 53.55, "lon": 10.0},
                "tags": {"railway": "station", "station": "subway", "name": "Jungfernstieg"},
            },
            node(8, 53.6, 10.0, railway="tram_stop"),
            {"type": "node", "id": 9, "tags": {"railway": "tram_stop", "name": "Ohne Lage"}},
        ]
    )
    assert [(s.op_id, s.name, s.type) for s in stops] == [("OSM-w7", "Jungfernstieg", "station")]


def test_light_rail_station_in_rinf_is_skipped():
    known = [KnownPoint("Berlin Treptower Park", 52.4935, 13.4613)]
    stops = stops_from_overpass(
        [
            node(1, 52.4934, 13.4615, railway="station", station="light_rail", name="S Treptower Park"),
            node(2, 52.4870, 13.4700, railway="station", station="light_rail", name="Sonnenallee"),
            node(3, 52.4934, 13.4615, railway="station", station="subway", name="Treptower Park"),
        ],
        known,
    )
    assert [(s.name, s.network) for s in stops] == [
        ("Sonnenallee", "light_rail"),
        ("Treptower Park", "subway"),
    ]


def test_normalize_name():
    assert normalize_name("S+U Alexanderplatz (Berlin)") == "alexanderplatz"
    assert normalize_name("U-Bahnhof Hermannplatz") == "hermannplatz"
    assert normalize_name("S Treptower Park") == "treptower park"
