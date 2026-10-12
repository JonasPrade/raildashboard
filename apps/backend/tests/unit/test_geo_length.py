"""Backend port of the frontend length calculation (shared/geo/length.ts)."""

import json

from dashboard_backend.services.geo_length import compute_geojson_length_km


def test_empty_or_invalid_input_is_none():
    assert compute_geojson_length_km(None) is None
    assert compute_geojson_length_km("") is None
    assert compute_geojson_length_km("not json") is None


def test_no_line_geometry_is_none():
    point_fc = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [10, 51]}}
            ],
        }
    )
    assert compute_geojson_length_km(point_fc) is None


def test_one_degree_longitude_at_equator():
    km = compute_geojson_length_km(json.dumps({"type": "LineString", "coordinates": [[0, 0], [1, 0]]}))
    assert 110 < km < 112
    # Same rounding as the frontend (two decimals).
    assert km == round(km, 2)


def test_sums_features_and_multilines():
    fc = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 0]]}},
                {
                    "type": "Feature",
                    "geometry": {"type": "MultiLineString", "coordinates": [[[1, 0], [2, 0]]]},
                },
            ],
        }
    )
    assert 221 < compute_geojson_length_km(fc) < 223
