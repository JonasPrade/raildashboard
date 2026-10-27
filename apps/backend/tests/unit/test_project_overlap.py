"""Overlapping project lines and their map lanes
(docs/features/feature-map-overlapping-geometries.md → B1).

Geometry checks are pure; the persistence checks run the real CRUD against an
in-memory SQLite schema.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from dashboard_backend.crud.projects.projects import update_project
from dashboard_backend.models.associations.project_to_constituency import ProjectToConstituency
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_map_geometry import (
    ProjectMapGeometry,
    ProjectOverlap,
)
from dashboard_backend.services import project_overlap as po
from dashboard_backend.services.geometry_simplify import simplify_geojson_text

M_LAT = 110_574.0  # metres per degree latitude


def _line(start_lon: float, end_lon: float, lat: float = 51.0, offset_m: float = 0.0, steps: int = 50):
    """An east-west line at *lat*, shifted north by *offset_m* metres."""
    shifted = lat + offset_m / M_LAT
    return [
        [start_lon + (end_lon - start_lon) * i / steps, shifted] for i in range(steps + 1)
    ]


def _text(*lines: list[list[float]]) -> str:
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {}, "geometry": {"type": "LineString", "coordinates": line}}
                for line in lines
            ],
        }
    )


def _lines(*lines):
    return po.project_lines(_text(*lines))


@pytest.fixture(autouse=True)
def _fresh_cache():
    po.clear_cache()
    yield
    po.clear_cache()


# ── geometry ────────────────────────────────────────────────────────────────


class TestMeasureOverlap:
    def test_identical_lines_share_their_whole_length(self):
        line = _line(9.0, 9.1)  # ~7 km at 51°N
        overlap = po.measure_overlap(_lines(line), _lines(line))
        assert overlap.shared_km == pytest.approx(7.0, rel=0.02)
        assert overlap.share_a == pytest.approx(1.0, abs=0.01)
        assert po.is_overlap(overlap)

    def test_parallel_routing_ten_metres_apart_overlaps(self):
        overlap = po.measure_overlap(_lines(_line(9.0, 9.1)), _lines(_line(9.0, 9.1, offset_m=10)))
        assert po.is_overlap(overlap)

    def test_separate_line_forty_metres_apart_does_not_overlap(self):
        overlap = po.measure_overlap(_lines(_line(9.0, 9.1)), _lines(_line(9.0, 9.1, offset_m=40)))
        assert overlap.shared_km == 0
        assert not po.is_overlap(overlap)

    def test_opposite_direction_still_overlaps(self):
        line = _line(9.0, 9.1)
        assert po.is_overlap(po.measure_overlap(_lines(line), _lines(line[::-1])))

    def test_crossing_lines_do_not_overlap(self):
        east_west = _line(9.0, 9.1)
        north_south = [[9.05, 50.95], [9.05, 51.05]]
        overlap = po.measure_overlap(_lines(east_west), _lines(north_south))
        assert overlap.shared_km < 0.1
        assert not po.is_overlap(overlap)

    def test_short_project_under_a_long_one_overlaps(self):
        # ~300 m: below 500 m, but its whole length runs on the long line (W4).
        short = _line(9.05, 9.0543, steps=5)
        overlap = po.measure_overlap(_lines(_line(9.0, 9.1)), _lines(short))
        assert overlap.shared_km < po.MIN_SHARED_KM
        assert po.is_overlap(overlap)

    def test_tiny_shared_piece_does_not_overlap(self):
        # ~70 m: half of the shorter line, but under the 100 m floor.
        tiny = _line(9.05, 9.051, steps=2)
        assert not po.is_overlap(po.measure_overlap(_lines(_line(9.0, 9.1)), _lines(tiny)))

    def test_short_touch_of_a_long_line_does_not_overlap(self):
        # Two long lines meeting end to end share ~200 m: neither 500 m nor half.
        a = _line(9.0, 9.1)
        b = _line(9.0972, 9.2)
        assert not po.is_overlap(po.measure_overlap(_lines(a), _lines(b)))

    def test_duplicate_sections_count_once(self):
        line = _line(9.0, 9.1)
        doubled = _lines(line, line)
        assert po.line_km(doubled) == pytest.approx(po.line_km(_lines(line)), rel=0.001)

    def test_points_and_garbage_have_no_lines(self):
        point = json.dumps({"type": "Point", "coordinates": [9.0, 51.0]})
        assert po.project_lines(point) is None
        assert po.project_lines("not json") is None
        assert po.project_lines(None) is None


class TestLanes:
    def test_preferred_lane_kept_when_free(self):
        assert po.smallest_free_lane([0, 2], preferred=1) == 1

    def test_smallest_free_lane_when_preferred_is_taken(self):
        assert po.smallest_free_lane([0, 1, 3], preferred=1) == 2

    def test_triangle_needs_three_lanes(self):
        lanes = po.color_graph([1, 2, 3], [(1, 2), (2, 3), (1, 3)])
        assert sorted(lanes.values()) == [0, 1, 2]

    def test_highest_degree_first_and_isolated_on_lane_zero(self):
        # 5 is the hub of a star: it stays on the track, every spoke beside it.
        lanes = po.color_graph([1, 2, 3, 4, 5], [(5, 1), (5, 2), (5, 3)])
        assert lanes[5] == 0
        assert lanes[1] == lanes[2] == lanes[3] == 1
        assert lanes[4] == 0


def test_simplified_lines_run_west_to_east():
    text = _text(_line(9.1, 9.0))
    collection = simplify_geojson_text(text)
    part = collection["features"][0]["geometry"]["coordinates"][0]
    assert part[0][0] < part[-1][0]


# ── persistence ─────────────────────────────────────────────────────────────


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _register_spatial_stubs(dbapi_conn, _record):
        for name, nargs in (("GeomFromEWKT", 1), ("ST_AsEWKB", 1), ("AsEWKB", 1)):
            dbapi_conn.create_function(name, nargs, lambda x: x)

    for table in (
        Project.__table__,
        ProjectToConstituency.__table__,
        ProjectMapGeometry.__table__,
        ProjectOverlap.__table__,
    ):
        table.create(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _add(db, name: str, geometry: str | None = None, **kwargs) -> Project:
    project = Project(name=name, **kwargs)
    db.add(project)
    db.commit()
    db.refresh(project)
    if geometry is not None:
        update_project(db, project.id, {"geojson_representation": geometry})
    return project


def _lane(db, project_id: int) -> int | None:
    row = db.get(ProjectMapGeometry, project_id)
    return None if row is None else row.lane


def _pairs(db) -> set[tuple[int, int]]:
    return {(r.project_a_id, r.project_b_id) for r in db.query(ProjectOverlap).all()}


CORRIDOR = _line(9.0, 9.2)
SECTION = _line(9.05, 9.15)
OTHER_LINE = _line(9.0, 9.2, lat=52.0)


class TestPersistence:
    def test_saving_overlapping_projects_gives_them_different_lanes(self, db):
        a = _add(db, "Korridor", _text(CORRIDOR))
        b = _add(db, "Elektrifizierung", _text(SECTION))
        assert _pairs(db) == {(a.id, b.id)}
        assert {_lane(db, a.id), _lane(db, b.id)} == {0, 1}
        pair = db.query(ProjectOverlap).one()
        assert pair.share_b == pytest.approx(1.0, abs=0.02)
        assert pair.share_a == pytest.approx(0.5, abs=0.02)

    def test_project_without_partner_stays_on_lane_zero(self, db):
        a = _add(db, "Korridor", _text(CORRIDOR))
        _add(db, "Woanders", _text(OTHER_LINE))
        assert _pairs(db) == set()
        assert _lane(db, a.id) == 0

    def test_partners_keep_their_lane_when_a_geometry_changes(self, db):
        a = _add(db, "Korridor", _text(CORRIDOR))
        b = _add(db, "Elektrifizierung", _text(SECTION))
        lanes_before = (_lane(db, a.id), _lane(db, b.id))
        c = _add(db, "Blockverdichtung", _text(_line(9.1, 9.2)))
        assert (_lane(db, a.id), _lane(db, b.id)) == lanes_before
        assert _lane(db, c.id) not in lanes_before

        update_project(db, c.id, {"geojson_representation": _text(_line(9.12, 9.2))})
        assert (_lane(db, a.id), _lane(db, b.id)) == lanes_before
        assert _lane(db, c.id) not in lanes_before

    def test_moving_away_removes_the_pair(self, db):
        a = _add(db, "Korridor", _text(CORRIDOR))
        b = _add(db, "Elektrifizierung", _text(SECTION))
        update_project(db, b.id, {"geojson_representation": _text(OTHER_LINE)})
        assert _pairs(db) == set()
        assert db.get(ProjectMapGeometry, a.id) is not None

    def test_removing_the_geometry_forgets_the_project(self, db):
        _add(db, "Korridor", _text(CORRIDOR))
        b = _add(db, "Elektrifizierung", _text(SECTION))
        update_project(db, b.id, {"geojson_representation": None})
        assert _pairs(db) == set()
        assert db.get(ProjectMapGeometry, b.id) is None

    def test_drafts_and_archived_projects_do_not_count(self, db):
        a = _add(db, "Korridor", _text(CORRIDOR))
        draft = _add(db, "Entwurf", _text(SECTION), is_draft=True)
        archived = _add(db, "Archiv", _text(SECTION), is_archived=True)
        assert _pairs(db) == set()
        assert db.get(ProjectMapGeometry, draft.id) is None
        assert db.get(ProjectMapGeometry, archived.id) is None

        update_project(db, draft.id, {"is_draft": False})
        assert _pairs(db) == {(a.id, draft.id)}

    def test_parent_and_child_overlap_like_any_other_pair(self, db):
        # W5: no special case — "Nur Hauptprojekte" decides what the map shows.
        parent = _add(db, "Korridor", geojson_from_subprojects=True)
        child = _add(db, "Abschnitt", superior_project_id=parent.id)
        update_project(db, child.id, {"geojson_representation": _text(SECTION)})
        db.refresh(parent)
        assert parent.geojson_representation is not None
        assert _pairs(db) == {(parent.id, child.id)}

    def test_unchanged_geometry_is_not_recomputed(self, db):
        a = _add(db, "Korridor", _text(CORRIDOR))
        before = db.get(ProjectMapGeometry, a.id).computed_at
        update_project(db, a.id, {"geojson_representation": _text(CORRIDOR)})
        assert db.get(ProjectMapGeometry, a.id).computed_at == before

    def test_full_rebuild_matches_the_incremental_pairs(self, db):
        a = _add(db, "Korridor", _text(CORRIDOR))
        b = _add(db, "Elektrifizierung", _text(SECTION))
        c = _add(db, "Blockverdichtung", _text(_line(9.1, 9.2)))
        _add(db, "Woanders", _text(OTHER_LINE))
        incremental = _pairs(db)

        db.query(ProjectOverlap).delete()
        db.query(ProjectMapGeometry).delete()
        db.commit()
        assert po.is_empty(db)

        stats = po.recompute_all_overlaps(db)
        assert _pairs(db) == incremental
        assert stats.projects_with_lines == 4
        assert stats.pairs == len(incremental)
        # The corridor has the most partners and stays on the track.
        assert _lane(db, a.id) == 0
        assert _lane(db, b.id) != _lane(db, a.id)
        assert _lane(db, c.id) != _lane(db, a.id)

    def test_map_lanes_lists_partners_across_groups(self, db):
        a = _add(db, "Korridor", _text(CORRIDOR))
        b = _add(db, "Elektrifizierung", _text(SECTION))
        lone = _add(db, "Woanders", _text(OTHER_LINE))
        lanes = po.map_lanes(db, [a.id, lone.id])
        assert lanes == {a.id: {"lane": _lane(db, a.id), "overlaps": [b.id]}}
