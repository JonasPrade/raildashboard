"""Slim project-group list, simplified geometry endpoint, ETag and gzip.

Runs the real CRUD against the SQLite test DB (project + association tables
exist there; the PostGIS centroid column is a TEXT stand-in and never read).
"""

import json

import pytest

from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.services import geometry_simplify
from dashboard_backend.services.geometry_simplify import TOLERANCE_DEG


def _dense_line(n: int = 200) -> list[list[float]]:
    """A nearly straight line with many sub-metre wiggles (simplifies away)."""
    return [[7.0 + i * 0.001, 51.0 + (0.000001 if i % 2 else 0.0)] for i in range(n)]


def _feature_collection(*geometries: dict) -> str:
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {"source": "osm", "blob": "x" * 500}, "geometry": g}
                for g in geometries
            ],
        }
    )


@pytest.fixture(autouse=True)
def _fresh_geometry_cache():
    geometry_simplify.clear_cache()
    yield
    geometry_simplify.clear_cache()


@pytest.fixture()
def seeded(db_session):
    group = ProjectGroup(name="Bedarfsplan", short_name="BP", color="#123456")
    other = ProjectGroup(name="Andere", short_name="AN")

    parent = Project(
        name="ABS Hauptstrecke",
        project_number="1-001",
        description="Ausbau",
        length=42.5,
        elektrification=True,
        second_track=True,
        effects_cargo_rail=True,
        geojson_representation=_feature_collection(
            {"type": "LineString", "coordinates": _dense_line()},
            {"type": "Point", "coordinates": [7.123456789, 51.987654321, 88.0]},
        ),
    )
    db_session.add(parent)
    db_session.flush()
    child = Project(
        name="Teilabschnitt",
        superior_project_id=parent.id,
        geojson_representation=_feature_collection(
            {"type": "LineString", "coordinates": [[7.0, 51.0], [7.1, 51.1]]}
        ),
    )
    no_geometry = Project(name="Ohne Geometrie")
    draft = Project(
        name="Entwurf",
        is_draft=True,
        geojson_representation=_feature_collection(
            {"type": "Point", "coordinates": [8.0, 52.0]}
        ),
    )
    db_session.add_all([child, no_geometry, draft])
    group.projects = [parent, child, no_geometry, draft]
    other.projects = [parent]
    db_session.add_all([group, other])
    db_session.commit()
    return {"group": group, "parent": parent, "child": child, "no_geometry": no_geometry}


# ---------------------------------------------------------------------------
# GET /project_groups/ — slim list
# ---------------------------------------------------------------------------


def test_list_is_slim_and_excludes_drafts(client, seeded):
    resp = client.get("/api/v1/project_groups/")
    assert resp.status_code == 200
    groups = {g["short_name"]: g for g in resp.json()}

    projects = {p["name"]: p for p in groups["BP"]["projects"]}
    assert set(projects) == {"ABS Hauptstrecke", "Teilabschnitt", "Ohne Geometrie"}

    parent = projects["ABS Hauptstrecke"]
    assert set(parent) == {
        "id",
        "name",
        "project_number",
        "superior_project_id",
        "description",
        "length",
        "active_features",
    }
    assert parent["project_number"] == "1-001"
    assert parent["length"] == 42.5
    assert set(parent["active_features"]) == {"elektrification", "second_track", "effects_cargo_rail"}
    assert projects["Teilabschnitt"]["superior_project_id"] == parent["id"]
    assert projects["Ohne Geometrie"]["active_features"] == []

    assert "geojson_representation" not in resp.text
    assert [p["name"] for p in groups["AN"]["projects"]] == ["ABS Hauptstrecke"]


def test_single_group_is_slim(client, seeded):
    resp = client.get(f"/api/v1/project_groups/{seeded['group'].id}")
    assert resp.status_code == 200
    assert "geojson_representation" not in resp.text
    assert len(resp.json()["projects"]) == 3


def test_list_etag_revalidation(client, seeded):
    first = client.get("/api/v1/project_groups/")
    etag = first.headers["etag"]
    assert first.headers["cache-control"] == "no-cache"

    not_modified = client.get("/api/v1/project_groups/", headers={"If-None-Match": etag})
    assert not_modified.status_code == 304
    assert not_modified.content == b""

    # A proxy may weaken the tag after compressing — still a match.
    weak = client.get("/api/v1/project_groups/", headers={"If-None-Match": f"W/{etag}"})
    assert weak.status_code == 304

    stale = client.get("/api/v1/project_groups/", headers={"If-None-Match": '"outdated"'})
    assert stale.status_code == 200


def test_list_etag_changes_with_data(client, seeded, db_session):
    etag = client.get("/api/v1/project_groups/").headers["etag"]
    seeded["parent"].name = "ABS Hauptstrecke (neu)"
    db_session.commit()

    resp = client.get("/api/v1/project_groups/", headers={"If-None-Match": etag})
    assert resp.status_code == 200
    assert resp.headers["etag"] != etag


# ---------------------------------------------------------------------------
# GET /project_groups/{id}/geometries
# ---------------------------------------------------------------------------


def test_geometries_only_superior_by_default(client, seeded):
    resp = client.get(f"/api/v1/project_groups/{seeded['group'].id}/geometries")
    assert resp.status_code == 200
    body = resp.json()
    assert body["group_id"] == seeded["group"].id
    assert body["only_superior"] is True
    assert body["tolerance"] == TOLERANCE_DEG
    # Parent only: the child is a subproject, the other has no geometry,
    # the draft is never exposed.
    assert set(body["geometries"]) == {str(seeded["parent"].id)}


def test_geometries_all_projects(client, seeded):
    resp = client.get(
        f"/api/v1/project_groups/{seeded['group'].id}/geometries",
        params={"only_superior": "false"},
    )
    assert resp.status_code == 200
    assert set(resp.json()["geometries"]) == {str(seeded["parent"].id), str(seeded["child"].id)}


def test_geometries_are_simplified(client, seeded):
    resp = client.get(f"/api/v1/project_groups/{seeded['group'].id}/geometries")
    collection = resp.json()["geometries"][str(seeded["parent"].id)]

    assert collection["type"] == "FeatureCollection"
    by_type = {f["geometry"]["type"]: f for f in collection["features"]}
    assert set(by_type) == {"MultiLineString", "MultiPoint"}
    assert all(f["properties"] == {} for f in collection["features"])

    (line,) = by_type["MultiLineString"]["geometry"]["coordinates"]
    original = _dense_line()
    assert len(line) < len(original) / 10
    # End points survive simplification.
    assert line[0] == [7.0, 51.0]
    assert line[-1] == [round(original[-1][0], 5), round(original[-1][1], 5)]

    # Points are kept, rounded to 5 decimals and reduced to 2D.
    assert by_type["MultiPoint"]["geometry"]["coordinates"] == [[7.12346, 51.98765]]


def test_geometries_unknown_group_404(client):
    resp = client.get("/api/v1/project_groups/999999/geometries")
    assert resp.status_code == 404


def test_geometries_etag_revalidation(client, seeded):
    url = f"/api/v1/project_groups/{seeded['group'].id}/geometries"
    etag = client.get(url).headers["etag"]
    assert client.get(url, headers={"If-None-Match": etag}).status_code == 304


def test_geometries_are_much_smaller_than_source(client, seeded):
    resp = client.get(f"/api/v1/project_groups/{seeded['group'].id}/geometries")
    source = len(seeded["parent"].geojson_representation)
    assert len(resp.content) < source / 3


# ---------------------------------------------------------------------------
# GZip
# ---------------------------------------------------------------------------


def test_gzip_when_requested(client, seeded):
    resp = client.get("/api/v1/project_groups/", headers={"Accept-Encoding": "gzip"})
    assert resp.status_code == 200
    assert resp.headers["content-encoding"] == "gzip"
    assert "accept-encoding" in resp.headers["vary"].lower()
    # httpx decodes transparently — the body is still the JSON list.
    assert isinstance(resp.json(), list)


def test_no_gzip_without_accept_encoding(client, seeded):
    resp = client.get("/api/v1/project_groups/", headers={"Accept-Encoding": "identity"})
    assert resp.status_code == 200
    assert "content-encoding" not in resp.headers


def test_small_responses_are_not_gzipped(client):
    resp = client.get("/api/v1/project_groups/999999", headers={"Accept-Encoding": "gzip"})
    assert resp.status_code == 404
    assert "content-encoding" not in resp.headers
