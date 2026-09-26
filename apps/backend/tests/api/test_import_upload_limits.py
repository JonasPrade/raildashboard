"""Upload ceiling shared by the three PDF importers.

All of them read the upload into memory before handing it to a Celery task, so
``deps.read_upload_within_limit`` is the single gate. The nginx in front of the
app enforces the same 50 MB (``apps/frontend/nginx.conf``); these tests cover
the backend backstop for requests that reach it directly.
"""

from __future__ import annotations

import io

import pytest

import dashboard_backend.api.deps as deps
from dashboard_backend.schemas.users import UserRole
from tests.api.conftest import basic_auth_header
from dashboard_backend.utils.file_storage import MAX_FILE_SIZE

# Every importer takes the file as ``pdf`` plus a report year.
PARSE_ENDPOINTS = [
    "/api/v1/import/haushalt/parse",
    "/api/v1/import/vib/parse",
    "/api/v1/import/fulda/parse",
]


def _pdf_upload(payload_size: int) -> dict:
    """A well-formed PDF upload of roughly ``payload_size`` bytes."""
    body = b"%PDF-1.4 " + b"x" * payload_size
    return {"pdf": ("bericht.pdf", io.BytesIO(body), "application/pdf")}


@pytest.mark.parametrize("path", PARSE_ENDPOINTS)
def test_parse_rejects_upload_above_the_limit(client, create_user, monkeypatch, path):
    """413 instead of pulling a huge body through the broker.

    The limit is patched down rather than posting 50 MB three times; the
    user-facing text still names the real ceiling, which is asserted below.
    """
    username = f"editor-{path.rsplit('/', 2)[-2]}"
    create_user(username, "pass123", UserRole.editor)
    monkeypatch.setattr(deps, "MAX_FILE_SIZE", 1024)

    resp = client.post(
        path,
        files=_pdf_upload(4096),
        data={"year": "2027"},
        headers=basic_auth_header(username, "pass123"),
    )

    assert resp.status_code == 413
    assert "50 MB" in resp.json()["detail"]


@pytest.mark.parametrize("path", PARSE_ENDPOINTS)
def test_parse_accepts_upload_below_the_limit(client, create_user, monkeypatch, path):
    """A file under the ceiling is not rejected by the size check."""
    username = f"editor-ok-{path.rsplit('/', 2)[-2]}"
    create_user(username, "pass123", UserRole.editor)
    monkeypatch.setattr(deps, "MAX_FILE_SIZE", 1024)

    class _FakeResult:
        id = "task-1"

    for module_name, task_name in (
        ("haushalt", "parse_haushalt_pdf"),
        ("vib", "parse_vib_pdf"),
        ("fulda", "parse_fulda_pdf"),
    ):
        module = __import__(
            f"dashboard_backend.api.v1.endpoints.{module_name}_import",
            fromlist=[task_name],
        )
        monkeypatch.setattr(getattr(module, task_name), "delay", lambda *a, **k: _FakeResult())

    resp = client.post(
        path,
        files=_pdf_upload(64),
        data={"year": "2027"},
        headers=basic_auth_header(username, "pass123"),
    )

    assert resp.status_code == 200


def test_limit_message_names_the_real_ceiling():
    """The detail text and the constant must not drift apart."""
    assert MAX_FILE_SIZE == 50 * 1024 * 1024
    assert deps.UPLOAD_TOO_LARGE == "Datei zu groß. Maximal 50 MB erlaubt."
