"""Text categories and text visibility (docs/features/feature-text-categories.md)."""
from __future__ import annotations

import pytest

from dashboard_backend.models.associations.text_to_project import TextToProject
from dashboard_backend.models.change_tracking.change_log import TextChangeLog
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_text import ProjectText
from dashboard_backend.models.projects.project_text_category import ProjectTextCategory
from dashboard_backend.models.projects.project_text_type import ProjectTextType
from dashboard_backend.models.projects.text_attachment import TextAttachment
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header

EDITOR = basic_auth_header("editor", "pass123")


@pytest.fixture()
def editor(create_user):
    return create_user("editor", "pass123", UserRole.editor)


@pytest.fixture()
def seeded(db_session):
    """Project, text type and the two migration-seeded categories."""
    project = Project(name="Testprojekt")
    text_type = ProjectTextType(name="Kommentar")
    info = ProjectTextCategory(name="Info", style="info")
    warning = ProjectTextCategory(name="Warnung", style="warning")
    db_session.add_all([project, text_type, info, warning])
    db_session.commit()
    return {"project": project, "type": text_type, "info": info, "warning": warning}


def _add_text(db, project, text_type, *, is_public=True, category=None):
    text = ProjectText(
        header="Hinweis",
        type=text_type.id,
        is_public=is_public,
        category_id=category.id if category else None,
    )
    db.add(text)
    db.flush()
    db.add(TextToProject(project_id=project.id, text_id=text.id))
    db.commit()
    return text


# --- Categories --------------------------------------------------------------


def test_list_text_categories_is_public(client, seeded):
    resp = client.get("/api/v1/text_categories")
    assert resp.status_code == 200
    assert [(c["name"], c["style"]) for c in resp.json()] == [("Info", "info"), ("Warnung", "warning")]


def test_create_text_category(client, editor, seeded):
    resp = client.post(
        "/api/v1/text_categories", json={"name": "Kritisch", "style": "critical"}, headers=EDITOR
    )
    assert resp.status_code == 201
    assert resp.json()["style"] == "critical"


def test_create_text_category_rejects_unknown_style(client, editor, seeded):
    resp = client.post(
        "/api/v1/text_categories", json={"name": "Bunt", "style": "pink"}, headers=EDITOR
    )
    assert resp.status_code == 422


def test_create_text_category_rejects_duplicate_name(client, editor, seeded):
    resp = client.post(
        "/api/v1/text_categories", json={"name": "warnung", "style": "critical"}, headers=EDITOR
    )
    assert resp.status_code == 409


def test_create_text_category_requires_editor(client, create_user, seeded):
    create_user("viewer", "pass123", UserRole.viewer)
    resp = client.post(
        "/api/v1/text_categories",
        json={"name": "Kritisch", "style": "critical"},
        headers=basic_auth_header("viewer", "pass123"),
    )
    assert resp.status_code == 403


def test_create_text_defaults_to_info(client, editor, seeded):
    resp = client.post(
        f"/api/v1/projects/{seeded['project'].id}/texts",
        json={"header": "Neu", "type": seeded["type"].id},
        headers=EDITOR,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["category"]["name"] == "Info"
    assert body["is_public"] is True


def test_create_text_with_unknown_category_is_422(client, editor, seeded):
    resp = client.post(
        f"/api/v1/projects/{seeded['project'].id}/texts",
        json={"header": "Neu", "type": seeded["type"].id, "category_id": 999},
        headers=EDITOR,
    )
    assert resp.status_code == 422


def test_update_category_is_logged(client, editor, seeded, db_session):
    text = _add_text(db_session, seeded["project"], seeded["type"], category=seeded["info"])

    resp = client.patch(
        f"/api/v1/projects/texts/{text.id}",
        json={"category_id": seeded["warning"].id},
        headers=EDITOR,
    )
    assert resp.status_code == 200
    assert resp.json()["category"]["style"] == "warning"

    log = db_session.query(TextChangeLog).filter(TextChangeLog.text_id == text.id).one()
    # Only the sent field is recorded, not the untouched ones.
    assert [e.field_name for e in log.entries] == ["category_id"]


def test_update_category_to_null_is_422(client, editor, seeded, db_session):
    text = _add_text(db_session, seeded["project"], seeded["type"], category=seeded["info"])
    resp = client.patch(
        f"/api/v1/projects/texts/{text.id}", json={"category_id": None}, headers=EDITOR
    )
    assert resp.status_code == 422


# --- Visibility --------------------------------------------------------------


def test_internal_texts_hidden_from_anonymous(client, editor, seeded, db_session):
    _add_text(db_session, seeded["project"], seeded["type"], is_public=True)
    _add_text(db_session, seeded["project"], seeded["type"], is_public=False)
    url = f"/api/v1/projects/{seeded['project'].id}/texts"

    anonymous = client.get(url)
    assert anonymous.status_code == 200
    assert [t["is_public"] for t in anonymous.json()] == [True]

    signed_in = client.get(url, headers=EDITOR)
    assert sorted(t["is_public"] for t in signed_in.json()) == [False, True]


def test_expired_session_counts_as_anonymous(client, seeded, db_session):
    _add_text(db_session, seeded["project"], seeded["type"], is_public=False)
    client.cookies.set("session", "invalid.token")
    resp = client.get(f"/api/v1/projects/{seeded['project'].id}/texts")
    assert resp.status_code == 200
    assert resp.json() == []


def test_wrong_credentials_still_fail(client, editor, seeded):
    resp = client.get(
        f"/api/v1/projects/{seeded['project'].id}/texts",
        headers=basic_auth_header("editor", "wrong"),
    )
    assert resp.status_code == 401


def test_internal_attachments_hidden_from_anonymous(client, editor, seeded, db_session):
    text = _add_text(db_session, seeded["project"], seeded["type"], is_public=False)
    attachment = TextAttachment(
        text_id=text.id,
        filename="intern.pdf",
        stored_filename="missing.pdf",
        mime_type="application/pdf",
        file_size=1,
    )
    db_session.add(attachment)
    db_session.commit()

    assert client.get(f"/api/v1/projects/texts/{text.id}/attachments").status_code == 404
    download = f"/api/v1/projects/texts/{text.id}/attachments/{attachment.id}/download"
    assert client.get(download).status_code == 404

    assert client.get(f"/api/v1/projects/texts/{text.id}/attachments", headers=EDITOR).status_code == 200


def test_text_without_category_has_null_category(client, seeded, db_session):
    """Texts written by older code (after a rollback) carry no category."""
    _add_text(db_session, seeded["project"], seeded["type"], category=None)
    resp = client.get(f"/api/v1/projects/{seeded['project'].id}/texts")
    assert resp.json()[0]["category"] is None
