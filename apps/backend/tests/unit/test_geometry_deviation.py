from __future__ import annotations

import pytest

from dashboard_backend.services.geometry_deviation import geometry_deviation


def _line(coords, kind="LineString"):
    return {"type": "Feature", "geometry": {"type": kind, "coordinates": coords}, "properties": {}}


ROUTE = [[10.0, 50.0], [10.1, 50.0], [10.2, 50.0]]


def test_same_alignment():
    result = geometry_deviation(ROUTE, [_line([[10.0, 50.0], [10.2, 50.0]])])
    assert result["route_within_corridor_share"] == 1.0
    assert result["existing_within_corridor_share"] == 1.0
    assert result["max_deviation_m"] == 0
    assert result["route_length_km"] == pytest.approx(14.3, abs=0.1)


def test_parallel_alignment_4_5_km_south():
    # 0.0405° latitude ≈ 4.5 km, like the Bielefeld – Seelze case.
    existing = [_line([[10.0, 49.9595], [10.2, 49.9595]])]
    result = geometry_deviation(ROUTE, existing)
    assert result["route_within_corridor_share"] == 0.0
    assert result["existing_within_corridor_share"] == 0.0
    assert result["max_deviation_m"] == pytest.approx(4478, abs=30)
    assert result["mean_deviation_m"] == pytest.approx(4478, abs=30)


def test_partial_cover_and_points_ignored():
    existing = [
        _line([[[10.0, 50.0], [10.1, 50.0]]], kind="MultiLineString"),
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [10.2, 50.0]}},
    ]
    result = geometry_deviation(ROUTE, existing)
    assert result["route_within_corridor_share"] == pytest.approx(0.507, abs=0.01)
    assert result["existing_within_corridor_share"] == 1.0
    assert result["max_deviation_m"] == pytest.approx(7150, abs=50)


def test_without_existing_lines():
    assert geometry_deviation(ROUTE, []) is None
    point = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [10.0, 50.0]}}
    assert geometry_deviation(ROUTE, [point]) is None
