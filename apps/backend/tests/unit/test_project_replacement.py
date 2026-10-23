"""Lifecycle ERSETZT (docs/features/feature-project-replacement.md): successor rules,
note/date for every status, the view's back-references and the parent aggregation
that leaves replaced subprojects out (W3).

Runs against the in-memory SQLite schema of ``test_progress_aggregation``.
"""

from __future__ import annotations

from datetime import date

import pytest

from dashboard_backend.crud.projects import progress as progress_crud
from dashboard_backend.crud.projects.progress import LifecycleError, update_progress
from dashboard_backend.crud.projects.projects import replaced_project_ids, subtree_ids
from dashboard_backend.models.change_tracking import ChangeLog, ChangeLogEntry
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.services.progress_derivation import aggregate_tree
from tests.unit.test_progress_aggregation import _make_tree, db, engine  # noqa: F401


@pytest.fixture()
def change_log(engine):  # noqa: F811
    ChangeLog.__table__.create(bind=engine)
    ChangeLogEntry.__table__.create(bind=engine)


def _projects(db, *names, draft=False):  # noqa: F811
    rows = [Project(name=name, is_draft=draft) for name in names]
    db.add_all(rows)
    db.commit()
    return rows


def _progress(db, pid):  # noqa: F811
    return db.query(ProjectProgress).filter(ProjectProgress.project_id == pid).one()


@pytest.mark.usefixtures("change_log")
class TestSetLifecycle:
    def test_replaced_with_successor_note_and_date(self, db):  # noqa: F811
        old, new = _projects(db, "Alt", "Neu")
        update_progress(
            db,
            old.id,
            {
                "lifecycle_status": "ERSETZT",
                "replaced_by_project_id": new.id,
                "lifecycle_note": "  Eigenständiges Vorhaben D-14  ",
                "lifecycle_date": date(2023, 5, 1),
            },
            None,
        )
        row = _progress(db, old.id)
        assert row.lifecycle_status == "ERSETZT"
        assert row.replaced_by_project_id == new.id
        assert row.lifecycle_note == "Eigenständiges Vorhaben D-14"
        assert row.lifecycle_date == date(2023, 5, 1)
        fields = {e.field_name for e in db.query(ChangeLogEntry)}
        assert {"progress.lifecycle_status", "progress.replaced_by_project_id"} <= fields

    def test_back_to_active_clears_everything(self, db):  # noqa: F811
        old, new = _projects(db, "Alt", "Neu")
        update_progress(
            db,
            old.id,
            {"lifecycle_status": "ERSETZT", "replaced_by_project_id": new.id, "lifecycle_note": "x"},
            None,
        )
        update_progress(db, old.id, {"lifecycle_status": "AKTIV"}, None)
        row = _progress(db, old.id)
        assert (row.replaced_by_project_id, row.lifecycle_note, row.lifecycle_date) == (None, None, None)

    def test_note_and_date_for_paused(self, db):  # noqa: F811
        (project,) = _projects(db, "P")
        update_progress(
            db,
            project.id,
            {"lifecycle_status": "PAUSIERT", "lifecycle_note": "Finanzierung offen", "lifecycle_date": date(2026, 1, 1)},
            None,
        )
        row = _progress(db, project.id)
        assert (row.lifecycle_note, row.lifecycle_date, row.replaced_by_project_id) == (
            "Finanzierung offen",
            date(2026, 1, 1),
            None,
        )

    def test_switching_from_replaced_to_aborted_drops_successor(self, db):  # noqa: F811
        old, new = _projects(db, "Alt", "Neu")
        update_progress(db, old.id, {"lifecycle_status": "ERSETZT", "replaced_by_project_id": new.id}, None)
        update_progress(db, old.id, {"lifecycle_status": "ABGEBROCHEN"}, None)
        assert _progress(db, old.id).replaced_by_project_id is None

    @pytest.mark.parametrize(
        "payload, message",
        [
            ({"lifecycle_status": "ERSETZT"}, "fehlt das Nachfolgeprojekt"),
            ({"lifecycle_status": "ERSETZT", "replaced_by_project_id": 99999}, "gibt es nicht"),
            ({"lifecycle_status": "PAUSIERT", "replaced_by_project_id": "NEW"}, "nur beim Status"),
        ],
    )
    def test_rejects_invalid_successor(self, db, payload, message):  # noqa: F811
        old, new = _projects(db, "Alt", "Neu")
        payload = {k: (new.id if v == "NEW" else v) for k, v in payload.items()}
        with pytest.raises(LifecycleError, match=message):
            update_progress(db, old.id, payload, None)

    def test_rejects_self(self, db):  # noqa: F811
        (project,) = _projects(db, "P")
        with pytest.raises(LifecycleError, match="selbst"):
            update_progress(db, project.id, {"lifecycle_status": "ERSETZT", "replaced_by_project_id": project.id}, None)

    def test_rejects_draft_successor(self, db):  # noqa: F811
        (old,) = _projects(db, "Alt")
        (draft,) = _projects(db, "Entwurf", draft=True)
        with pytest.raises(LifecycleError, match="Entwurf"):
            update_progress(db, old.id, {"lifecycle_status": "ERSETZT", "replaced_by_project_id": draft.id}, None)

    def test_rejects_ring_but_allows_chain(self, db):  # noqa: F811
        a, b, c = _projects(db, "A", "B", "C")
        update_progress(db, a.id, {"lifecycle_status": "ERSETZT", "replaced_by_project_id": b.id}, None)
        update_progress(db, b.id, {"lifecycle_status": "ERSETZT", "replaced_by_project_id": c.id}, None)
        assert progress_crud.successor_chain(db, a.id) == [a.id, b.id, c.id]
        with pytest.raises(LifecycleError, match="selbst durch dieses Projekt"):
            update_progress(db, c.id, {"lifecycle_status": "ERSETZT", "replaced_by_project_id": a.id}, None)


@pytest.mark.usefixtures("change_log")
def test_parent_aggregation_leaves_replaced_children_out(db):  # noqa: F811
    superior = _make_tree(db, 2)  # Leaf-0 VORPLANUNG, Leaf-1 BAU
    leaves = db.query(Project).filter(Project.superior_project_id == superior.id).order_by(Project.id).all()
    update_progress(
        db, leaves[1].id, {"lifecycle_status": "ERSETZT", "replaced_by_project_id": leaves[0].id}, None
    )

    node = progress_crud._build_aggregation_node(db, superior, date(2026, 7, 1))
    agg = aggregate_tree(node)
    assert agg.span is not None
    assert {agg.span[0].value, agg.span[1].value} == {"VORPLANUNG"}
    # The replaced child stays a node (the subproject table shows it with a badge).
    assert [child.lifecycle.value for child in node.children] == ["AKTIV", "ERSETZT"]

    assert replaced_project_ids(db, [leaf.id for leaf in leaves]) == {leaves[1].id}
    assert subtree_ids(db, superior.id, skip_replaced=True) == [superior.id, leaves[0].id]
    assert len(subtree_ids(db, superior.id)) == 3


@pytest.mark.usefixtures("change_log")
def test_view_names_successor_and_back_reference(db, monkeypatch):  # noqa: F811
    # Track documents live in tables this schema lacks; they are not under test.
    monkeypatch.setattr(progress_crud, "_track_documents", lambda db, pid, track: [])
    monkeypatch.setattr(progress_crud, "_build_forecast_for_project", lambda *a, **k: {"next_steps": []})
    old, new = _projects(db, "Alt", "Neu")
    new.project_number = "D-14"
    db.commit()
    update_progress(db, old.id, {"lifecycle_status": "ERSETZT", "replaced_by_project_id": new.id}, None)

    old_view = progress_crud.get_progress_view(db, old.id, date(2026, 10, 23))
    new_view = progress_crud.get_progress_view(db, new.id, date(2026, 10, 23))
    assert old_view["lifecycle_status"] == "ERSETZT"
    assert old_view["replaced_by"] == {"id": new.id, "name": "Neu", "project_number": "D-14"}
    assert new_view["replaced_by"] is None
    assert new_view["replaces"] == [{"id": old.id, "name": "Alt", "project_number": None}]


# --- Importers (W5) -------------------------------------------------------------


def test_redirect_replaced_keeps_order_and_dedupes():
    from dashboard_backend.crud.projects.projects import redirect_replaced

    ids, redirected = redirect_replaced([1, 2, 3], {1: 3, 2: 4})
    assert ids == [3, 4]
    assert redirected == {3: 1, 4: 2}


@pytest.mark.usefixtures("change_log")
def test_successor_map_follows_chains(db):  # noqa: F811
    from dashboard_backend.crud.projects.projects import successor_map

    a, b, c = _projects(db, "A", "B", "C")
    update_progress(db, a.id, {"lifecycle_status": "ERSETZT", "replaced_by_project_id": b.id}, None)
    update_progress(db, b.id, {"lifecycle_status": "ERSETZT", "replaced_by_project_id": c.id}, None)
    assert successor_map(db) == {a.id: c.id, b.id: c.id}


def test_infraplan_suggestion_moves_to_successor():
    from dashboard_backend.tasks.infraplan_matching import ProjectRef, suggest_rows

    projects = [ProjectRef(1, "ABS/NBS Hannover – Bielefeld", None, "2-016-V01"), ProjectRef(2, "NBS/ABS Bielefeld – Seelze")]
    row = {"row_key": "A-1", "section": "A", "primary_number": "2-016-V01", "bezeichnung": "", "massnahme": ""}
    out = suggest_rows([row], projects, {}, successors={1: 2})["A-1"]
    assert out[0]["project_id"] == 2
    assert out[0]["redirected_from"] == 1
    assert all(s["project_id"] != 1 for s in out)
