"""MCP maintenance additions: archived listing, text deletion and attachments,
project-group settings and timeline, track documents, recompute, set-back
conflicts, Sammel-FinVe phases and the system status."""

from __future__ import annotations

import json
from datetime import date

import dashboard_backend.mcp.tools.system as system_tools
from dashboard_backend.models.associations.document_to_projects import DocumentToProject
from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.projects.document import Document
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.models.projects.project_text_type import ProjectTextType
from dashboard_backend.models.projects.text_attachment import TextAttachment
from dashboard_backend.schemas.system import RoutingHealthSchema
from dashboard_backend.schemas.tasks import WorkerHealthSchema
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _key_for,
    _payload,
    _role_user,
    _seed_projects,
    admin_token,
    mcp_client,
)


def _list(result):
    """A tool returning a list: one content item per element (none for [])."""
    assert result["isError"] is False, result
    structured = result.get("structuredContent")
    if structured is not None and "result" in structured:
        return structured["result"]
    return [json.loads(item["text"]) for item in result["content"]]


# --- archived projects ---------------------------------------------------------


def test_list_projects_archived_filter(mcp_client, admin_token, db_session):
    alpha, beta = _seed_projects(db_session)
    _payload(
        _call(
            mcp_client,
            admin_token,
            "archive_project",
            {"project_id": alpha.id, "reason": "ersetzt", "replaced_by_project_id": beta.id},
        )
    )
    default = _payload(_call(mcp_client, admin_token, "list_projects"))
    assert [p["id"] for p in default["projects"]] == [beta.id]
    assert "is_archived" not in default["projects"][0]

    only = _payload(_call(mcp_client, admin_token, "list_projects", {"archived": "only"}))
    assert [p["id"] for p in only["projects"]] == [alpha.id]
    assert only["projects"][0]["is_archived"] is True
    assert only["projects"][0]["replaced_by_project_id"] == beta.id

    both = _payload(_call(mcp_client, admin_token, "list_projects", {"archived": "include"}))
    assert both["total"] == 2


# --- project texts -------------------------------------------------------------


def test_texts_list_attachments_and_delete(mcp_client, admin_token, db_session):
    alpha, beta = _seed_projects(db_session)
    text_type = ProjectTextType(name="Info")
    db_session.add(text_type)
    db_session.commit()
    created = _payload(
        _call(
            mcp_client,
            admin_token,
            "upsert_project_text",
            {"project_id": alpha.id, "header": "Doppelt", "text": "A", "text_type_id": text_type.id},
        )
    )
    db_session.add(
        TextAttachment(
            text_id=created["id"],
            filename="plan.pdf",
            stored_filename="x.pdf",
            mime_type="application/pdf",
            file_size=1234,
        )
    )
    db_session.commit()
    texts = _list(_call(mcp_client, admin_token, "get_project_texts", {"project_id": alpha.id}))
    assert texts[0]["attachments"] == [
        {"id": texts[0]["attachments"][0]["id"], "filename": "plan.pdf", "mime_type": "application/pdf", "file_size": 1234}
    ]

    wrong = _call(
        mcp_client, admin_token, "delete_project_text", {"project_id": beta.id, "text_id": created["id"]}
    )
    assert wrong["isError"] is True
    deleted = _payload(
        _call(
            mcp_client, admin_token, "delete_project_text", {"project_id": alpha.id, "text_id": created["id"]}
        )
    )
    assert deleted == {"deleted": created["id"], "header": "Doppelt", "linked_projects": [alpha.id]}
    assert _list(_call(mcp_client, admin_token, "get_project_texts", {"project_id": alpha.id})) == []
    history = _payload(
        _call(mcp_client, admin_token, "get_project_text_changelog", {"project_id": alpha.id})
    )
    assert history["events"][0]["action"] == "DELETE"
    assert db_session.query(TextAttachment).count() == 0


# --- project groups ------------------------------------------------------------


def test_update_project_group(mcp_client, admin_token, db_session):
    _seed_projects(db_session)
    other = ProjectGroup(name="Deutschlandtakt", short_name="DT", color="#111111")
    db_session.add(other)
    db_session.commit()
    updated = _payload(
        _call(
            mcp_client,
            admin_token,
            "update_project_group",
            {
                "group": "bp",
                "description": "Bedarfsplan Schiene",
                "skipped_phases": ["VORPLANUNG"],
                "assumed_build_months": 48,
            },
        )
    )
    assert updated["short_name"] == "BP"
    assert updated["description"] == "Bedarfsplan Schiene"
    assert updated["skipped_phases"] == ["VORPLANUNG"]
    assert updated["assumed_build_months"] == 48

    cleared = _payload(
        _call(
            mcp_client,
            admin_token,
            "update_project_group",
            {"group": "BP", "clear_assumed_build_months": True},
        )
    )
    assert cleared["assumed_build_months"] is None

    clash = _call(mcp_client, admin_token, "update_project_group", {"group": "BP", "short_name": "DT"})
    assert clash["isError"] is True and "vergeben" in clash["content"][0]["text"]
    assert _call(mcp_client, admin_token, "update_project_group", {"group": "BP"})["isError"] is True
    assert _call(mcp_client, admin_token, "update_project_group", {"group": "XX", "public": True})["isError"] is True

    reader = _key_for(db_session, _role_user(db_session, "leser", ["mcp.access"]))
    denied = _call(mcp_client, reader, "update_project_group", {"group": "BP", "public": True})
    assert denied["isError"] is True and "projectgroup.edit" in denied["content"][0]["text"]


def test_project_group_timeline(mcp_client, admin_token, db_session):
    alpha, _ = _seed_projects(db_session)
    db_session.add(
        ProgressObservation(
            project_id=alpha.id,
            source_type="MANUELL",
            track="MAIN",
            asserted_state="BAU",
            observed_date=date(2027, 3, 1),
            is_expected=True,
            is_derived=False,
        )
    )
    db_session.commit()
    timeline = _payload(_call(mcp_client, admin_token, "get_project_group_timeline", {"group": "BP"}))
    assert timeline["group"]["short_name"] == "BP"
    assert [item["project_id"] for item in timeline["items"]] == [alpha.id]


# --- planning state --------------------------------------------------------------


def test_track_documents_and_recompute(mcp_client, admin_token, db_session):
    alpha, _ = _seed_projects(db_session)
    doc = Document(title="Planfeststellungsbeschluss PFA 1", file_path="/x.pdf", source="EBA")
    stray = Document(title="Unbeteiligt", file_path="/y.pdf")
    db_session.add_all([doc, stray])
    db_session.flush()
    db_session.add(DocumentToProject(project_id=alpha.id, document_id=doc.id))
    db_session.commit()

    listed = _payload(_call(mcp_client, admin_token, "list_project_documents", {"project_id": alpha.id}))
    assert [(d["id"], d["tracks"]) for d in listed["documents"]] == [(doc.id, [])]

    progress = _payload(
        _call(
            mcp_client,
            admin_token,
            "set_track_document",
            {"project_id": alpha.id, "track": "PF", "document_id": doc.id},
        )
    )
    assert [d["id"] for d in progress["pf_documents"]] == [doc.id]
    listed = _payload(_call(mcp_client, admin_token, "list_project_documents", {"project_id": alpha.id}))
    assert listed["documents"][0]["tracks"] == ["PF"]

    unlinked = _payload(
        _call(
            mcp_client,
            admin_token,
            "set_track_document",
            {"project_id": alpha.id, "track": "PF", "document_id": doc.id, "linked": False},
        )
    )
    assert unlinked["pf_documents"] == []
    again = _call(
        mcp_client,
        admin_token,
        "set_track_document",
        {"project_id": alpha.id, "track": "PF", "document_id": doc.id, "linked": False},
    )
    assert again["isError"] is True
    missing = _call(
        mcp_client,
        admin_token,
        "set_track_document",
        {"project_id": alpha.id, "track": "PARL", "document_id": 9999},
    )
    assert missing["isError"] is True

    recomputed = _payload(
        _call(mcp_client, admin_token, "recompute_project_progress", {"project_id": alpha.id})
    )
    assert recomputed["project_id"] == alpha.id


def test_progress_conflicts(mcp_client, admin_token, db_session, monkeypatch):
    import dashboard_backend.mcp.tools.planning as planning_tools

    rows = [
        {
            "project_id": pid,
            "project_name": f"ABS {pid}",
            "project_number": None,
            "computed_phase": "BAU",
            "conflict": {
                "observation_id": 2,
                "source_type": "VIB",
                "asserted_phase": "VORPLANUNG",
                "observed_date": "2025-12-31",
                "trust": 0.6,
                "contradicted_ids": [1],
                "contradicted_phase": "BAU",
                "applied": False,
            },
            "contradicted": [],
        }
        for pid in (7, 8, 9)
    ]
    monkeypatch.setattr(planning_tools.progress_crud, "list_progress_conflicts", lambda db: rows)
    result = _payload(_call(mcp_client, admin_token, "list_progress_conflicts", {"limit": 2, "offset": 1}))
    assert result["total"] == 3
    assert [row["project_id"] for row in result["conflicts"]] == [8, 9]
    assert result["conflicts"][0]["conflict"]["applied"] is False

    reader = _key_for(db_session, _role_user(db_session, "leser", ["mcp.access"]))
    assert _call(mcp_client, reader, "list_progress_conflicts")["isError"] is True


# --- Sammel-FinVe ----------------------------------------------------------------


def test_sammel_finve_phase(mcp_client, admin_token, db_session):
    alpha, _ = _seed_projects(db_session)
    sammel = Finve(id=7001, name="SV Sammelvereinbarung ohne Phase", is_sammel_finve=True)
    regular = Finve(id=7002, name="ABS Alpha", is_sammel_finve=False)
    db_session.add_all([sammel, regular])
    db_session.flush()
    db_session.add(FinveToProject(finve_id=sammel.id, project_id=alpha.id))
    db_session.commit()

    open_ = _payload(_call(mcp_client, admin_token, "list_sammel_finve_phases", {"only_open": True}))
    assert [f["finve_id"] for f in open_["finves"]] == [sammel.id]
    assert open_["finves"][0]["projects"] == [{"id": alpha.id, "name": alpha.name}]

    result = _payload(
        _call(
            mcp_client,
            admin_token,
            "set_sammel_finve_phase",
            {"finve_id": sammel.id, "progress_phase": "VORPLANUNG"},
        )
    )
    assert result["finve"]["effective_phase"] == "VORPLANUNG"
    assert result["recomputed_project_ids"] == [alpha.id]
    assert _payload(_call(mcp_client, admin_token, "list_sammel_finve_phases", {"only_open": True}))["total"] == 0

    cleared = _payload(_call(mcp_client, admin_token, "set_sammel_finve_phase", {"finve_id": sammel.id}))
    assert cleared["finve"]["progress_phase"] is None
    assert _call(
        mcp_client, admin_token, "set_sammel_finve_phase", {"finve_id": regular.id, "progress_phase": "BAU"}
    )["isError"] is True


# --- system status -----------------------------------------------------------------


def test_system_status(mcp_client, admin_token, db_session, monkeypatch):
    monkeypatch.setattr(
        system_tools,
        "routing_health",
        lambda: RoutingHealthSchema(
            status="ok", base_url="http://routing", message="Routing läuft.", checked_at=0.0
        ),
    )
    monkeypatch.setattr(
        system_tools,
        "cached_worker_health",
        lambda: WorkerHealthSchema(
            status="ok", broker_reachable=True, broker_url="redis://broker", message="Worker laufen.", checked_at=0.0
        ),
    )
    status = _payload(_call(mcp_client, admin_token, "get_system_status"))
    assert status["routing"]["status"] == "ok"
    assert status["workers"]["broker_reachable"] is True

    editor = _key_for(db_session, _role_user(db_session, "editor2", ["mcp.access", "project.edit"]))
    denied = _call(mcp_client, editor, "get_system_status")
    assert denied["isError"] is True and "settings.manage" in denied["content"][0]["text"]
