"""MCP tools reading text attachments: PDF text page by page, Word text,
PDF page / image file as image, and the ownership checks."""

from __future__ import annotations

import io
import zipfile

import fitz  # pymupdf
import pytest

from dashboard_backend.core.config import settings
from dashboard_backend.models.associations.text_to_project import TextToProject
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_text import ProjectText
from dashboard_backend.models.projects.project_text_type import ProjectTextType
from dashboard_backend.models.projects.text_attachment import TextAttachment
from dashboard_backend.services.attachment_content import DOCX, PDF
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _payload,
    admin_token,
    mcp_client,
)


def _pdf(pages: list[str]) -> bytes:
    doc = fitz.open()
    for body in pages:
        page = doc.new_page()
        if body:
            page.insert_text((72, 72), body)
    data = doc.tobytes()
    doc.close()
    return data


def _docx(paragraphs: list[str], row: list[str]) -> bytes:
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    cells = "".join(f"<w:tc><w:p><w:r><w:t>{c}</w:t></w:r></w:p></w:tc>" for c in row)
    xml = f'<?xml version="1.0"?><w:document {ns}><w:body>{body}<w:tbl><w:tr>{cells}</w:tr></w:tbl></w:body></w:document>'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return buffer.getvalue()


PNG = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 2, 2), False).tobytes("png")


@pytest.fixture()
def seeded(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    project = Project(name="ABS Beispiel", is_draft=False)
    other = Project(name="Anderes Projekt", is_draft=False)
    text_type = ProjectTextType(name="Info")
    db_session.add_all([project, other, text_type])
    db_session.flush()
    text = ProjectText(header="Planfeststellung", text="…", type=text_type.id)
    db_session.add(text)
    db_session.flush()
    db_session.add(TextToProject(text_id=text.id, project_id=project.id))

    files = {
        "pfb.pdf": (PDF, _pdf(["Seite eins Beschluss", "", "Seite drei Auflagen"])),
        "notiz.docx": (DOCX, _docx(["Erster Absatz", "Zweiter Absatz"], ["PFA 1", "2027"])),
        "plan.png": ("image/png", PNG),
        "kosten.xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", b"PK"),
    }
    attachments = {}
    for name, (mime, data) in files.items():
        stored = f"{name}.bin"
        (tmp_path / str(text.id)).mkdir(exist_ok=True)
        (tmp_path / str(text.id) / stored).write_bytes(data)
        attachment = TextAttachment(
            text_id=text.id, filename=name, stored_filename=stored, mime_type=mime, file_size=len(data)
        )
        db_session.add(attachment)
        db_session.flush()
        attachments[name] = attachment.id
    missing = TextAttachment(
        text_id=text.id, filename="weg.pdf", stored_filename="weg.pdf", mime_type=PDF, file_size=1
    )
    db_session.add(missing)
    db_session.commit()
    attachments["weg.pdf"] = missing.id
    return {"project": project.id, "other": other.id, "text": text.id, "attachments": attachments}


def _read(client, token, seeded, name, **extra):
    args = {
        "project_id": seeded["project"],
        "text_id": seeded["text"],
        "attachment_id": seeded["attachments"][name],
        **extra,
    }
    return _call(client, token, "read_text_attachment", args)


def test_pdf_text_paged_with_empty_pages(mcp_client, admin_token, seeded):
    first = _payload(_read(mcp_client, admin_token, seeded, "pfb.pdf", pages=2))
    assert first["page_count"] == 3 and first["pages"] == [1, 2] and first["next_page"] == 3
    assert "Seite eins Beschluss" in first["text"]
    assert first["empty_pages"] == [2] and "gescannt" in first["note"]
    rest = _payload(_read(mcp_client, admin_token, seeded, "pfb.pdf", page=3))
    assert "Auflagen" in rest["text"] and rest["next_page"] is None
    beyond = _read(mcp_client, admin_token, seeded, "pfb.pdf", page=9)
    assert beyond["isError"] is True and "1–3" in beyond["content"][0]["text"]


def test_docx_text_and_unsupported_formats(mcp_client, admin_token, seeded):
    docx = _payload(_read(mcp_client, admin_token, seeded, "notiz.docx"))
    assert docx["text"] == "Erster Absatz\nZweiter Absatz\nPFA 1 | 2027"
    assert "page_count" not in docx
    for name, hint in (("plan.png", "get_text_attachment_image"), ("kosten.xlsx", "Oberfläche")):
        result = _read(mcp_client, admin_token, seeded, name)
        assert result["isError"] is True and hint in result["content"][0]["text"]


def test_images(mcp_client, admin_token, seeded):
    for name in ("pfb.pdf", "plan.png"):
        result = _call(
            mcp_client,
            admin_token,
            "get_text_attachment_image",
            {
                "project_id": seeded["project"],
                "text_id": seeded["text"],
                "attachment_id": seeded["attachments"][name],
            },
        )
        assert result["isError"] is False
        assert result["content"][0]["type"] == "image"
        assert result["content"][0]["mimeType"] == "image/png"


def test_ownership_and_missing_file(mcp_client, admin_token, seeded):
    foreign = _call(
        mcp_client,
        admin_token,
        "read_text_attachment",
        {
            "project_id": seeded["other"],
            "text_id": seeded["text"],
            "attachment_id": seeded["attachments"]["pfb.pdf"],
        },
    )
    assert foreign["isError"] is True and "gehört nicht" in foreign["content"][0]["text"]
    gone = _read(mcp_client, admin_token, seeded, "weg.pdf")
    assert gone["isError"] is True and "fehlt" in gone["content"][0]["text"]
