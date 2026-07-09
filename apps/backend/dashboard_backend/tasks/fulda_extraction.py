"""OCR + LLM extraction for the Fulda-Runde importer (#46).

A Fulda-Runde "Kleine Anfrage" PDF is OCR'd (reusing the VIB OCR pipeline) and
the resulting text is handed to the configured LLM, which returns the projects
grouped by Leistungsphase category. When no LLM is configured the extraction
returns no items and the editor enters them manually. Runs synchronously from
the admin endpoint (Kleine Anfragen are short).
"""

from __future__ import annotations

import logging

from dashboard_backend.core.config import settings
from dashboard_backend.services.llm import call_llm_json
from dashboard_backend.tasks.vib_ocr import extract_full_pdf_text

logger = logging.getLogger(__name__)

# The Fulda-Runde answer groups projects by Leistungsphase: the question heading
# above each project list says which phase status the list represents. The LLM's
# only job is to assign each list to one of these five categories (by the heading,
# not by guessing a question number). Budget-only questions carry no projects.
FULDA_CATEGORY_LABELS: dict[str, str] = {
    "IN_LPH_1_2": (
        "Projekte, die sich aktuell in Leistungsphase 1–2 (Vorplanung) befinden "
        "oder 2026 neu in Lph 1–2 aufgenommen werden"
    ),
    "COMPLETED_LPH_1_2": (
        "Projekte, deren Leistungsphase 1–2 abgeschlossen ist/wird, ohne dass "
        "bereits Lph 3–4 aufgenommen wird"
    ),
    "IN_LPH_3_4": (
        "Projekte, die sich aktuell in Leistungsphase 3–4 (Entwurfs-/"
        "Genehmigungsplanung) befinden oder nach Abschluss Lph 1–2 neu in Lph 3–4 "
        "aufgenommen werden"
    ),
    "COMPLETED_LPH_3_4": (
        "Projekte, deren Leistungsphase 3–4 abgeschlossen ist/wird"
    ),
    "HAS_BAUFINVE": (
        "Projekte mit bestehender oder neu erteilter BAUfinanzierungsvereinbarung "
        "(Finanzierung des Baus / Lph 5–9), NICHT die Sammelfinanzierungsvereinbarung "
        "der Planungsphasen Lph 1–4. Nur verwenden, wenn die Frage ausdrücklich eine "
        "Liste von Projekten mit Baufinanzierungsvereinbarung nennt"
    ),
}

FULDA_CATEGORIES: set[str] = set(FULDA_CATEGORY_LABELS)

_SYSTEM_PROMPT = (
    "Du analysierst die Antwort der Bundesregierung auf eine Kleine Anfrage zur "
    "'Fulda-Runde' über den Planungsstand von Bahnprojekten. Antworte ausschließlich "
    "mit einem validen JSON-Objekt, ohne Erklärungen."
)

_CATEGORY_CATALOG = "\n".join(
    f"  - {key}: {label}" for key, label in FULDA_CATEGORY_LABELS.items()
)

_USER_PROMPT_TEMPLATE = """\
--- TEXT ---
{text}
--- ENDE ---

Dies ist die Antwort der Bundesregierung. Jede nummerierte Frage wird mit einer
Tabelle von Projekten beantwortet (Spalten 'Projekt' und 'Abschnitt'). Die
**Überschrift / der Fragetext über jeder Tabelle** sagt, in welcher
Leistungsphase die aufgelisteten Projekte stehen. Ordne jede Projektzeile genau
einer dieser Kategorien zu — anhand der Frage über der Tabelle, nicht nach
eigenem Ermessen:
{categories}

**Jede Tabelle/Aufzählung gehört zu GENAU EINER Kategorie** (der ihrer
Frage-Überschrift). Gib dieselbe Projektzeile niemals unter mehreren Kategorien
aus. Manche Fragen werden gar nicht mit einer Projektliste beantwortet (z. B.
Verweis auf eine Haushaltsanlage, „bleibt abzuwarten", oder „keine Aufzählung
möglich") — für solche Fragen gibst du KEINE Einträge aus.

Antworte als JSON:
{{
  "source_label": "<Drucksache-Nummer oder null>",
  "document_date": "<YYYY-MM-DD oder null>",
  "items": [
    {{"category": "<einer der obigen Schlüssel>", "project_name": "<Spalte 'Projekt'>", "abschnitt": "<Spalte 'Abschnitt'>"}}
  ]
}}

**Übernimm `project_name` und `abschnitt` exakt und wortwörtlich** aus der
Tabelle — KEINE Umformulierung, Übersetzung, Abkürzung, Ergänzung oder
Vereinheitlichung (Kürzel wie ABS/NBS/VDE und Bindestriche genau so lassen).

**`abschnitt` ist Pflicht für jede Zeile:**
- In zweispaltigen Tabellen ist es die Spalte 'Abschnitt'.
- In Aufzählungen ohne Tabelle (z. B. „Großknoten Frankfurt: Kurve Mainaschaff"
  oder „ABS Berlin – Dresden: 2. BS") ist `project_name` der Teil **vor** dem
  Doppelpunkt und `abschnitt` der Teil **danach**.
- Steht kein eigener Abschnitt da, setze `abschnitt` auf "Gesamtstrecke".

Gib jede Projektzeile jeder Antwort-Tabelle/Aufzählung aus und setze `category`
auf den passenden Schlüssel. Tabellen mit reinen Finanzzahlen (z. B.
Mittelbedarf) lässt du weg. Erfinde nichts.
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
    """Validate LLM rows into ``{project_name, abschnitt, category}`` dicts.

    The LLM assigns each project list to one of ``FULDA_CATEGORIES`` by the
    question heading above it and gives the Abschnitt per row (the second table
    column, or the part after the colon in a bullet list). Rows with no project
    name or an unknown category are dropped, and duplicate (name, abschnitt,
    category) triples are de-duplicated — but the same project with different
    Abschnitte stays as separate rows (each Abschnitt is its own subproject).
    """
    items: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    if not isinstance(raw_items, list):
        return items
    for entry in raw_items:
        if not isinstance(entry, dict):
            continue
        name = (entry.get("project_name") or "").strip()
        category = (entry.get("category") or "").strip().upper()
        if not name or category not in FULDA_CATEGORIES:
            continue
        abschnitt = (entry.get("abschnitt") or "").strip() or None
        key = (name.lower(), (abschnitt or "").lower(), category)
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {"project_name": name, "abschnitt": abschnitt, "category": category}
        )
    return items


def extract_fulda_announcements(text: str) -> dict:
    """Extract Fulda announcements from OCR text.

    Returns ``{"source_label", "document_date", "items": [...]}`` with validated
    items. Empty items when no LLM is configured or extraction fails.
    """

    empty = {"source_label": None, "document_date": None, "items": []}
    if not settings.llm_base_url or not (text or "").strip():
        return empty

    prompt = _USER_PROMPT_TEMPLATE.format(
        text=text[:_MAX_TEXT_CHARS], categories=_CATEGORY_CATALOG
    )
    try:
        result = call_llm_json(_SYSTEM_PROMPT, prompt)
    except Exception as exc:  # noqa: BLE001 - extraction is best-effort
        logger.warning("Fulda LLM extraction failed: %s", exc)
        return empty

    return {
        "source_label": result.get("source_label") or None,
        "document_date": result.get("document_date") or None,
        "items": normalize_items(result.get("items")),
    }
