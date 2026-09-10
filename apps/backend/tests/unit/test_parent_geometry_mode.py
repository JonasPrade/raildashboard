"""Geometry mode of a superior project: aggregated from subprojects vs. self-maintained.

Runs against an in-memory SQLite schema. ``project.centroid`` is a PostGIS geometry in
production; the table is re-created here with TEXT in its place so plain SQLite can host
it (none of the geometry-cascade code touches the column).
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import Column, MetaData, Table, Text, create_engine, event
from sqlalchemy.orm import sessionmaker

from dashboard_backend.crud.projects.projects import (
    has_subprojects,
    recompute_geojson_for_parent,
    update_project,
)
from dashboard_backend.models.associations.project_to_constituency import (
    ProjectToConstituency,
)
from dashboard_backend.models.projects.project import Project


def _sqlite_project_table() -> Table:
    """Clone project's table with the Geometry column replaced by TEXT."""
    md = MetaData()
    cols = []
    for c in Project.__table__.columns:
        cols.append(Column("centroid", Text) if c.name == "centroid" else c.copy())
    return Table("project", md, *cols)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _register_spatial_stubs(dbapi_conn, _record):
        for name, nargs in (("GeomFromEWKT", 1), ("ST_AsEWKB", 1), ("AsEWKB", 1)):
            dbapi_conn.create_function(name, nargs, lambda x: x)

    _sqlite_project_table().create(bind=engine)
    # The geometry cascade also refreshes the constituency links of every
    # project it touches, so the link table has to exist here.
    ProjectToConstituency.__table__.create(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _line(x: float) -> str:
    """A one-feature FeatureCollection, distinguishable by its x coordinate."""
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [[x, 0], [x, 1]]},
                    "properties": {},
                }
            ],
        }
    )


def _add(db, name: str, **kwargs) -> Project:
    project = Project(name=name, **kwargs)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def _feature_count(project: Project) -> int:
    if not project.geojson_representation:
        return 0
    return len(json.loads(project.geojson_representation)["features"])


class TestDefaultAggregation:
    def test_flag_defaults_to_aggregated(self, db):
        assert _add(db, "Solo").geojson_from_subprojects is True

    def test_parent_aggregates_children(self, db):
        parent = _add(db, "Parent")
        child_a = _add(db, "A", superior_project_id=parent.id)
        _add(db, "B", superior_project_id=parent.id, geojson_representation=_line(2))

        update_project(db, child_a.id, {"geojson_representation": _line(1)})

        db.refresh(parent)
        assert _feature_count(parent) == 2


class TestSelfMaintainedParent:
    def test_child_change_does_not_overwrite_parent(self, db):
        parent = _add(
            db,
            "Parent",
            geojson_from_subprojects=False,
            geojson_representation=_line(9),
        )
        child = _add(db, "Child", superior_project_id=parent.id)

        update_project(db, child.id, {"geojson_representation": _line(1)})

        db.refresh(parent)
        assert parent.geojson_representation == _line(9)

    def test_cascade_stops_at_a_self_maintained_ancestor(self, db):
        grandparent = _add(db, "Grandparent")
        parent = _add(
            db,
            "Parent",
            superior_project_id=grandparent.id,
            geojson_from_subprojects=False,
            geojson_representation=_line(9),
        )
        child = _add(db, "Child", superior_project_id=parent.id)

        update_project(db, child.id, {"geojson_representation": _line(1)})

        db.refresh(parent)
        db.refresh(grandparent)
        assert parent.geojson_representation == _line(9)
        # The grandparent aggregates the parent — whose geometry did not change.
        assert grandparent.geojson_representation is None


class TestSwitchingTheMode:
    def test_switching_to_self_maintained_keeps_the_aggregated_geometry(self, db):
        parent = _add(db, "Parent")
        child = _add(db, "Child", superior_project_id=parent.id)
        update_project(db, child.id, {"geojson_representation": _line(1)})
        db.refresh(parent)
        aggregated = parent.geojson_representation

        update_project(db, parent.id, {"geojson_from_subprojects": False})

        db.refresh(parent)
        assert parent.geojson_representation == aggregated

    def test_switching_back_rebuilds_from_the_subprojects(self, db):
        parent = _add(
            db,
            "Parent",
            geojson_from_subprojects=False,
            geojson_representation=_line(9),
        )
        _add(db, "Child", superior_project_id=parent.id, geojson_representation=_line(1))

        update_project(db, parent.id, {"geojson_from_subprojects": True})

        db.refresh(parent)
        assert parent.geojson_representation == _line(1)

    def test_switching_back_cascades_to_the_grandparent(self, db):
        grandparent = _add(db, "Grandparent")
        parent = _add(
            db,
            "Parent",
            superior_project_id=grandparent.id,
            geojson_from_subprojects=False,
        )
        _add(db, "Child", superior_project_id=parent.id, geojson_representation=_line(1))

        update_project(db, parent.id, {"geojson_from_subprojects": True})

        db.refresh(grandparent)
        assert _feature_count(grandparent) == 1

    def test_switching_a_childless_project_keeps_its_geometry(self, db):
        solo = _add(db, "Solo", geojson_from_subprojects=False, geojson_representation=_line(1))

        update_project(db, solo.id, {"geojson_from_subprojects": True})

        db.refresh(solo)
        assert solo.geojson_representation == _line(1)

    def test_explicit_null_leaves_the_flag_untouched(self, db):
        parent = _add(db, "Parent", geojson_from_subprojects=False)

        update_project(db, parent.id, {"geojson_from_subprojects": None, "name": "Renamed"})

        db.refresh(parent)
        assert parent.geojson_from_subprojects is False
        assert parent.name == "Renamed"


class TestHasSubprojects:
    def test_true_only_with_children(self, db):
        parent = _add(db, "Parent")
        assert has_subprojects(db, parent.id) is False
        _add(db, "Child", superior_project_id=parent.id)
        assert has_subprojects(db, parent.id) is True


class TestRecomputeGuards:
    def test_recompute_skips_a_self_maintained_parent(self, db):
        parent = _add(
            db,
            "Parent",
            geojson_from_subprojects=False,
            geojson_representation=_line(9),
        )
        _add(db, "Child", superior_project_id=parent.id, geojson_representation=_line(1))

        recompute_geojson_for_parent(db, parent.id)

        db.refresh(parent)
        assert parent.geojson_representation == _line(9)
