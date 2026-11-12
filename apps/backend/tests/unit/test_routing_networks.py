"""Network switches → GraphHopper request, route sections and stored origins.

The query custom model below is also sent by docker/graphhopper/test/smoke.sh to a real
router; keep both in step."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from dashboard_backend.services import routing_client as routing_client_module
from dashboard_backend.services.exceptions import RoutingNoPathError
from dashboard_backend.services.routing_client import RoutingClient
from dashboard_backend.services.routing_networks import (
    feature_origin,
    normalize_networks,
    route_line_features,
    route_sections,
    routing_request,
    status_totals_km,
)


def test_without_switches_existing_profile_and_no_model():
    for networks in (None, {}, {"construction": False, "proposed": False}):
        request = routing_request(networks)
        assert request.profile == "rail_default"
        assert request.custom_model is None


def test_switches_build_flex_request():
    both = routing_request({"construction": True, "proposed": True})
    assert both.profile == "rail_flex"
    assert both.custom_model == {
        "priority": [{"if": "railway_status == EXISTING", "multiply_by": "0.1"}]
    }

    proposed_only = routing_request({"proposed": True})
    assert proposed_only.custom_model["priority"] == [
        {"if": "railway_status == CONSTRUCTION", "multiply_by": "0"},
        {"if": "railway_status == EXISTING", "multiply_by": "0.1"},
    ]

    construction_only = routing_request({"construction": True})
    assert construction_only.custom_model["priority"] == [
        {"if": "railway_status == PROPOSED", "multiply_by": "0"},
        {"if": "railway_status == EXISTING", "multiply_by": "0.1"},
    ]


def test_unknown_network_rejected():
    with pytest.raises(ValueError):
        normalize_networks({"subway": True})


COORDS = [[10.0, 50.0], [10.02, 50.0], [10.05, 50.0], [10.08, 50.0], [10.1, 50.0]]


def test_sections_merge_runs_and_measure():
    details = {
        "railway_status": [
            [0, 1, "existing"],
            [1, 2, "proposed"],
            [2, 3, "proposed"],
            [3, 4, "existing"],
        ]
    }
    sections = route_sections(COORDS, details)
    assert [(s["track_status"], s["from_index"], s["to_index"]) for s in sections] == [
        ("existing", 0, 1),
        ("proposed", 1, 3),
        ("existing", 3, 4),
    ]
    assert sections[1]["length_km"] == pytest.approx(4.29, abs=0.02)
    totals = status_totals_km(sections)
    assert set(totals) == {"existing", "proposed"}
    assert totals["existing"] + totals["proposed"] == pytest.approx(7.15, abs=0.03)


def test_sections_without_details_count_as_existing():
    sections = route_sections(COORDS, None)
    assert [(s["track_status"], s["from_index"], s["to_index"]) for s in sections] == [
        ("existing", 0, 4)
    ]


def test_line_features_split_by_status_and_tag_origin():
    sections = route_sections(
        COORDS, {"railway_status": [[0, 2, "existing"], [2, 4, "construction"]]}
    )
    features = route_line_features(COORDS, sections)
    assert [f["geometry"]["coordinates"] for f in features] == [COORDS[0:3], COORDS[2:5]]
    assert [f["properties"] for f in features] == [
        {"geometry_source": "routing", "track_status": "existing"},
        {"geometry_source": "routing", "track_status": "construction"},
    ]
    assert [feature_origin(f) for f in features] == ["routing_existing", "routing_construction"]


def test_feature_origin_of_other_sources():
    assert feature_origin({"properties": {"geometry_source": "manual"}}) == "manual"
    assert feature_origin({"properties": {"geometry_source": "upload"}}) == "upload"
    assert feature_origin({"properties": {}}) == "unknown"
    assert feature_origin({}) == "unknown"


# --- HTTP shape of the request ----------------------------------------------------------


def _client_with(monkeypatch, handler) -> RoutingClient:
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        return real(*args, transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(routing_client_module.httpx, "AsyncClient", factory)
    return RoutingClient("http://gh:8989")


WAYPOINTS = [{"lat": 50.0, "lon": 10.0}, {"lat": 50.0, "lon": 10.2}]


def test_existing_network_uses_get_with_status_detail(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["params"] = request.url.params.multi_items()
        return httpx.Response(200, json={"paths": []})

    client = _client_with(monkeypatch, handler)
    asyncio.run(client.route(WAYPOINTS, "rail_default", {}))
    assert seen["method"] == "GET"
    assert ("profile", "rail_default") in seen["params"]
    assert ("details", "railway_status") in seen["params"]
    assert ("point", "50.0,10.0") in seen["params"]


def test_custom_model_uses_post(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"paths": []})

    client = _client_with(monkeypatch, handler)
    model = routing_request({"proposed": True}).custom_model
    asyncio.run(client.route(WAYPOINTS, "rail_flex", {}, custom_model=model))
    assert seen["method"] == "POST"
    assert seen["body"]["profile"] == "rail_flex"
    assert seen["body"]["points"] == [[10.0, 50.0], [10.2, 50.0]]
    assert seen["body"]["details"] == ["railway_status"]
    assert seen["body"]["custom_model"] == model


def test_bad_request_is_no_path(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "Connection between locations not found"})

    client = _client_with(monkeypatch, handler)
    with pytest.raises(RoutingNoPathError, match="Connection between locations"):
        asyncio.run(client.route(WAYPOINTS, "rail_default", {}))
