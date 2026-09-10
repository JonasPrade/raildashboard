"""Geometry splitting and the materialised project ↔ constituency links.

The intersection itself is PostGIS and cannot run on the SQLite test database;
what is pinned here is everything around it — which geometries go into the
line bucket and which into the point bucket, that a missing geometry produces no
rows, and how the links are read back and ordered.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import Column, MetaData, Table, Text, create_engine, event
from sqlalchemy.orm import sessionmaker

from dashboard_backend.crud import parliament as parliament_crud
from dashboard_backend.models.associations.project_to_constituency import (
    OVERLAP_KIND_LINE,
    OVERLAP_KIND_POINT,
    ProjectToConstituency,
)
from dashboard_backend.models.parliament import (
    Committee,
    CommitteeMembership,
    Constituency,
    Mandate,
    ParliamentPeriod,
    Politician,
)
from dashboard_backend.models.projects.project import Project
from dashboard_backend.services.constituency_matching import (
    compute_links_for_project,
    coverage,
    split_geometries,
)


def _feature_collection(*geometries):
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": geometry, "properties": {}}
                for geometry in geometries
            ],
        }
    )


LINE = {"type": "LineString", "coordinates": [[10.0, 53.5], [11.0, 53.2]]}
POINT = {"type": "Point", "coordinates": [8.66, 50.11]}


# --- geometry splitting -----------------------------------------------------


def test_lines_and_points_are_separated():
    lines, points = split_geometries(_feature_collection(LINE, POINT))
    assert [g["type"] for g in lines] == ["LineString"]
    assert [g["type"] for g in points] == ["Point"]


def test_bare_geometry_and_nested_collections_are_understood():
    assert split_geometries(json.dumps(LINE))[0] == [LINE]
    nested = json.dumps(
        {"type": "GeometryCollection", "geometries": [LINE, POINT]}
    )
    lines, points = split_geometries(nested)
    assert lines and points


def test_polygons_count_as_lines_rather_than_disappearing():
    polygon = {
        "type": "Polygon",
        "coordinates": [[[10.0, 53.0], [10.1, 53.0], [10.1, 53.1], [10.0, 53.0]]],
    }
    lines, points = split_geometries(_feature_collection(polygon))
    assert lines == [polygon]
    assert points == []


@pytest.mark.parametrize("value", [None, "", "not json", "{}", '{"type": "Feature"}'])
def test_unusable_geometry_yields_nothing(value):
    assert split_geometries(value) == ([], [])


# --- links ------------------------------------------------------------------


def _sqlite_project_table() -> Table:
    """Clone project's table with the PostGIS centroid replaced by TEXT."""
    md = MetaData()
    cols = [
        Column("centroid", Text) if c.name == "centroid" else c.copy()
        for c in Project.__table__.columns
    ]
    return Table("project", md, *cols)


TABLES = [
    ParliamentPeriod.__table__,
    Politician.__table__,
    Constituency.__table__,
    Committee.__table__,
    Mandate.__table__,
    CommitteeMembership.__table__,
    ProjectToConstituency.__table__,
]


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    # geoalchemy2 wraps geometry params in spatial functions; register
    # pass-through stand-ins so plain SQLite accepts them (values stay NULL).
    @event.listens_for(engine, "connect")
    def _register_spatial_stubs(dbapi_conn, _record):
        for name, nargs in (("GeomFromEWKT", 1), ("ST_AsEWKB", 1), ("AsEWKB", 1)):
            dbapi_conn.create_function(name, nargs, lambda x: x)

    _sqlite_project_table().create(bind=engine)
    for table in TABLES:
        table.create(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def seeded(session):
    period = ParliamentPeriod(external_id=161, label="Bundestag 2025 - 2029", is_current=True)
    session.add(period)
    session.flush()
    near = Constituency(parliament_period_id=period.id, number=182, name="Offenbach")
    far = Constituency(parliament_period_id=period.id, number=1, name="Flensburg")
    project = Project(name="ABS Test", geojson_representation=_feature_collection(LINE))
    session.add_all([near, far, project])
    session.flush()
    session.add_all(
        [
            ProjectToConstituency(
                project_id=project.id,
                constituency_id=far.id,
                length_km=3.0,
                share=0.06,
                overlap_kind=OVERLAP_KIND_LINE,
            ),
            ProjectToConstituency(
                project_id=project.id,
                constituency_id=near.id,
                length_km=51.0,
                share=0.94,
                overlap_kind=OVERLAP_KIND_LINE,
            ),
        ]
    )
    session.commit()
    return {"project": project, "near": near, "far": far, "period": period}


def test_links_are_ordered_by_kilometres(session, seeded):
    rows = parliament_crud.links_for_project(session, seeded["project"].id)
    assert [constituency.number for _, constituency in rows] == [182, 1]
    assert rows[0][0].length_km == 51.0


def test_recompute_without_postgis_clears_but_writes_nothing(session, seeded):
    # Documented no-op on a non-spatial backend: saving a project keeps working,
    # the links simply cannot be recomputed there.
    written = compute_links_for_project(session, seeded["project"])
    session.commit()
    assert written == 0
    assert parliament_crud.links_for_project(session, seeded["project"].id) == []


def test_project_without_geometry_produces_no_links(session, seeded):
    project = Project(name="Ohne Geometrie")
    session.add(project)
    session.commit()
    assert compute_links_for_project(session, project) == 0


def test_coverage_counts_projects_without_geometry(session, seeded):
    session.add(Project(name="Ohne Geometrie"))
    session.commit()
    numbers = coverage(session)
    assert numbers["projects_total"] == 2
    assert numbers["projects_with_geometry"] == 1
    assert numbers["projects_without_geometry"] == 1
    assert numbers["projects_linked"] == 1


def test_direct_and_list_mandates_stay_apart(session, seeded):
    politician_a = Politician(external_id=1, label="Direkt Gewählt", last_name="Gewählt")
    politician_b = Politician(external_id=2, label="Über Liste", last_name="Liste")
    politician_c = Politician(external_id=3, label="Im Ausschuss", last_name="Ausschuss")
    session.add_all([politician_a, politician_b, politician_c])
    session.flush()

    committee = Committee(
        external_id=900,
        parliament_period_id=seeded["period"].id,
        key="verkehr",
        label="Verkehrsausschuss",
    )
    session.add(committee)
    session.flush()

    mandates = [
        Mandate(
            external_id=10,
            politician_id=politician_a.id,
            parliament_period_id=seeded["period"].id,
            constituency_id=seeded["near"].id,
            mandate_type="constituency",
            is_direct_mandate=True,
        ),
        Mandate(
            external_id=11,
            politician_id=politician_b.id,
            parliament_period_id=seeded["period"].id,
            constituency_id=seeded["near"].id,
            mandate_type="list",
            is_direct_mandate=False,
        ),
        Mandate(
            external_id=12,
            politician_id=politician_c.id,
            parliament_period_id=seeded["period"].id,
            constituency_id=seeded["near"].id,
            mandate_type="list",
            is_direct_mandate=False,
        ),
    ]
    session.add_all(mandates)
    session.flush()
    session.add(
        CommitteeMembership(
            mandate_id=mandates[2].id,
            committee_id=committee.id,
            role="chairperson",
            role_label="Vorsitz",
            role_rank=0,
        )
    )
    session.commit()

    grouped = parliament_crud.mandates_for_constituencies(session, [seeded["near"].id])
    direct, listed = parliament_crud.split_mandates(grouped[seeded["near"].id])

    assert [m.name for m in direct] == ["Direkt Gewählt"]
    # Committee members lead the list side — that is the working list.
    assert [m.name for m in listed] == ["Im Ausschuss", "Über Liste"]
    assert listed[0].committees[0].role_label == "Vorsitz"


def test_point_only_link_carries_no_kilometres(session, seeded):
    project = Project(name="Bahnhof", geojson_representation=_feature_collection(POINT))
    session.add(project)
    session.flush()
    session.add(
        ProjectToConstituency(
            project_id=project.id,
            constituency_id=seeded["near"].id,
            length_km=0.0,
            share=1.0,
            overlap_kind=OVERLAP_KIND_POINT,
        )
    )
    session.commit()

    (link, _), = parliament_crud.links_for_project(session, project.id)
    assert link.overlap_kind == OVERLAP_KIND_POINT
    assert link.length_km == 0.0
    assert link.share == 1.0
