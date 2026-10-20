"""MCP data-maintenance tools (issue #175, stage A): the new list_projects
filters, list_data_gaps and check_geometry."""

from __future__ import annotations

import json
from datetime import date, datetime

from geoalchemy2.shape import from_shape
from shapely.geometry import LineString

from dashboard_backend.models.change_tracking import ChangeLog
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.models.railway_infrastructure.operational_point import OperationalPoint
from dashboard_backend.models.routes import Route
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _payload,
    admin_token,
    mcp_client,
)


def _collection(*features):
    return json.dumps({"type": "FeatureCollection", "features": list(features)})


def _line(*coords):
    return {"type": "Feature", "geometry": {"type": "LineString", "coordinates": list(coords)}, "properties": {}}


def _routed(start, end, steps=40):
    (x0, y0), (x1, y1) = start, end
    return _line(*[[x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps] for i in range(steps + 1)])


def _route_for(project_id):
    return Route(
        project_id=project_id,
        profile="rail_default",
        graph_version="test",
        distance_m=1000.0,
        duration_ms=60000,
        geom=from_shape(LineString([(9, 48), (9, 48.5)]), srid=4326),
        cache_key=f"route-{project_id}",
    )


def _seed(db):
    """complete: everything there. sketched: chords, no route, no description.
    bare: nothing at all, unknown phase. bswag: in a BSWAG group, paused, stale."""
    group = ProjectGroup(name="Testgruppe", short_name="TG", color="#000000")
    bswag = ProjectGroup(name="Bedarfsplan", short_name="BSWAG-NEU", color="#000000")
    routed = _collection(_routed([9.0, 48.0], [9.0, 48.5]))
    chords = _collection(*(_line([9.0, 48.0 + 0.1 * i], [9.0, 48.1 + 0.1 * i]) for i in range(5)))
    complete = Project(
        name="ABS Complete", project_number="1-001", description="Text", length=55.6,
        geojson_representation=routed, is_draft=False,
    )
    sketched = Project(
        name="Stuttgart – Ulm", project_number="2-002", length=55.6,
        geojson_representation=chords, is_draft=False,
    )
    bare = Project(name="Bare", is_draft=False)
    paused = Project(
        name="Paused", project_number="3-003", description="Text", length=10.0,
        geojson_representation=routed, is_draft=False,
    )
    complete.project_groups = [group]
    sketched.project_groups = [group]
    bare.project_groups = [group]
    paused.project_groups = [bswag]
    db.add_all([group, bswag, complete, sketched, bare, paused])
    db.flush()
    db.add_all(
        [
            ProjectProgress(project_id=complete.id, computed_phase="BAU", computed_confidence=0.8),
            ProjectProgress(project_id=sketched.id, manual_phase_override="VORPLANUNG"),
            # The derivation's fallback: NICHT_GESTARTET at confidence 0.0 = unknown.
            ProjectProgress(project_id=bare.id, computed_phase="NICHT_GESTARTET", computed_confidence=0.0),
            ProjectProgress(
                project_id=paused.id, computed_phase="BAU", computed_confidence=0.5,
                lifecycle_status="PAUSIERT",
            ),
            ProgressObservation(
                project_id=paused.id, source_type="MANUELL", track="MAIN",
                asserted_state="BAU", observed_date=date(2015, 1, 1),
            ),
            ProgressObservation(
                project_id=complete.id, source_type="MANUELL", track="MAIN",
                asserted_state="BAU", observed_date=date.today(),
            ),
            _route_for(complete.id),
            _route_for(paused.id),
            ChangeLog(project_id=sketched.id, timestamp=datetime(2026, 10, 1, 12, 0)),
            ChangeLog(project_id=complete.id, timestamp=datetime(2026, 9, 1, 12, 0)),
            OperationalPoint(op_id="TS", name="Stuttgart Hbf", type="station", latitude=48.784, longitude=9.18),
            OperationalPoint(op_id="TU", name="Ulm Hbf", type="station", latitude=48.4, longitude=9.0),
        ]
    )
    db.commit()
    return complete, sketched, bare, paused


def _ids(result):
    return [p["id"] for p in result["projects"]]


def _list(client, token, **arguments):
    return _payload(_call(client, token, "list_projects", arguments))


# --- list_projects filters ---------------------------------------------------


def test_list_projects_is_known(mcp_client, admin_token, db_session):
    complete, sketched, bare, paused = _seed(db_session)
    known = _list(mcp_client, admin_token, is_known=True)
    assert _ids(known) == [complete.id, paused.id, sketched.id]
    assert all(p["is_known"] for p in known["projects"])
    unknown = _list(mcp_client, admin_token, is_known=False)
    assert _ids(unknown) == [bare.id]
    assert unknown["projects"][0]["is_known"] is False


def test_list_projects_geometry_length_lifecycle_parl(mcp_client, admin_token, db_session):
    complete, sketched, bare, paused = _seed(db_session)
    assert _ids(_list(mcp_client, admin_token, has_geometry=False)) == [bare.id]
    assert _ids(_list(mcp_client, admin_token, has_length=False)) == [bare.id]
    assert _ids(_list(mcp_client, admin_token, lifecycle_status="PAUSIERT")) == [paused.id]
    # Projects without a progress row count as AKTIV.
    assert paused.id not in _ids(_list(mcp_client, admin_token, lifecycle_status="AKTIV"))
    assert _ids(_list(mcp_client, admin_token, parl_befassung_relevant=True)) == [paused.id]

    # The override wins over the group default.
    db_session.query(ProjectProgress).filter_by(project_id=paused.id).update(
        {"parl_befassung_relevant": False}
    )
    db_session.query(ProjectProgress).filter_by(project_id=bare.id).update(
        {"parl_befassung_relevant": True}
    )
    db_session.commit()
    assert _ids(_list(mcp_client, admin_token, parl_befassung_relevant=True)) == [bare.id]
    assert paused.id in _ids(_list(mcp_client, admin_token, parl_befassung_relevant=False))


def _filtered(client, token, *filters, **arguments):
    return _list(client, token, filters=list(filters), **arguments)


def test_list_project_filters_catalog(mcp_client, admin_token):
    catalog = _payload(_call(mcp_client, admin_token, "list_project_filters"))
    fields = {f["field"]: f for f in catalog["fields"]}
    assert {"name", "project_number", "description", "closure", "phase"} <= set(fields)
    assert fields["phase"]["values"] and "BAU" in fields["phase"]["values"]
    assert "starts_with" in fields["description"]["operators"]
    # Every operator offered by a field is explained.
    assert {op for f in fields.values() for op in f["operators"]} <= set(catalog["operators"])


def test_list_projects_filters_closure(mcp_client, admin_token, db_session):
    complete, sketched, bare, paused = _seed(db_session)
    closure = {"field": "closure", "op": "eq", "value": True}
    assert _ids(_filtered(mcp_client, admin_token, closure)) == []
    db_session.query(Project).filter_by(id=paused.id).update({"closure": True})
    # An unset flag (NULL) counts as false.
    db_session.query(Project).filter_by(id=bare.id).update({"closure": None})
    db_session.commit()
    assert _ids(_filtered(mcp_client, admin_token, closure)) == [paused.id]
    others = _ids(_filtered(mcp_client, admin_token, {"field": "closure", "value": False}))
    assert paused.id not in others and bare.id in others


def test_list_projects_filters_text_and_number(mcp_client, admin_token, db_session):
    complete, sketched, bare, paused = _seed(db_session)
    db_session.query(Project).filter_by(id=sketched.id).update(
        {"description": "Reaktivierung der Strecke 50%_x"}
    )
    db_session.commit()
    starts = {"field": "description", "op": "starts_with", "value": "reaktivierung"}
    assert _ids(_filtered(mcp_client, admin_token, starts)) == [sketched.id]
    # LIKE wildcards in the value are literal.
    assert _ids(_filtered(mcp_client, admin_token, {"field": "description", "op": "contains", "value": "%_x"})) == [sketched.id]
    assert _ids(_filtered(mcp_client, admin_token, {"field": "description", "op": "contains", "value": "%x"})) == []
    assert _ids(_filtered(mcp_client, admin_token, {"field": "description", "op": "is_empty"})) == [bare.id]
    assert _ids(_filtered(mcp_client, admin_token, {"field": "name", "op": "ends_with", "value": "ULM"})) == [sketched.id]
    assert _ids(_filtered(mcp_client, admin_token, {"field": "length", "op": "gte", "value": 50})) == [complete.id, sketched.id]
    top_level = _filtered(mcp_client, admin_token, {"field": "superior_project_id", "op": "is_empty"})
    assert set(_ids(top_level)) == {bare.id, complete.id, paused.id, sketched.id}


def test_list_projects_filters_combine_with_named_parameters(mcp_client, admin_token, db_session):
    complete, sketched, bare, paused = _seed(db_session)
    result = _filtered(
        mcp_client, admin_token,
        {"field": "phase", "op": "in", "value": ["bau", "VORPLANUNG"]},
        {"field": "last_change", "op": "lte", "value": "2026-09-01"},
        project_group="TG",
    )
    assert _ids(result) == [complete.id]
    assert _ids(_filtered(mcp_client, admin_token, {"field": "project_group", "op": "ne", "value": "TG"})) == [paused.id]


def test_list_projects_filters_reject_bad_input(mcp_client, admin_token, db_session):
    _seed(db_session)
    for bad in (
        {"field": "nope", "value": 1},
        {"field": "closure", "op": "contains", "value": True},
        {"field": "closure", "value": "vielleicht"},
        {"field": "phase", "value": "KAPUTT"},
        {"field": "last_change", "op": "gte", "value": "gestern"},
        {"field": "description", "op": "contains"},
        {"field": "name", "value": "x", "extra": 1},
    ):
        assert _call(mcp_client, admin_token, "list_projects", {"filters": [bad]})["isError"], bad


def test_list_projects_updated_since_and_order(mcp_client, admin_token, db_session):
    complete, sketched, bare, paused = _seed(db_session)
    assert _ids(_list(mcp_client, admin_token, updated_since="2026-09-15")) == [sketched.id]
    newest_first = _list(mcp_client, admin_token, order_by="last_change", descending=True)
    # Never-changed projects go last, by name.
    assert _ids(newest_first) == [sketched.id, complete.id, bare.id, paused.id]
    by_length = _list(mcp_client, admin_token, order_by="length")
    assert _ids(by_length)[0] == paused.id and _ids(by_length)[-1] == bare.id


# --- list_data_gaps ----------------------------------------------------------


def test_list_data_gaps_all(mcp_client, admin_token, db_session):
    complete, sketched, bare, paused = _seed(db_session)
    result = _payload(_call(mcp_client, admin_token, "list_data_gaps"))
    gaps = {p["id"]: p["gaps"] for p in result["projects"]}
    assert complete.id not in gaps
    assert gaps[sketched.id] == ["no_route", "no_description"]
    assert gaps[bare.id] == [
        "no_geometry",
        "no_length",
        "unknown_phase",
        "no_description",
        "no_project_number",
    ]
    assert gaps[paused.id] == ["stale_observation"]
    assert result["total"] == 3
    assert result["counts"]["no_description"] == 2


def test_list_data_gaps_selection_group_and_paging(mcp_client, admin_token, db_session):
    complete, sketched, bare, paused = _seed(db_session)
    result = _payload(
        _call(mcp_client, admin_token, "list_data_gaps", {"gaps": ["no_route"], "project_group": "tg"})
    )
    assert _ids(result) == [sketched.id]
    assert result["counts"] == {"no_route": 1}
    assert result["stale_before"] is None

    page = _payload(_call(mcp_client, admin_token, "list_data_gaps", {"limit": 1, "offset": 1}))
    assert page["total"] == 3 and len(page["projects"]) == 1

    assert _call(mcp_client, admin_token, "list_data_gaps", {"project_group": "nope"})["isError"]
    assert _call(mcp_client, admin_token, "list_data_gaps", {"gaps": ["kaputt"]})["isError"]


def test_aggregating_parent_has_no_route_gap(mcp_client, admin_token, db_session):
    complete, *_ = _seed(db_session)
    parent = Project(
        name="Parent", project_number="9", description="x", length=1.0, is_draft=False,
        geojson_representation=complete.geojson_representation,
    )
    db_session.add(parent)
    db_session.flush()
    complete.superior_project_id = parent.id
    db_session.commit()
    result = _payload(_call(mcp_client, admin_token, "list_data_gaps", {"gaps": ["no_route"]}))
    assert parent.id not in _ids(result)


def test_list_data_gaps_drafts_filter(mcp_client, admin_token, db_session):
    _seed(db_session)
    draft = Project(name="Import-Entwurf", project_number="02 G 1_A", is_draft=True)
    db_session.add(draft)
    db_session.commit()
    default = _payload(_call(mcp_client, admin_token, "list_data_gaps", {"gaps": ["no_geometry"]}))
    assert draft.id not in _ids(default)
    only = _payload(
        _call(mcp_client, admin_token, "list_data_gaps", {"gaps": ["no_geometry"], "drafts": "only"})
    )
    assert _ids(only) == [draft.id] or set(_ids(only)) == {draft.id}
    assert only["projects"][0]["is_draft"] is True


# --- check_geometry ----------------------------------------------------------


def test_check_geometry_single_project(mcp_client, admin_token, db_session):
    _, sketched, _, _ = _seed(db_session)
    result = _payload(_call(mcp_client, admin_token, "check_geometry", {"project_id": sketched.id}))
    checks = [f["check"] for f in result["findings"]]
    # Chords; "Stuttgart" resolves to Stuttgart Hbf, far from the line at lon 9.0.
    assert checks == ["chords", "far_from_start"]
    assert result["has_saved_route"] is False
    assert [s["op_id"] for s in result["stations_from_name"]] == ["TS", "TU"]
    assert result["unresolved_places"] == []


def test_check_geometry_group(mcp_client, admin_token, db_session):
    complete, sketched, bare, _ = _seed(db_session)
    result = _payload(_call(mcp_client, admin_token, "check_geometry", {"project_group": "TG"}))
    assert result["checked"] == 3
    assert _ids(result) == [bare.id, sketched.id]
    assert result["counts"] == {"no_geometry": 1, "chords": 1, "far_from_start": 1}

    everything = _payload(
        _call(mcp_client, admin_token, "check_geometry", {"project_group": "TG", "only_findings": False})
    )
    assert everything["total"] == 3


def test_check_geometry_needs_exactly_one_target(mcp_client, admin_token, db_session):
    complete, *_ = _seed(db_session)
    assert _call(mcp_client, admin_token, "check_geometry")["isError"]
    assert _call(
        mcp_client, admin_token, "check_geometry", {"project_id": complete.id, "project_group": "TG"}
    )["isError"]
