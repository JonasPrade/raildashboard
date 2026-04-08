"""VIB PDF text extraction — Mistral OCR or pymupdf fallback.

Pipeline:
  1. Pass full PDF bytes to Mistral OCR API (one call, returns pages).
  2. Per page: inline table content (page.tables) into the markdown,
     optionally skip page.header / page.footer, strip image refs.
  3. Join ALL page markdowns into full_text — _parse_vib_pdf handles
     section filtering.
  4. Return (full_text, model_used, ocr_status) for persistence in VibDraftReport.

Mistral OCR page object fields used here:
  page.markdown  — body text with [tbl-N.md](tbl-N.md) placeholders for tables
  page.tables    — list of OCRTableObject(id, content, format)
  page.images    — list of OCRImageObject (referenced as ![img-N.*](img-N.*))
  page.header    — page header string (already separated by the API)
  page.footer    — page footer string (already separated by the API)

Why full text (not just section B):
  _parse_vib_pdf needs the TOC (before section B) for canonical project names
  and uses position-based boundary detection across the full document.

Fallback (no OCR_API_KEY): use pymupdf get_text("text") per page.
"""
from __future__ import annotations

import base64
import io
import logging
import re
from types import SimpleNamespace

import fitz  # pymupdf — fallback text extraction
from mistralai.client import Mistral

logger = logging.getLogger(__name__)

_RAIL_START_RE = re.compile(r"\bB\s+Schienenwege\b", re.IGNORECASE)
_RAIL_END_RE = re.compile(r"\bC\s+Bundesfernstra", re.IGNORECASE)

# Inline image references produced by Mistral OCR: ![alt](filename)
_IMAGE_REF_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)", re.IGNORECASE)


def _find_rail_section_pages(pages: list) -> list:
    """Return only the pages belonging to section B (Schienenwege).

    Utility for debugging. Not used in the main extraction flow —
    _parse_vib_pdf handles section filtering on the full text.
    Falls back to all pages if section B is not found.
    """
    start: int | None = None
    end: int | None = None

    for i, page in enumerate(pages):
        text = _page_to_text(page, strip_headers_footers=False, strip_images=False)
        if start is None and _RAIL_START_RE.search(text):
            start = i
        elif start is not None and end is None and _RAIL_END_RE.search(text):
            end = i
            break

    if start is None:
        logger.warning("Section B (Schienenwege) not found — using all pages")
        return pages

    return pages[start:end]


def _inline_tables(markdown: str, tables: list) -> str:
    """Replace [tbl-N.md](tbl-N.md) placeholders with the actual table content.

    Mistral OCR puts table text in page.tables[i].content and inserts a
    link placeholder in page.markdown.  The link target is the table id
    with a ".md" suffix, e.g. id="tbl-3" → "[tbl-3.md](tbl-3.md)".
    """
    for tbl in tables:
        tbl_id: str = tbl.id  # e.g. "tbl-3"
        content: str = tbl.content or ""
        # Replace the placeholder — try both with and without .md suffix
        for ref in (
            f"[{tbl_id}.md]({tbl_id}.md)",
            f"[{tbl_id}]({tbl_id})",
        ):
            if ref in markdown:
                markdown = markdown.replace(ref, f"\n{content}\n")
                break
    return markdown


def _page_to_text(page, strip_headers_footers: bool, strip_images: bool) -> str:
    """Convert a single Mistral OCR page object to a plain text string.

    - Inlines table content from page.tables (replaces [tbl-N.md] references).
    - Optionally skips page.header and page.footer (already separated by the API).
    - Optionally strips image references (![...](...)  — no text value).
    """
    markdown: str = getattr(page, "markdown", "") or ""

    # Inline table content
    tables = getattr(page, "tables", None) or []
    if tables:
        markdown = _inline_tables(markdown, tables)

    # Strip image refs (![img-N.jpeg](img-N.jpeg)) — carry no text information
    if strip_images:
        markdown = _IMAGE_REF_RE.sub("", markdown)

    # Header / footer are returned as separate strings by the Mistral API.
    # When strip_headers_footers=False, prepend/append them so they are
    # searchable (e.g. for TOC / metadata extraction).
    if not strip_headers_footers:
        header: str = getattr(page, "header", None) or ""
        footer: str = getattr(page, "footer", None) or ""
        parts = []
        if header:
            parts.append(header)
        parts.append(markdown)
        if footer:
            parts.append(footer)
        return "\n".join(parts)

    return markdown


def _pages_to_text(pages: list, strip_headers_footers: bool = True, strip_images: bool = True) -> str:
    """Join all pages into a single string."""
    return "\n".join(
        _page_to_text(page, strip_headers_footers=strip_headers_footers, strip_images=strip_images)
        for page in pages
    )


def _collect_images(pages: list) -> list[dict]:
    """Collect all images from OCR pages.

    Returns a list of {"page_index": int, "id": str, "image_base64": str} dicts.
    Images without base64 data (e.g. referenced but not returned) are skipped.
    """
    images = []
    for page in pages:
        page_images = getattr(page, "images", None) or []
        page_index = getattr(page, "index", 0)
        for img in page_images:
            img_id = getattr(img, "id", None)
            img_b64 = getattr(img, "image_base64", None)
            if img_id and img_b64:
                images.append({"page_index": page_index, "id": img_id, "image_base64": img_b64})
    return images


def _ocr_with_mistral(pdf_bytes: bytes, api_key: str, base_url: str, model: str) -> tuple[list, str]:
    """Call Mistral OCR API. Returns (pages, model_name_used)."""
    b64 = base64.b64encode(pdf_bytes).decode("ascii")
    # 5 minute timeout — VIB PDFs are ~100 pages and OCR can take 60–120s
    client = Mistral(api_key=api_key, server_url=base_url, timeout_ms=300_000)
    response = client.ocr.process(
        model=model,
        document={
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{b64}",
        },
        table_format="markdown",
    )
    return response.pages, response.model


def _ocr_fallback_pymupdf(pdf_bytes: bytes) -> list:
    """Extract text from PDF using pymupdf. Returns list of SimpleNamespace pages."""
    pages = []
    with fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf") as doc:
        for page in doc:
            pages.append(SimpleNamespace(index=page.number, markdown=page.get_text("text") or ""))
    return pages


def extract_pages_as_pdf(pdf_bytes: bytes, start_page: int, end_page: int) -> bytes:
    """Extract a page range from a PDF and return it as new PDF bytes.

    Pages are 1-indexed and inclusive.  Uses pymupdf (fitz).
    """
    with fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf") as doc:
        sub = fitz.open()
        sub.insert_pdf(doc, from_page=start_page - 1, to_page=end_page - 1)
        data = sub.tobytes()
        sub.close()
        return data


def extract_full_pdf_text(
    pdf_bytes: bytes,
    api_key: str,
    base_url: str,
    model: str,
    start_page: int | None = None,
    end_page: int | None = None,
    strip_headers_footers: bool = True,
) -> tuple[str, str, str, list[dict]]:
    """Extract the full text of a VIB PDF (all pages joined).

    If start_page / end_page are given (1-indexed, inclusive), only those pages
    are extracted and sent to OCR — all other pages are ignored.

    strip_headers_footers: when True, page.header and page.footer (returned as
    separate fields by Mistral OCR) are excluded from the joined text.
    Image references are always stripped.

    Returns:
        (full_text, ocr_model, ocr_status) where ocr_status is one of:
          "done"     — Mistral OCR succeeded
          "fallback" — pymupdf used (no api_key or Mistral error)
          "failed"   — both Mistral and pymupdf unavailable
    """
    if start_page is not None and end_page is not None:
        try:
            pdf_bytes = extract_pages_as_pdf(pdf_bytes, start_page, end_page)
            logger.info("VIB OCR: restricted to pages %d–%d", start_page, end_page)
        except Exception as exc:
            logger.warning("Failed to extract page range %d–%d, using full PDF: %s", start_page, end_page, exc)

    if api_key:
        try:
            pages, model_used = _ocr_with_mistral(pdf_bytes, api_key, base_url, model)
            n_tables = sum(len(getattr(p, "tables", None) or []) for p in pages)
            ocr_images = _collect_images(pages)
            logger.info(
                "VIB OCR done: %d pages, %d tables, %d images extracted (strip_headers=%s)",
                len(pages), n_tables, len(ocr_images), strip_headers_footers,
            )
            return _pages_to_text(pages, strip_headers_footers=strip_headers_footers), model_used, "done", ocr_images
        except Exception as exc:
            logger.warning("Mistral OCR failed, falling back to pymupdf: %s", exc, exc_info=True)

    # pymupdf fallback — no separate header/footer/table/image fields
    try:
        pages = _ocr_fallback_pymupdf(pdf_bytes)
    except Exception:
        logger.error("pymupdf not installed and Mistral OCR unavailable — returning empty text")
        return "", "none", "failed", []

    return _pages_to_text(pages, strip_headers_footers=False), "pymupdf", "fallback", []
