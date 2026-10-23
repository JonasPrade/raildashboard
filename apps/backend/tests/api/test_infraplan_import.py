"""Tests for /api/v1/import/infraplan (stage 1: drafts, re-parse, page images)."""

from __future__ import annotations

import io

import fitz
import pytest

import dashboard_backend.database as database
from dashboard_backend.models.infraplan import InfraplanParseResult
from dashboard_backend.schemas.users import UserRole
from dashboard_backend.tasks.infraplan import parse_infraplan_pdf
from dashboard_backend.utils.file_storage import infraplan_pdf_exists, read_infraplan_pdf
from tests.api.conftest import basic_auth_header

BASE = "/api/v1/import/infraplan"


def _pdf_bytes(pages: int = 2) -> bytes:
    doc = fitz.open()
    for i in range(pages):
        doc.new_page().insert_text((72, 72), f"Seite {i + 1}")
    data = doc.tobytes()
    doc.close()
    return data


def _upload(data: bytes | None = None) -> dict:
    return {"pdf": ("infraplan.pdf", io.BytesIO(data or _pdf_bytes()), "application/pdf")}


@pytest.fixture(autouse=True)
def pdf_dir(tmp_path, monkeypatch):
    """Stored PDFs go to a directory of this test."""
    from dashboard_backend.core.config import settings

    monkeypatch.setattr(settings, "infraplan_pdf_dir", str(tmp_path / "infraplan"))


class _FakeResult:
    def __init__(self, task_id: str = "task-ip-1") -> None:
        self.id = task_id


@pytest.fixture()
def editor(create_user):
    create_user("editor-ip", "pass123", UserRole.editor)
    return basic_auth_header("editor-ip", "pass123")


@pytest.fixture()
def launched(monkeypatch):
    calls: list[int] = []

    def _delay(parse_result_id):
        calls.append(parse_result_id)
        return _FakeResult(f"task-{len(calls)}")

    monkeypatch.setattr(parse_infraplan_pdf, "delay", _delay)
    return calls


def _create_draft(client, editor, launched) -> int:
    resp = client.post(f"{BASE}/parse", files=_upload(), data={"year": "2026"}, headers=editor)
    assert resp.status_code == 200, resp.text
    return resp.json()["parse_result_id"]


# --- auth --------------------------------------------------------------------


def test_list_requires_auth(client):
    assert client.get(f"{BASE}/parse-result").status_code == 401


def test_parse_forbidden_for_viewer(client, create_user):
    create_user("viewer-ip", "pass123", UserRole.viewer)
    resp = client.post(
        f"{BASE}/parse",
        files=_upload(),
        data={"year": "2026"},
        headers=basic_auth_header("viewer-ip", "pass123"),
    )
    assert resp.status_code == 403


# --- upload ------------------------------------------------------------------


def test_parse_stores_pdf_and_starts_task(client, editor, launched, db_session):
    data = _pdf_bytes()
    resp = client.post(f"{BASE}/parse", files=_upload(data), data={"year": "2026"}, headers=editor)

    assert resp.status_code == 200
    body = resp.json()
    assert body["task_id"] == "task-1"
    assert launched == [body["parse_result_id"]]

    record = db_session.get(InfraplanParseResult, body["parse_result_id"])
    assert record.year == 2026
    assert record.status == "PENDING"
    assert record.task_id == "task-1"
    assert record.file_name == "infraplan.pdf"
    assert record.username_snapshot == "editor-ip"
    assert read_infraplan_pdf(record.pdf_path) == data


def test_parse_rejects_non_pdf(client, editor, launched):
    resp = client.post(
        f"{BASE}/parse",
        files={"pdf": ("x.pdf", io.BytesIO(b"not a pdf"), "application/pdf")},
        data={"year": "2026"},
        headers=editor,
    )
    assert resp.status_code == 400
    assert launched == []


def test_parse_requires_year(client, editor, launched):
    resp = client.post(f"{BASE}/parse", files=_upload(), headers=editor)
    assert resp.status_code == 422


# --- list / get / delete -----------------------------------------------------


def test_list_and_get_draft(client, editor, launched, db_session):
    draft_id = _create_draft(client, editor, launched)
    record = db_session.get(InfraplanParseResult, draft_id)
    record.status = "SUCCESS"
    record.result_json = {"sections": [], "rows": [], "footnotes": {}, "page_count": 2}
    record.warnings_json = [{"kind": "GAP", "section": "BP_A", "lfd_nr": 3, "message": "fehlt"}]
    record.kpi_pages_json = [{"page": 2, "kind": "STEUERUNG", "title": "Neu gebaute Gleiskilometer"}]
    db_session.commit()

    listed = client.get(f"{BASE}/parse-result", headers=editor).json()
    assert [d["id"] for d in listed] == [draft_id]
    assert "result_json" not in listed[0]
    assert listed[0]["row_count"] == 0
    assert listed[0]["warnings_json"][0]["kind"] == "GAP"

    one = client.get(f"{BASE}/parse-result/{draft_id}", headers=editor).json()
    assert one["has_pdf"] is True
    assert one["result_json"]["page_count"] == 2
    assert one["kpi_pages_json"][0]["title"] == "Neu gebaute Gleiskilometer"


def test_get_unknown_draft_is_404(client, editor):
    assert client.get(f"{BASE}/parse-result/999", headers=editor).status_code == 404


def test_delete_removes_draft_and_pdf(client, editor, launched, db_session):
    draft_id = _create_draft(client, editor, launched)
    pdf_path = db_session.get(InfraplanParseResult, draft_id).pdf_path

    resp = client.delete(f"{BASE}/parse-result/{draft_id}", headers=editor)

    assert resp.status_code == 204
    db_session.expire_all()
    assert db_session.get(InfraplanParseResult, draft_id) is None
    assert not infraplan_pdf_exists(pdf_path)


def test_delete_confirmed_draft_is_refused(client, editor, launched, db_session):
    from datetime import datetime

    draft_id = _create_draft(client, editor, launched)
    db_session.get(InfraplanParseResult, draft_id).confirmed_at = datetime.utcnow()
    db_session.commit()

    assert client.delete(f"{BASE}/parse-result/{draft_id}", headers=editor).status_code == 409


# --- reparse -----------------------------------------------------------------


def test_reparse_starts_task_again(client, editor, launched, db_session):
    draft_id = _create_draft(client, editor, launched)
    record = db_session.get(InfraplanParseResult, draft_id)
    record.status = "FAILURE"
    record.error_message = "kaputt"
    db_session.commit()

    resp = client.post(f"{BASE}/parse-result/{draft_id}/reparse", headers=editor)

    assert resp.status_code == 200
    assert resp.json() == {"task_id": "task-2", "parse_result_id": draft_id}
    db_session.refresh(record)
    assert (record.status, record.error_message, record.task_id) == ("PENDING", None, "task-2")


def test_reparse_without_pdf_is_refused(client, editor, launched, db_session):
    draft_id = _create_draft(client, editor, launched)
    db_session.get(InfraplanParseResult, draft_id).pdf_path = None
    db_session.commit()

    assert client.post(f"{BASE}/parse-result/{draft_id}/reparse", headers=editor).status_code == 409


# --- page image --------------------------------------------------------------


def test_page_image_renders_png(client, editor, launched):
    draft_id = _create_draft(client, editor, launched)

    resp = client.get(f"{BASE}/parse-result/{draft_id}/page/2.png?dpi=60", headers=editor)

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content.startswith(b"\x89PNG")


def test_page_image_out_of_range_is_404(client, editor, launched):
    draft_id = _create_draft(client, editor, launched)
    assert client.get(f"{BASE}/parse-result/{draft_id}/page/3.png", headers=editor).status_code == 404
    assert client.get(f"{BASE}/parse-result/{draft_id}/page/0.png", headers=editor).status_code == 404


def test_page_image_requires_permission(client, create_user, editor, launched):
    draft_id = _create_draft(client, editor, launched)
    create_user("viewer-ip2", "pass123", UserRole.viewer)
    resp = client.get(
        f"{BASE}/parse-result/{draft_id}/page/1.png",
        headers=basic_auth_header("viewer-ip2", "pass123"),
    )
    assert resp.status_code == 403


# --- task --------------------------------------------------------------------


@pytest.fixture()
def worker_db(tmp_path, monkeypatch):
    """A database of its own, as the worker has: the task commits and rolls
    back on its own session, which the per-test transaction cannot hold."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from dashboard_backend.models.infraplan import (
        InfraplanEntry,
        InfraplanEntryProject,
        InfraplanReport,
    )
    from dashboard_backend.models.projects.project import Project
    from dashboard_backend.models.projects.project_progress import ProjectProgress
    from dashboard_backend.models.users import User

    engine = create_engine(f"sqlite:///{tmp_path / 'worker.db'}")
    # The task also reads projects, their successors (replaced projects) and
    # earlier years for its suggestions.
    for model in (
        Project, ProjectProgress, User, InfraplanParseResult, InfraplanReport, InfraplanEntry, InfraplanEntryProject
    ):
        model.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(database, "Session", factory)
    yield factory
    engine.dispose()


def _draft_in(factory, pdf_path: str | None) -> int:
    with factory() as session:
        record = InfraplanParseResult(year=2026, file_name="infraplan.pdf", pdf_path=pdf_path)
        session.add(record)
        session.commit()
        return record.id


def test_task_parses_stored_pdf(worker_db):
    """The Celery task body reads the draft's PDF and stores rows + warnings.

    A PDF without measure tables parses fine but reports every section as
    missing — the warning that stops an unattended confirmation.
    """
    from dashboard_backend.utils.file_storage import save_infraplan_pdf

    draft_id = _draft_in(worker_db, save_infraplan_pdf(1, _pdf_bytes()))

    assert parse_infraplan_pdf.run(draft_id) == {"parse_result_id": draft_id}

    with worker_db() as session:
        record = session.get(InfraplanParseResult, draft_id)
        assert record.status == "SUCCESS"
        assert record.result_json["page_count"] == 2
        assert record.result_json["rows"] == []
        assert {w["kind"] for w in record.warnings_json} == {"EMPTY_SECTION"}
        assert record.kpi_pages_json == []


def test_task_records_failure(worker_db):
    draft_id = _draft_in(worker_db, None)

    with pytest.raises(FileNotFoundError):
        parse_infraplan_pdf.run(draft_id)

    with worker_db() as session:
        record = session.get(InfraplanParseResult, draft_id)
        assert record.status == "FAILURE"
        assert "Kein PDF" in record.error_message
