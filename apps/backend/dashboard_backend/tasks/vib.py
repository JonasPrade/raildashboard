from __future__ import annotations

import io
import logging
import re

from celery import Task

from dashboard_backend.celery_app import celery_app
from dashboard_backend.crud.vib import save_draft_report
from dashboard_backend.database import Session
from dashboard_backend.models.projects.project import Project
from dashboard_backend.schemas.vib import (
    VibEntryProposed,
    VibParseTaskResult,
    VibPfaEntryProposed,
)
from dashboard_backend.tasks.vib_matching import suggest_projects_for_vib_entry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Section boundary markers in the VIB PDF
# ---------------------------------------------------------------------------

# The rail section starts with "B Schienenwege" and ends before "C Bundesfernstraßen".
# NOTE: these patterns also match table-of-contents entries (". . . . . 43") which
# appear earlier in the document.  Use _find_content_section_boundary() to skip TOC hits.
_SECTION_START_RE = re.compile(r"^\s*B\s+Schienenwege", re.IGNORECASE | re.MULTILINE)
_SECTION_END_RE = re.compile(r"^\s*C\s+Bundesfernstra", re.IGNORECASE | re.MULTILINE)

# TOC entries have spaced dots ". . . . ." followed by a page number; content lines don't.
_TOC_DOT_RE = re.compile(r"\.\s\.")

# Vorhaben heading: "B.4.1.3  ABS Lübeck–Rostock–Stralsund (VDE Nr. 1)"
# Also matches OCR variant "B 4.1.1" (space instead of dot between B and 4).
# Only match 4-level B.4.x.x headings (the actual Vorhaben entries, not section overviews).
# Group 1 = section nr (e.g. "B.4.1.3" or "B 4.1.1"), Group 2 = name (may include right-column artifact)
_VORHABEN_HEADING_RE = re.compile(
    r"^(B[\s.]4\.\d+\.\d+)\s{1,8}(.+)$",
    re.MULTILINE,
)

# TOC entry pattern: "B 4.1.1 Name ... 56" or "B.4.1.8 Name" (multi-line)
_TOC_ENTRY_RE = re.compile(r"^(B[\s.]4\.[123]\.\d+)\s+(.+)", re.MULTILINE)
# Trailing dots (continuous "....." or spaced ". . .") + page number at end of a TOC line
_TOC_PAGE_RE = re.compile(r"\s*\.[\.\s]+(\d+)\s*$")

# Right-column content labels that pdfplumber merges onto the heading line in two-column
# layouts.  Strip everything from this marker onwards to get the clean project name.
# Uses \s+ (single space is enough) because pdfplumber may only insert one space at the
# column boundary.
_HEADING_SUFFIX_RE = re.compile(
    r"\s+(?:Verkehrliche\s+Zielsetzung|Projektkenndaten|"
    r"Noch\s+umzusetzende\s+Maßnahmen|Durchgef[üu]hrte\s+(?:und\s+)?[Gg]eplante\s+Maßnahmen|"
    r"Durchgef[üu]hrte\s+Maßnahmen|Bauaktivit[äa]ten|Teilinbetriebnahmen|Projektstand)"
    r".*$",
    re.IGNORECASE | re.DOTALL,
)

# Category determined by parent section number:
#   B.4.1.x → laufend, B.4.2.x → neu, B.4.3.x → potentiell, other → abgeschlossen
_CATEGORY_MAP = {
    "B.4.1": "laufend",
    "B.4.2": "neu",
    "B.4.3": "potentiell",
}

# Block label patterns (bold headings in the PDF text)
_BLOCK_LABELS: dict[str, re.Pattern] = {
    "verkehrliche_zielsetzung": re.compile(r"Verkehrliche\s+Zielsetzung", re.IGNORECASE),
    "durchgefuehrte_massnahmen": re.compile(
        r"Durchgef[üu]hrte\s+(?:und\s+)?[Gg]eplante\s+Maßnahmen|Durchgef[üu]hrte\s+Maßnahmen",
        re.IGNORECASE,
    ),
    "noch_umzusetzende_massnahmen": re.compile(r"Noch\s+umzusetzende\s+Maßnahmen", re.IGNORECASE),
    "bauaktivitaeten": re.compile(r"Bauaktivit[äa]ten(?:\s*\[\d{4}\])?", re.IGNORECASE),
    "teilinbetriebnahmen": re.compile(r"Teilinbetriebnahmen(?:\s*\[\d{4}\])?", re.IGNORECASE),
    "planungsstand": re.compile(r"Planungsstand", re.IGNORECASE),
    "projektkenndaten": re.compile(r"Projektkenndaten", re.IGNORECASE),
}

_PFA_TABLE_HEADER_RE = re.compile(r"Nr\s*\.\s*PFA.{0,60}[Öö]rtlichkeit", re.IGNORECASE | re.DOTALL)

# Projektkenndaten value extraction
_STRECKLAENGE_RE = re.compile(r"Streckenl[äa]nge.*?(\d[\d,.]*)\s*km", re.IGNORECASE)
_GESCHWINDIGKEIT_RE = re.compile(r"Geschwindigkeit.*?(\d+(?:[/\-–]\d+)?)\s*km/h", re.IGNORECASE)
_GESAMTKOSTEN_RE = re.compile(r"Gesamtkosten.*?(\d[\d,.]*)\s*Mio", re.IGNORECASE)

# Document metadata
_DRUCKSACHE_RE = re.compile(r"Drucksache\s+([\d/]+)", re.IGNORECASE)
_REPORT_DATE_RE = re.compile(r"(\d{2})[.\-/](\d{2})[.\-/](\d{4})")

# Maximum raw_text stored per entry (caps DB storage)
_RAW_TEXT_MAX_CHARS = 8000


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _is_two_column_page(words: list) -> bool:
    """Return True if more than 15% of words start in the right-column zone (x0 > 260 pt)."""
    if not words:
        return False
    right_count = sum(1 for w in words if w["x0"] > 260)
    return (right_count / len(words)) >= 0.15


def _extract_page_text_columns(page: object) -> str:
    """Extract text from a PDF page, auto-detecting single vs. two-column layout.

    For two-column pages: reads left column (x0 <= 260) top-to-bottom, then
    right column top-to-bottom, concatenates.
    For single-column pages: reads all words in top-to-bottom order.
    """
    COL_BOUNDARY = 260.0
    Y_TOLERANCE = 3

    words = page.extract_words()
    if not words:
        return page.extract_text() or ""

    two_col = _is_two_column_page(words)

    left_lines: dict[int, list] = {}
    right_lines: dict[int, list] = {}

    for w in words:
        y_key = round(w["top"] / Y_TOLERANCE)
        if two_col:
            target = left_lines if w["x0"] <= COL_BOUNDARY else right_lines
        else:
            target = left_lines  # single column — all words go to left_lines
        target.setdefault(y_key, []).append(w)

    def _lines_to_text(lines: dict[int, list]) -> str:
        result = []
        for y_key in sorted(lines):
            row = sorted(lines[y_key], key=lambda w: w["x0"])
            result.append(" ".join(w["text"] for w in row))
        return "\n".join(result)

    left_text = _lines_to_text(left_lines)
    right_text = _lines_to_text(right_lines)
    return (left_text + "\n" + right_text) if right_text else left_text


def _find_content_boundary(text: str, pattern: re.Pattern) -> int | None:
    """Return the char position of the first match that is NOT a TOC entry.

    Table-of-contents lines contain spaced dots (". . .") followed by a page
    number.  The actual section headings in the body do not.
    """
    for m in pattern.finditer(text):
        line_end = text.find("\n", m.start())
        if line_end == -1:
            line_end = len(text)
        line = text[m.start():line_end]
        if not _TOC_DOT_RE.search(line):
            return m.start()
    return None


def _parse_float_de(value: str | None) -> float | None:
    """Parse German-formatted float string (comma as decimal separator)."""
    if not value:
        return None
    cleaned = value.replace(".", "").replace(",", ".").strip()
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _determine_category(section: str) -> str:
    """Derive category from section number like 'B.4.1.3'."""
    parts = section.split(".")
    parent = ".".join(parts[:3])
    return _CATEGORY_MAP.get(parent, "abgeschlossen")


def _extract_lfd_nr(section: str) -> str | None:
    """Extract the last numeric component as the lfd_nr within its category."""
    parts = section.split(".")
    return parts[-1] if parts else None


def _parse_toc(full_text: str) -> dict[str, str]:
    """Parse the table of contents to extract canonical project names.

    The TOC contains the authoritative list of all B.4.x.x entries with clean
    project names (free of the two-column layout artefacts present in the body).
    Some entries span multiple lines in the TOC (e.g. B.4.1.8 has cross-
    references on continuation lines); we only use the first-line name.

    Returns: {normalized_section_nr: clean_name}
      e.g. {"B.4.1.1": "Lfd. Vorhaben Nr. 2 – ABS Lübeck/Hagenow Land–Rostock–Stralsund (VDE Nr. 1)"}
    """
    # TOC comes before the content section; find the boundary.
    toc_start_m = re.search(r"B\s+Schienenwege", full_text)
    content_start = _find_content_boundary(full_text, _SECTION_START_RE)
    if toc_start_m is None or content_start is None:
        return {}

    toc_text = full_text[toc_start_m.start():content_start]
    lines = toc_text.split("\n")

    result: dict[str, str] = {}
    for line in lines:
        m = _TOC_ENTRY_RE.match(line)
        if not m:
            continue

        section = m.group(1).replace(" ", ".")
        name_part = m.group(2)

        # Strip trailing dots+page-number if on the same line
        page_m = _TOC_PAGE_RE.search(name_part)
        if page_m:
            name = name_part[:page_m.start()].strip()
        else:
            name = name_part.strip()

        # Fix common OCR space artefact: "L fd." → "Lfd."
        name = re.sub(r"\bL\s+fd\.", "Lfd.", name)
        name = name.strip()

        if name:
            result[section] = name

    return result


# ---------------------------------------------------------------------------
# PFA table parsing
# ---------------------------------------------------------------------------

def _parse_pfa_table(block_text: str) -> list[VibPfaEntryProposed]:
    """Parse the PFA table block into structured rows.

    PDF columns are separated by single spaces (not multiple), so we split on
    the "Entwurfsplanung" status keyword ('abgeschlossen', 'offen',
    'in Überarbeitung') to locate the Örtlichkeit boundary.  The remaining
    date-like tokens are mapped positionally to the remaining columns.
    """
    entries: list[VibPfaEntryProposed] = []
    current_abschnitt: str | None = None

    # "Entwurfsplanung" column always starts with one of these status words
    _entwurfsplanung_re = re.compile(
        r"\b(abgeschlossen|offen|in\s+[ÜU]berarbeitung)\b",
        re.IGNORECASE,
    )
    lines = [ln.strip() for ln in block_text.split("\n") if ln.strip()]
    # Skip table header lines
    data_lines = [
        ln for ln in lines
        if not re.search(
            r"Nr\s*\.\s*PFA|[Öö]rtlichkeit|Entwurfsplanung|Abschluss|Datum\s+PFB|Baubeginn|Inbetriebnahme",
            ln,
            re.IGNORECASE,
        )
    ]

    _abschnitt_re = re.compile(r"^\d+\.\s+(?:Bau|Ausbau)stufe.*$", re.IGNORECASE)
    _pfa_row_re = re.compile(r"^(\d+(?:\.\d+)?)\s+(.+)$")

    for line in data_lines:
        if _abschnitt_re.match(line):
            current_abschnitt = line
            continue

        m = _pfa_row_re.match(line)
        if not m:
            continue

        nr_pfa = m.group(1)
        rest = m.group(2)

        # Split Örtlichkeit from Entwurfsplanung by the first status keyword
        status_match = _entwurfsplanung_re.search(rest)
        if status_match:
            oertlichkeit = rest[:status_match.start()].strip() or None
            after_status = rest[status_match.start():]
            # Collect all remaining tokens after the status word
            tokens = after_status.split()
            entwurfsplanung = tokens[0] if tokens else None
            date_tokens = tokens[1:]
        else:
            # No status found — the entire rest is the location
            oertlichkeit = rest.strip() or None
            entwurfsplanung = None
            date_tokens = []

        entry = VibPfaEntryProposed(
            abschnitt_label=current_abschnitt,
            nr_pfa=nr_pfa,
            oertlichkeit=oertlichkeit,
            entwurfsplanung=entwurfsplanung,
            abschluss_finve=date_tokens[0] if len(date_tokens) > 0 else None,
            datum_pfb=date_tokens[1] if len(date_tokens) > 1 else None,
            baubeginn=date_tokens[2] if len(date_tokens) > 2 else None,
            inbetriebnahme=date_tokens[3] if len(date_tokens) > 3 else None,
        )
        entries.append(entry)

    return entries


# ---------------------------------------------------------------------------
# Sub-block extraction
# ---------------------------------------------------------------------------

def _extract_sub_blocks(block_text: str) -> dict[str, str]:
    """Split a Vorhaben block into named sub-sections.

    Finds the positions of each known block label within the block text and
    extracts the text between consecutive labels.
    """
    label_positions: list[tuple[int, str]] = []

    for label_key, pattern in _BLOCK_LABELS.items():
        m = pattern.search(block_text)
        if m:
            label_positions.append((m.start(), label_key))

    pfa_m = _PFA_TABLE_HEADER_RE.search(block_text)
    if pfa_m:
        label_positions.append((pfa_m.start(), "pfa"))

    label_positions.sort(key=lambda x: x[0])

    result: dict[str, str] = {}
    for idx, (pos, key) in enumerate(label_positions):
        # Content starts after the label line ends
        newline_pos = block_text.find("\n", pos)
        content_start = newline_pos + 1 if newline_pos != -1 else pos
        content_end = (
            label_positions[idx + 1][0] if idx + 1 < len(label_positions) else len(block_text)
        )
        content = block_text[content_start:content_end].strip()
        if content:
            result[key] = content

    return result


# ---------------------------------------------------------------------------
# Core PDF parser
# ---------------------------------------------------------------------------

def _parse_vib_pdf(
    pdf_bytes: bytes,
    year: int,
    all_projects: list | None = None,
    task: "Task | None" = None,
) -> VibParseTaskResult:
    """Parse a VIB PDF and return a structured task result.

    Approach:
    1. Extract text from all pages, accumulate into one string.
    2. Find the "B Schienenwege" → "C Bundesfernstraßen" slice.
    3. Within that slice, detect each Vorhaben heading (B.4.x.x).
    4. For each Vorhaben, split its block into labelled sub-sections.
    5. Run auto-matching against projects.
    """
    import pdfplumber

    all_pages_text: list[str] = []
    drucksache_nr: str | None = None
    report_date_str: str | None = None

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        total_pages = len(pdf.pages)
        logger.info("VIB PDF parse started: %d pages, year=%d", total_pages, year)

        for page_idx, page in enumerate(pdf.pages, start=1):
            if task is not None:
                task.update_state(
                    state="PROGRESS",
                    meta={
                        "current_page": page_idx,
                        "total_pages": total_pages,
                    },
                )
            page_text = _extract_page_text_columns(page)
            all_pages_text.append(page_text)

            # Extract document metadata from first few pages
            if page_idx <= 5:
                if drucksache_nr is None:
                    m_dr = _DRUCKSACHE_RE.search(page_text)
                    if m_dr:
                        drucksache_nr = m_dr.group(1)
                if report_date_str is None:
                    m_date = _REPORT_DATE_RE.search(page_text)
                    if m_date:
                        d, mo, y = m_date.group(1), m_date.group(2), m_date.group(3)
                        report_date_str = f"{y}-{mo}-{d}"

    full_text = "\n".join(all_pages_text)

    # Find rail section boundaries — skip table-of-contents entries (". . . 43")
    rail_start_pos = _find_content_boundary(full_text, _SECTION_START_RE)
    rail_end_pos = _find_content_boundary(full_text, _SECTION_END_RE)

    if rail_start_pos is None:
        logger.warning("VIB: 'B Schienenwege' content section not found — parsing entire document")
        rail_text = full_text
    else:
        rail_end = rail_end_pos if rail_end_pos is not None else len(full_text)
        rail_text = full_text[rail_start_pos:rail_end]
        logger.info(
            "VIB: rail section found at chars %d–%d (%d chars)",
            rail_start_pos, rail_end, rail_end - rail_start_pos,
        )

    # Build TOC name lookup for canonical project names (avoids two-column artefacts).
    toc_names = _parse_toc(full_text)
    logger.info("VIB: parsed %d project names from TOC", len(toc_names))

    # Find all Vorhaben headings within the rail section
    heading_matches = list(_VORHABEN_HEADING_RE.finditer(rail_text))
    logger.info("VIB: found %d Vorhaben headings", len(heading_matches))

    entries: list[VibEntryProposed] = []

    for i, hm in enumerate(heading_matches):
        # Normalize "B 4.1.1" (OCR space artefact) → "B.4.1.1"
        section_nr = hm.group(1).strip().replace(" ", ".")
        extracted_name = hm.group(2).strip()

        block_start = hm.start()
        block_end = (
            heading_matches[i + 1].start() if i + 1 < len(heading_matches) else len(rail_text)
        )
        block_text = rail_text[block_start:block_end]

        category = _determine_category(section_nr)
        lfd_nr = _extract_lfd_nr(section_nr)

        # Use the TOC name as canonical vib_name_raw — it is free of two-column
        # layout artefacts that pdfplumber merges onto the heading line in the body.
        # Fall back to the extracted heading name (with suffix stripping) if not in TOC.
        if section_nr in toc_names:
            name_raw = toc_names[section_nr]
        else:
            name_raw = _HEADING_SUFFIX_RE.sub("", extracted_name).strip()

        sub_blocks = _extract_sub_blocks(block_text)

        # Parse Projektkenndaten
        kenndaten_text = sub_blocks.get("projektkenndaten", "")
        strecklaenge: float | None = None
        gesamtkosten: float | None = None
        geschwindigkeit_str: str | None = None

        if kenndaten_text:
            m_strecke = _STRECKLAENGE_RE.search(kenndaten_text)
            if m_strecke:
                strecklaenge = _parse_float_de(m_strecke.group(1))

            m_kosten = _GESAMTKOSTEN_RE.search(kenndaten_text)
            if m_kosten:
                gesamtkosten = _parse_float_de(m_kosten.group(1))

            m_speed = _GESCHWINDIGKEIT_RE.search(kenndaten_text)
            if m_speed:
                geschwindigkeit_str = m_speed.group(1)

        # Parse PFA table
        pfa_entries: list[VibPfaEntryProposed] = []
        pfa_text = sub_blocks.get("pfa", "")
        if pfa_text:
            pfa_entries = _parse_pfa_table(pfa_text)

        # Auto-match project
        suggested_ids: list[int] = []
        if all_projects:
            suggested_ids = suggest_projects_for_vib_entry(name_raw, all_projects)

        entry = VibEntryProposed(
            vib_section=section_nr,
            vib_lfd_nr=lfd_nr,
            vib_name_raw=name_raw,
            category=category,
            verkehrliche_zielsetzung=sub_blocks.get("verkehrliche_zielsetzung"),
            durchgefuehrte_massnahmen=sub_blocks.get("durchgefuehrte_massnahmen"),
            noch_umzusetzende_massnahmen=sub_blocks.get("noch_umzusetzende_massnahmen"),
            bauaktivitaeten=sub_blocks.get("bauaktivitaeten"),
            teilinbetriebnahmen=sub_blocks.get("teilinbetriebnahmen"),
            raw_text=block_text[:_RAW_TEXT_MAX_CHARS],
            strecklaenge_km=strecklaenge,
            gesamtkosten_mio_eur=gesamtkosten,
            entwurfsgeschwindigkeit=geschwindigkeit_str,
            planungsstand=sub_blocks.get("planungsstand"),
            pfa_entries=pfa_entries,
            project_id=suggested_ids[0] if suggested_ids else None,
            suggested_project_ids=suggested_ids,
        )
        entries.append(entry)

    logger.info("VIB PDF parse complete: %d entries", len(entries))
    return VibParseTaskResult(
        year=year,
        drucksache_nr=drucksache_nr,
        report_date=report_date_str,
        entries=entries,
    )


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@celery_app.task(bind=True)
def parse_vib_pdf(
    self: Task,
    pdf_bytes: bytes,
    year: int,
    pdf_filename: str,
    user_info: dict,
) -> dict:
    """Parse a VIB PDF and return the structured result.

    The full VibParseTaskResult is returned as a dict and stored in the Celery
    result backend (Redis).  The confirm endpoint reads it via the task_id.
    """
    logger.info(
        "parse_vib_pdf started: file=%s year=%d user=%s",
        pdf_filename,
        year,
        user_info.get("username") if user_info else "unknown",
    )
    db = Session()
    try:
        all_projects = db.query(Project).all()
        logger.info("Loaded %d projects for VIB auto-matching", len(all_projects))

        result = _parse_vib_pdf(
            pdf_bytes,
            year,
            all_projects=all_projects,
            task=self,
        )
        logger.info("parse_vib_pdf finished: %d entries", len(result.entries))

        # Persist the raw parse result to the DB immediately so it survives
        # Redis eviction and the user can resume review without re-uploading.
        raw_json = result.model_dump_json()
        save_draft_report(
            db=db,
            task_id=self.request.id,
            year=year,
            raw_result_json=raw_json,
            user=None,  # user object not available in worker context; id stored in user_info
        )
        db.commit()
        logger.info("parse_vib_pdf: raw result saved to vib_draft_report (task_id=%s)", self.request.id)

        return result.model_dump()

    except Exception as exc:
        logger.exception("parse_vib_pdf failed: %s", exc)
        raise
    finally:
        db.close()
