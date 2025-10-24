from __future__ import annotations

import pytest
from pydantic import ValidationError

from dashboard_backend.models.routes import route_hash
from dashboard_backend.schemas.routes import RouteIn


@pytest.mark.parametrize(
    "waypoints",
    [
        [
            {"lat": 51.1234567, "lon": 7.9876543},
            {"lat": 52.2222222, "lon": 8.1111111},
        ],
        [
            {"lat": 51.1234561, "lon": 7.9876549},
            {"lat": 52.2222228, "lon": 8.1111114},
        ],
    ],
)
def test_route_hash_stable_with_rounding(waypoints):
    hash_one = route_hash(waypoints, "rail_default", {}, "v1")
    hash_two = route_hash(waypoints, "rail_default", {}, "v1")
    assert hash_one == hash_two


def test_route_hash_changes_with_options():
    base = [
        {"lat": 51.0, "lon": 7.0},
        {"lat": 52.0, "lon": 8.0},
    ]
    default_hash = route_hash(base, "rail_default", {}, "v1")
    other_hash = route_hash(base, "rail_default", {"speed": 1}, "v1")
    assert default_hash != other_hash


def test_route_in_requires_two_waypoints():
    with pytest.raises(ValidationError):
        RouteIn(waypoints=[{"lat": 51.0, "lon": 7.0}])


def test_route_in_validates_coordinate_ranges():
    with pytest.raises(ValidationError):
        RouteIn(
            waypoints=[
                {"lat": 91.0, "lon": 7.0},
                {"lat": 51.0, "lon": 7.0},
            ]
        )
