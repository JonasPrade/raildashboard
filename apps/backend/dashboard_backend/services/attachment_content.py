"""Read the content of a text attachment for the MCP tools — text of PDF pages,
text of a Word document (.docx), a PDF page as image.

Only stdlib and pymupdf (already a dependency); legacy Office formats and
spreadsheets are not read.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree

PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
IMAGES = {"image/png": "png", "image/jpeg": "jpeg"}

MAX_PAGES_PER_CALL = 10
MAX_CHARS = 40_000

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class AttachmentContentError(ValueError):
    pass


@dataclass
class TextResult:
    text: str
    truncated: bool
    page_count: int | None = None
    first_page: int | None = None
    last_page: int | None = None
    # PDF pages without a text layer (probably scans).
    empty_pages: tuple[int, ...] = ()


def _cut(text: str) -> tuple[str, bool]:
    if len(text) > MAX_CHARS:
        return text[: MAX_CHARS - 1] + "…", True
    return text, False


def pdf_text(data: bytes, page: int = 1, pages: int = 3) -> TextResult:
    """Text of ``pages`` PDF pages from ``page`` (1-indexed), page markers in between."""
    import fitz  # pymupdf

    pages = max(1, min(pages, MAX_PAGES_PER_CALL))
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # noqa: BLE001 - pymupdf raises its own types
        raise AttachmentContentError("Die PDF-Datei lässt sich nicht öffnen.") from exc
    with doc:
        count = doc.page_count
        if not 1 <= page <= count:
            raise AttachmentContentError(f"Seite {page} gibt es nicht (1–{count}).")
        last = min(count, page + pages - 1)
        texts = {n: doc[n - 1].get_text().strip() for n in range(page, last + 1)}
    parts = [f"--- Seite {n} ---\n{body}" for n, body in texts.items()]
    text, truncated = _cut("\n\n".join(parts))
    empty = tuple(n for n, body in texts.items() if not body)
    return TextResult(text, truncated, count, page, last, empty)


def docx_text(data: bytes) -> TextResult:
    """Paragraph text of a .docx (body only; tables row by row, cells separated by " | ")."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            xml = archive.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise AttachmentContentError("Die Word-Datei lässt sich nicht lesen.") from exc
    body = ElementTree.fromstring(xml).find(f"{_W}body")
    lines: list[str] = []
    for block in list(body) if body is not None else []:
        if block.tag == f"{_W}p":
            lines.append("".join(t.text or "" for t in block.iter(f"{_W}t")))
        elif block.tag == f"{_W}tbl":
            for row in block.iter(f"{_W}tr"):
                cells = [
                    "".join(t.text or "" for t in cell.iter(f"{_W}t")).strip()
                    for cell in row.iter(f"{_W}tc")
                ]
                lines.append(" | ".join(cells))
    text, truncated = _cut("\n".join(line for line in lines).strip())
    return TextResult(text, truncated)


def pdf_page_png(data: bytes, page: int, dpi: int) -> bytes:
    import fitz  # pymupdf

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise AttachmentContentError("Die PDF-Datei lässt sich nicht öffnen.") from exc
    with doc:
        if not 1 <= page <= doc.page_count:
            raise AttachmentContentError(f"Seite {page} gibt es nicht (1–{doc.page_count}).")
        return doc[page - 1].get_pixmap(dpi=max(50, min(dpi, 200))).tobytes("png")
