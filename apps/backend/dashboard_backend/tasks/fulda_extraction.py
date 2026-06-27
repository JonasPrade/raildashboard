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

# The Fulda-Runde answer is structured by numbered question; the question number
# deterministically fixes the Leistungsphase category. (Questions 12–14 are pure
# budget figures and carry no projects.)
FULDA_QUESTION_CATEGORY: dict[int, str] = {
    1: "IN_LPH_1_2",        # aktuell in Sammel-FinVe Lph 1/2
    2: "IN_LPH_1_2",        # 2026 neu in Lph 1/2 aufgenommen
    3: "COMPLETED_LPH_1_2",  # Lph 1/2 wird 2026 abgeschlossen
    4: "IN_LPH_3_4",        # nach Abschluss Lph 1/2 Aufnahme in Lph 3/4
    5: "COMPLETED_LPH_1_2",  # Lph 1/2 abgeschlossen, keine Aufnahme in Lph 3/4
    6: "IN_LPH_3_4",        # aktuell in Lph 3/4
    7: "COMPLETED_LPH_3_4",  # Lph 3/4 wird 2026 abgeschlossen
    8: "HAS_BAUFINVE",      # hat Baufinanzierungsvereinbarung
    9: "HAS_BAUFINVE",      # erhält 2026 Baufinanzierungsvereinbarung
    10: "COMPLETED_LPH_3_4",  # Lph 3/4 abgeschlossen, keine BauFinVe
    11: "HAS_BAUFINVE",     # Ausschreibung Lph 5–9 in Vorbereitung
}

_SYSTEM_PROMPT = (
    "Du analysierst die Antwort der Bundesregierung auf eine Kleine Anfrage zur "
    "'Fulda-Runde' über den Planungsstand von Bahnprojekten. Antworte ausschließlich "
    "mit einem validen JSON-Objekt, ohne Erklärungen."
)

_USER_PROMPT_TEMPLATE = """\
--- TEXT ---
{text}
--- ENDE ---

Dies ist die Antwort der Bundesregierung. Jede nummerierte Frage wird mit einer
Tabelle von Projekten beantwortet (Spalten 'Projekt' und 'Abschnitt'). Die
**Fragenummer** bestimmt die Kategorie — ordne daher jede Projektzeile der Nummer
der Frage zu, unter der ihre Tabelle steht (nicht nach eigenem Ermessen).

Antworte als JSON:
{{
  "source_label": "<Drucksache-Nummer oder null>",
  "document_date": "<YYYY-MM-DD oder null>",
  "items": [
    {{"question": <Fragenummer als ganze Zahl>, "project_name": "<Spalte 'Projekt'>", "abschnitt": "<Spalte 'Abschnitt' oder null>"}}
  ]
}}

Gib jede Projektzeile jeder Antwort-Tabelle aus. Lass die Fragen 12, 13 und 14
(reine Finanzzahlen) weg. Erfinde nichts.
"""

_MAX_TEXT_CHARS = 60000


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
    """Map LLM rows (question + project_name) to ``{project_name, category}``.

    The category comes from the question number (``FULDA_QUESTION_CATEGORY``), not
    from the model's own judgement. Rows for budget-only questions (12–14) or with
    no project name are dropped, and duplicate (name, category) pairs — the same
    project listed for several Abschnitte under one question — are de-duplicated.
    """
    items: list[dict] = []
    seen: set[tuple[str, str]] = set()
    if not isinstance(raw_items, list):
        return items
    for entry in raw_items:
        if not isinstance(entry, dict):
            continue
        name = (entry.get("project_name") or "").strip()
        try:
            question = int(entry.get("question"))
        except (TypeError, ValueError):
            continue
        category = FULDA_QUESTION_CATEGORY.get(question)
        if not name or category is None:
            continue
        key = (name.lower(), category)
        if key in seen:
            continue
        seen.add(key)
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
