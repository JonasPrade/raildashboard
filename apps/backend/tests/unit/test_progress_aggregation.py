"""Batched superior aggregation (#89): golden semantics + sublinear queries.

Runs against an in-memory SQLite schema. ``project.centroid`` is a PostGIS
geometry in production; the table is re-created here with TEXT in its place so
plain SQLite can host it (the aggregation never touches the column).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import Column, MetaData, Table, Text, create_engine, event
from sqlalchemy.orm import sessionmaker

from dashboard_backend.crud.projects import progress as progress_crud
from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.associations.fulda_announcement_to_project import (
    fulda_announcement_to_project,
)
from dashboard_backend.models.associations.project_to_project_group import (
    ProjectToProjectGroup,
)
from dashboard_backend.models.projects.bauportal_status import BauportalStatus
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.fulda_announcement import FuldaAnnouncement
from dashboard_backend.models.projects.media_report import MediaReport
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.models.vib.vib_entry import VibEntry, vib_entry_project
from dashboard_backend.models.vib.vib_pfa_entry import VibPfaEntry
from dashboard_backend.models.vib.vib_report import VibReport
from dashboard_backend.services.progress_derivation import aggregate_tree


def _sqlite_project_table() -> Table:
    """Clone project's table with the Geometry column replaced by TEXT."""
    md = MetaData()
    cols = []
    for c in Project.__table__.columns:
        if c.name == "centroid":
            cols.append(Column("centroid", Text))
        else:
            cols.append(c.copy())
    return Table("project", md, *cols)


_TABLES_BEFORE = [
    ProjectGroup.__table__,
    ProjectToProjectGroup.__table__,
    ProjectProgress.__table__,
    ProgressObservation.__table__,
    VibReport.__table__,
    VibEntry.__table__,
    vib_entry_project,
    VibPfaEntry.__table__,
    Finve.__table__,
    FinveToProject.__table__,
    BauportalStatus.__table__,
    MediaReport.__table__,
    FuldaAnnouncement.__table__,
    fulda_announcement_to_project,
]


@pytest.fixture()
def engine():
    engine = create_engine("sqlite:///:memory:")

    # geoalchemy2 wraps geometry params/columns in spatial functions; register
    # pass-through stand-ins so plain SQLite accepts them (values stay NULL).
    @event.listens_for(engine, "connect")
    def _register_spatial_stubs(dbapi_conn, _record):
        for name, nargs in (("GeomFromEWKT", 1), ("ST_AsEWKB", 1), ("AsEWKB", 1)):
            dbapi_conn.create_function(name, nargs, lambda x: x)

    _sqlite_project_table().create(bind=engine)
    for t in _TABLES_BEFORE:
        t.create(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db(engine):
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _make_tree(db, n_leaves: int) -> Project:
    """One superior with ``n_leaves`` leaf subprojects, each with one fresh
    manual MAIN observation (alternating VORPLANUNG / BAU)."""
    superior = Project(name=f"Superior-{n_leaves}")
    db.add(superior)
    db.flush()
    phases = ["VORPLANUNG", "BAU"]
    for i in range(n_leaves):
        leaf = Project(name=f"Leaf-{i}", superior_project_id=superior.id)
        db.add(leaf)
        db.flush()
        db.add(
            ProgressObservation(
                project_id=leaf.id,
                source_type="MANUELL",
                track="MAIN",
                asserted_state=phases[i % 2],
                observed_date=date(2026, 1, 1),
                is_derived=False,
                is_expected=False,
            )
        )
        # fresh cache → the batched resync must NOT run for this leaf
        db.add(
            ProjectProgress(
                project_id=leaf.id,
                lifecycle_status="AKTIV",
                computed_at=datetime.utcnow(),
            )
        )
    db.commit()
    return superior


def _count_queries(engine, fn):
    counter = {"n": 0}

    def _before(conn, cursor, statement, parameters, context, executemany):
        if statement.strip().upper().startswith(("SELECT", "INSERT", "UPDATE", "DELETE")):
            counter["n"] += 1

    event.listen(engine, "before_cursor_execute", _before)
    try:
        result = fn()
    finally:
        event.remove(engine, "before_cursor_execute", _before)
    return result, counter["n"]


def test_aggregation_golden_semantics(db):
    superior = _make_tree(db, 4)
    node = progress_crud._build_aggregation_node(db, superior, date(2026, 7, 1))
    db.commit()
    agg = aggregate_tree(node)

    # Leaves alternate VORPLANUNG/BAU → span covers both, all leaves known.
    assert agg.is_known is True
    assert agg.span is not None
    span_values = {agg.span[0].value, agg.span[1].value}
    assert span_values == {"VORPLANUNG", "BAU"}

    leaf_phases = sorted(
        (child.project_id, aggregate_tree(child).display_phase.value)
        for child in node.children
    )
    expected = sorted(
        (child.id, ["VORPLANUNG", "BAU"][i % 2])
        for i, child in enumerate(
            db.query(Project)
            .filter(Project.superior_project_id == superior.id)
            .order_by(Project.id)
            .all()
        )
    )
    assert leaf_phases == expected


def test_aggregation_query_count_is_sublinear(engine, db):
    """The same number of queries regardless of leaf count (fresh caches)."""
    small = _make_tree(db, 2)
    big = _make_tree(db, 10)

    _, q_small = _count_queries(
        engine, lambda: progress_crud._build_aggregation_node(db, small, date(2026, 7, 1))
    )
    db.commit()  # flush the first run's cache updates outside the second count
    _, q_big = _count_queries(
        engine, lambda: progress_crud._build_aggregation_node(db, big, date(2026, 7, 1))
    )
    assert q_big == q_small, f"query count grew with leaves: {q_small} -> {q_big}"


def test_aggregation_resyncs_stale_leaves_in_batch(engine, db):
    """Stale leaves trigger the batched resync — query count still constant."""
    superior = _make_tree(db, 6)
    # Make all leaves stale.
    db.query(ProjectProgress).update(
        {ProjectProgress.computed_at: datetime.utcnow() - timedelta(days=30)}
    )
    db.commit()

    node, q_stale = _count_queries(
        engine, lambda: progress_crud._build_aggregation_node(db, superior, date(2026, 7, 1))
    )
    db.commit()
    agg = aggregate_tree(node)
    assert agg.is_known is True

    # Second stale run with more leaves must not add per-leaf queries.
    superior2 = _make_tree(db, 12)
    db.query(ProjectProgress).update(
        {ProjectProgress.computed_at: datetime.utcnow() - timedelta(days=30)}
    )
    db.commit()
    _, q_stale2 = _count_queries(
        engine, lambda: progress_crud._build_aggregation_node(db, superior2, date(2026, 7, 1))
    )
    assert q_stale2 == q_stale, f"stale resync grew with leaves: {q_stale} -> {q_stale2}"
