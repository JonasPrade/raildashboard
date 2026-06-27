"""OCR + LLM extraction for the Fulda-Runde importer (#46).

A Fulda-Runde "Kleine Anfrage" PDF is OCR'd (reusing the VIB OCR pipeline) and
the resulting text is handed to the configured LLM, which returns the projects
grouped by Leistungsphase category. When no LLM is configured the extraction
returns no items and the editor enters them manually. Runs synchronously from
the admin endpoint (Kleine Anfragen are short).
"""

from __future__ import annotations

import json
import logging

from dashboard_backend.core.config import settings
from dashboard_backend.tasks.vib_ocr import extract_full_pdf_text

logger = logging.getLogger(__name__)

_ALLOWED_CATEGORIES = {
    "IN_LPH_1_2",
    "IN_LPH_3_4",
    "COMPLETED_LPH_1_2",
    "COMPLETED_LPH_3_4",
}

_SYSTEM_PROMPT = (
    "Du analysierst eine parlamentarische Kleine Anfrage zur 'Fulda-Runde' über den "
    "Planungsstand von Bahnprojekten. Antworte ausschließlich mit einem validen "
    "JSON-Objekt, ohne Erklärungen."
)

_USER_PROMPT_TEMPLATE = """\
--- TEXT ---
{text}
--- ENDE ---

Die Kleine Anfrage listet Projekte nach Leistungsphase (Lph). Ordne jedes genannte
Projekt genau einer Kategorie zu:
- "IN_LPH_1_2": Projekt befindet sich aktuell in Leistungsphase 1–2 (Vorplanung)
- "IN_LPH_3_4": Projekt befindet sich aktuell in Leistungsphase 3–4 (Entwurfs-/Genehmigungsplanung)
- "COMPLETED_LPH_1_2": Projekt hat Lph 1–2 abgeschlossen (bzw. schließt sie dieses Jahr ab)
- "COMPLETED_LPH_3_4": Projekt hat Lph 3–4 abgeschlossen (bzw. schließt sie dieses Jahr ab)

Antworte als JSON:
{{
  "source_label": "<Drucksache-Nummer/Bezeichnung oder null>",
  "document_date": "<YYYY-MM-DD oder null>",
  "items": [
    {{"project_name": "<Projektname>", "category": "<eine der vier Kategorien>"}}
  ]
}}

Nimm nur Projekte auf, die eindeutig einer Kategorie zugeordnet sind. Erfinde nichts.
"""

_MAX_TEXT_CHARS = 30000


def ocr_fulda_pdf(pdf_bytes: bytes) -> tuple[str, str, str]:
    """OCR a Fulda PDF. Returns (full_text, ocr_model, ocr_status)."""
    full_text, ocr_model, ocr_status, _images = extract_full_pdf_text(
        pdf_bytes=pdf_bytes,
        api_key=settings.ocr_api_key,
        base_url=settings.ocr_base_url,
        model=settings.ocr_model,
        strip_headers_footers=settings.ocr_strip_headers_footers,
    )
    return full_text, ocr_model, ocr_status


def normalize_items(raw_items) -> list[dict]:
    """Keep only items with a name and a valid category (upper-cased)."""
    items: list[dict] = []
    if not isinstance(raw_items, list):
        return items
    for entry in raw_items:
        if not isinstance(entry, dict):
            continue
        name = (entry.get("project_name") or "").strip()
        category = (entry.get("category") or "").strip().upper()
        if name and category in _ALLOWED_CATEGORIES:
            items.append({"project_name": name, "category": category})
    return items


def _call_llm(prompt: str) -> dict:
    from openai import OpenAI  # lazy import

    client = OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key or "no-key",
    )
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)


def extract_fulda_announcements(text: str) -> dict:
    """Extract Fulda announcements from OCR text.

    Returns ``{"source_label", "document_date", "items": [...]}`` with validated
    items. Empty items when no LLM is configured or extraction fails.
    """

    empty = {"source_label": None, "document_date": None, "items": []}
    if not settings.llm_base_url or not (text or "").strip():
        return empty

    prompt = _USER_PROMPT_TEMPLATE.format(text=text[:_MAX_TEXT_CHARS])
    try:
        result = _call_llm(prompt)
    except Exception as exc:  # noqa: BLE001 - extraction is best-effort
        logger.warning("Fulda LLM extraction failed: %s", exc)
        return empty

    return {
        "source_label": result.get("source_label") or None,
        "document_date": result.get("document_date") or None,
        "items": normalize_items(result.get("items")),
    }
