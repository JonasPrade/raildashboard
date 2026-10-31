"""MCP Medien/Presse tools: the agent writes a report it read; confirming it
materialises a low-trust MEDIEN observation."""

from __future__ import annotations

from dashboard_backend.models.projects.media_report import MediaReport
from dashboard_backend.models.projects.project import Project
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _key_for,
    _payload,
    _role_user,
    admin_token,
    mcp_client,
)

URL = "https://zeitung.example/artikel-gaeubahn"


def _project(db, name="Gäubahn Stuttgart – Singen"):
    project = Project(name=name, is_draft=False)
    db.add(project)
    db.commit()
    return project


def _report(client, token, **overrides):
    args = {
        "url": URL,
        "publication": "Stuttgarter Zeitung",
        "published_date": "2026-10-20",
        "quote": "Die Bauarbeiten am Pfaffensteigtunnel haben begonnen.",
    }
    args.update(overrides)
    return _call(client, token, "add_media_report", args)


def _media_observations(client, token, project_id):
    progress = _payload(_call(client, token, "get_project_progress", {"project_id": project_id}))
    return [o for o in progress["observations"] if o["source_type"] == "MEDIEN"]


def test_review_flow_confirm_materialises(mcp_client, admin_token, db_session):
    project = _project(db_session)
    added = _payload(
        _report(mcp_client, admin_token, project_id=project.id, asserted_phase="BAU")
    )
    assert added["confirmed"] is False and added["feeds_planning_state"] is False
    assert added["observed_date"] == "2026-10-20"  # defaults to published_date
    assert not _media_observations(mcp_client, admin_token, project.id)

    listed = _payload(
        _call(mcp_client, admin_token, "list_media_reports", {"only_unconfirmed": True, "search": "zeitung.example"})
    )
    assert [r["id"] for r in listed["reports"]] == [added["id"]]

    confirmed = _payload(
        _call(mcp_client, admin_token, "update_media_report", {"report_id": added["id"], "confirmed": True})
    )
    assert confirmed["feeds_planning_state"] is True
    observations = _media_observations(mcp_client, admin_token, project.id)
    assert len(observations) == 1
    assert observations[0]["asserted_state"] == "BAU"
    assert "Stuttgarter Zeitung" in observations[0]["note"]

    _payload(_call(mcp_client, admin_token, "delete_media_report", {"report_id": added["id"]}))
    assert not _media_observations(mcp_client, admin_token, project.id)
    assert db_session.query(MediaReport).count() == 0


def test_add_confirmed_counts_at_once_and_duplicates_are_refused(mcp_client, admin_token, db_session):
    project = _project(db_session)
    other = _project(db_session, "Stuttgart 21")
    _payload(
        _report(mcp_client, admin_token, project_id=project.id, asserted_phase="BAU", confirmed=True)
    )
    assert len(_media_observations(mcp_client, admin_token, project.id)) == 1

    again = _report(mcp_client, admin_token, project_id=project.id)
    assert again["isError"] is True and "schon" in again["content"][0]["text"]
    # The same article for another project is a separate report.
    assert _payload(_report(mcp_client, admin_token, project_id=other.id))["project_id"] == other.id
    by_project = _payload(_call(mcp_client, admin_token, "list_media_reports", {"project_id": other.id}))
    assert by_project["total"] == 1


def test_confirm_without_project_or_phase_warns(mcp_client, admin_token, db_session):
    project = _project(db_session)
    loose = _payload(_report(mcp_client, admin_token, confirmed=True))
    assert loose["confirmed"] is False and loose["warnings"]

    attached = _payload(
        _call(
            mcp_client,
            admin_token,
            "update_media_report",
            {"report_id": loose["id"], "project_id": project.id, "confirmed": True},
        )
    )
    assert attached["confirmed"] is True
    assert attached["feeds_planning_state"] is False
    assert any("asserted_phase" in w for w in attached["warnings"])

    cleared = _payload(
        _call(mcp_client, admin_token, "update_media_report", {"report_id": loose["id"], "clear_project": True})
    )
    assert cleared["project_id"] is None and cleared["confirmed"] is False


def test_errors_and_permission(mcp_client, admin_token, db_session):
    assert _report(mcp_client, admin_token, project_id=99999)["isError"] is True
    assert _report(mcp_client, admin_token, quote=" ")["isError"] is True
    assert _call(mcp_client, admin_token, "update_media_report", {"report_id": 5})["isError"] is True
    assert _call(
        mcp_client, admin_token, "update_media_report", {"report_id": 5, "confirmed": True}
    )["isError"] is True
    assert _call(mcp_client, admin_token, "delete_media_report", {"report_id": 5})["isError"] is True

    reader = _key_for(db_session, _role_user(db_session, "leser", ["mcp.access"]))
    for name, args in (("list_media_reports", {}), ("delete_media_report", {"report_id": 1})):
        result = _call(mcp_client, reader, name, args)
        assert result["isError"] is True and "progress.edit" in result["content"][0]["text"]
