"""Haushalt importer (Anlage VWIB, Teil B) — PDF table → Finve/Budget rows.

Three stages, following ``docs/features/feature-pdf-import-unification.md``:

  1. Textgewinnung — pdfplumber reads the table structure and the page text.
     The shared stage 1 (``services.document_ocr``) can be switched on with
     ``HAUSHALT_OCR_ENABLED`` to store its markdown with the run as well; the
     table values always come from pdfplumber.
  2. Segmentierung — Teil B holds several tables (Bedarfsplanmaßnahmen,
     Lärmsanierung, ERTMS, …); only the Bedarfsplan table carries FinVe rows,
     so the others are detected and skipped instead of bleeding into the last
     row of the first one.
  3. Semantik — the column layout is mapped onto the canonical schema once per
     document (``haushalt_columns``); every value is then transferred
     deterministically through that map.  No number passes through a model.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field as dataclass_field

from celery import Task

from dashboard_backend.celery_app import celery_app

logger = logging.getLogger(__name__)
from dashboard_backend.crud.haushalt_import import (
    get_or_create_haushalt_titel,
    save_parse_result,
)
from dashboard_backend.database import Session
from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.project import Project
from dashboard_backend.tasks.finve_matching import suggest_projects_for_finve, suggest_projects_for_sv_erlaeuterung, suggest_per_erlaeuterung_project
from dashboard_backend.services.document_ocr import extract_document_text
from dashboard_backend.tasks.haushalt_columns import (
    ColumnMap,
    is_header_row,
    resolve_column_map,
)
from dashboard_backend.schemas.haushalt_import import (
    HaushaltsParseResultSchema,
    HaushaltsParseTaskResult,
    ProposedBudget,
    ProposedFinve,
    TableSectionSchema,
    TitelEntryProposed,
)

# ---------------------------------------------------------------------------
# Table sections — Teil B is several tables in one PDF
# ---------------------------------------------------------------------------

# Page caption, e.g. "Tabelle 1 - Bedarfsplanmaßnahmen"
_TABLE_CAPTION_RE = re.compile(r"^[ \t]*Tabelle\s+(\d+)\s*[-–—]\s*(.+?)\s*$", re.MULTILINE)

# Closing row of every table — a totals line, not a FinVe
_TABLE_TOTALS_RE = re.compile(r"^\s*(TABELLENSUMMEN|SUMME)\b", re.IGNORECASE)


@dataclass
class TableSection:
    """One "Tabelle N – …" of Teil B and the pages it spans (1-indexed)."""

    number: int | None
    title: str
    pages: list[int] = dataclass_field(default_factory=list)
    imported: bool = False


def _detect_table_sections(page_texts: list[str]) -> list[TableSection]:
    """Group the PDF's pages by the "Tabelle N – …" caption they carry.

    A page without a caption belongs to the last captioned section (tables run
    over many pages, the caption repeats but may be missed on a page).  A PDF
    with no caption at all yields a single unnumbered section over all pages —
    the pre-2027 behaviour of treating the whole document as one table.
    """
    sections: list[TableSection] = []
    for page_no, text in enumerate(page_texts, start=1):
        match = _TABLE_CAPTION_RE.search(text or "")
        if match:
            number, title = int(match.group(1)), match.group(2).strip()
            if not sections or sections[-1].number != number:
                sections.append(TableSection(number=number, title=title))
        elif not sections:
            sections.append(TableSection(number=None, title=""))
        sections[-1].pages.append(page_no)
    return sections


def _select_import_section(sections: list[TableSection]) -> TableSection | None:
    """The one table this importer reads: the Bedarfsplan table (Tabelle 1).

    The other tables of Teil B (Lärmsanierung, ERTMS, Kleine und Mittlere
    Maßnahmen, InvKG) list positions without a FinVe number and do not map onto
    Finve/Budget rows.  Marks every section carrying the chosen table number as
    imported — a missed caption in the middle of the table would otherwise
    split it in two — and returns the first of them.
    """
    numbered = [s for s in sections if s.number is not None]
    chosen = min(numbered, key=lambda s: s.number) if numbered else (sections[0] if sections else None)
    if chosen is None:
        return None
    for section in sections:
        if section.number == chosen.number:
            section.imported = True
    return chosen


def _is_table_totals_row(name_cell: str | None) -> bool:
    """True for the "TABELLENSUMMEN" row that closes a table."""
    return bool(name_cell) and bool(_TABLE_TOTALS_RE.match(name_cell.strip()))


# ---------------------------------------------------------------------------
# Column access — every value goes through the document's ColumnMap
# ---------------------------------------------------------------------------

def _cell_of(cells: list, cmap: ColumnMap, field_name: str) -> str | None:
    """The cell of ``field_name`` in this row, or None when unmapped/empty."""
    idx = cmap.index(field_name)
    if idx is None:
        return None
    return _cell(cells, idx)


def _parse_int(value: str | None) -> int | None:
    """Parse a string like "1.234" or "1234" to int; return None on failure."""
    if not value:
        return None
    cleaned = value.replace(".", "").replace(",", "").replace(" ", "").strip()
    try:
        return int(cleaned)
    except (ValueError, TypeError):
        return None


def _parse_float(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = value.replace(",", ".").replace("%", "").strip()
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _cell(row: list, idx: int) -> str | None:
    """Safe index into a row list."""
    if idx < len(row) and row[idx] is not None:
        return str(row[idx]).strip()
    return None


def _split_multiline(value: str | None) -> list[str]:
    """Split a cell value by newline, dropping empty/whitespace-only lines."""
    if not value:
        return []
    return [line.strip() for line in value.split("\n") if line.strip()]


def _first_line(value: str | None) -> str | None:
    """Return only the first (non-empty) line of a cell value."""
    lines = _split_multiline(value)
    return lines[0] if lines else None


def _nth_line(value: str | None, n: int) -> str | None:
    """Return the n-th non-empty line (0-indexed) of a cell value, or None."""
    lines = _split_multiline(value)
    return lines[n] if n < len(lines) else None


def _titel_numeric_fields(cells: list, cmap: ColumnMap, line_idx: int) -> dict:
    """The seven numeric TitelEntryProposed fields from the standard columns.

    ``line_idx`` selects the line inside each multi-line cell (0 = first line).
    Which column holds which field comes from the document's ColumnMap.
    """
    return {
        "cost_estimate_last_year": _parse_int(_nth_line(_cell_of(cells, cmap, "cost_last_year"), line_idx)),
        "cost_estimate_aktuell": _parse_int(_nth_line(_cell_of(cells, cmap, "cost_actual"), line_idx)),
        "verausgabt_bis": _parse_int(_nth_line(_cell_of(cells, cmap, "spent_two_years_previous"), line_idx)),
        "bewilligt": _parse_int(_nth_line(_cell_of(cells, cmap, "allowed_previous_year"), line_idx)),
        "ausgabereste_transferred": _parse_int(_nth_line(_cell_of(cells, cmap, "ausgabereste"), line_idx)),
        "veranschlagt": _parse_int(_nth_line(_cell_of(cells, cmap, "year_planned"), line_idx)),
        "vorhalten_future": _parse_int(_nth_line(_cell_of(cells, cmap, "next_years"), line_idx)),
    }


_KAP_TITEL_RE = re.compile(r"Kap\.\s*(\d+)[^,\n]*(?:,\s*|\s+)Titel\s+([\d ]+)", re.IGNORECASE)


_BHO_NOTE_RE = re.compile(
    r"\nUnterlagen\s+entsprechend.*",
    re.IGNORECASE | re.DOTALL,
)

# Section header that appears in the name cell of the first Sammel-FinVe on a page
_SAMMELVEREINBARUNGEN_HEADER_RE = re.compile(r"^SAMMELVEREINBARUNGEN\s*\n?", re.IGNORECASE)

# En-dash / hyphen variants used as bullet characters in the PDF
_BULLET_CHARS = "\u2010\u2011\u2012\u2013\u2014-"


def _is_erlaeuterung_row(cells: list, cmap: ColumnMap) -> bool:
    """True if the row is an Erläuterung block following a FinVe entry."""
    name_cell = _cell_of(cells, cmap, "name") or ""
    return name_cell.strip().lower().startswith("erläuterung:")


def _is_erlaeuterung_continuation(cells: list, cmap: ColumnMap) -> bool:
    """True if the row looks like a continuation of an Erläuterung block.

    When a long Erläuterung spans multiple PDF pages, pdfplumber produces
    additional table rows for each page.  These lack the "Erläuterung:"
    prefix but start (at least one line) with a bullet character.
    """
    name_cell = _cell_of(cells, cmap, "name") or ""
    # At least one non-empty line must start with a bullet char
    return any(
        line.strip() and line.strip()[0] in _BULLET_CHARS
        for line in name_cell.split("\n")
    )


def _extract_erlaeuterung_projects(erlaeuterung_cell: str) -> list[str]:
    """Extract bullet-listed project names from an Erläuterung cell.

    Lines starting with a dash/en-dash character are treated as list entries.
    Continuation lines (no leading dash) are joined to the previous entry.
    Returns a list of individual project name strings; empty if no bullet list.
    """
    text = re.sub(r"^Erläuterung:\s*\n?", "", erlaeuterung_cell, flags=re.IGNORECASE)
    lines = text.split("\n")

    projects: list[str] = []
    current: list[str] | None = None  # None = not inside a bullet list yet

    for line in lines:
        stripped = line.strip()
        if stripped and stripped[0] in _BULLET_CHARS:
            if current is not None:
                joined = " ".join(current).strip()
                if joined:
                    projects.append(joined)
            remainder = stripped[1:].strip()
            current = [remainder] if remainder else []
        elif current is not None and stripped:
            current.append(stripped)

    if current:
        joined = " ".join(current).strip()
        if joined:
            projects.append(joined)

    return [p for p in projects if len(p) > 3]

_SV_NAME_RE = re.compile(r"\bSV\b|Sammelfinanzierungsvereinbarung", re.IGNORECASE)

# Matches raw-text lines like "YYY 763 SV Lph. 1/2 A 2012 4.000 ..."
# Group 1 = finve_nr, Group 2 = name (stops before the 4-digit starting year)
_YYY_RAW_RE = re.compile(
    r"^YYY\s+(\d+)\s+(.+?)\s+20\d\d\b",
    re.MULTILINE,
)


def _is_sammel_finve(name: str) -> bool:
    return bool(_SV_NAME_RE.search(name))


def _build_sv_raw_lookup(page_text: str) -> dict[str, int]:
    """Scan raw page text for YYY lines and return name_lower → finve_nr mapping.

    Used to recover FinVe numbers for SV rows that lost their col-0 identifier
    at a PDF page break.
    """
    lookup: dict[str, int] = {}
    for m in _YYY_RAW_RE.finditer(page_text):
        finve_nr = int(m.group(1))
        name = m.group(2).strip()
        # Strip section header prefix that may appear in raw text
        name = _SAMMELVEREINBARUNGEN_HEADER_RE.sub("", name).strip()
        lookup[name.lower()] = finve_nr
    return lookup


def _extract_project_name(name_cell: str | None) -> str:
    """Extract the full project name from the name column cell.

    The name column may contain the project name on multiple lines followed by
    'davon:' and Kap./Titel sub-entries.  We take everything before 'davon:'.
    Parenthetical BHO notes ("Unterlagen entsprechend § 24 BHO...") are stripped.
    Multiple name lines are joined with a single space.
    """
    if not name_cell:
        return ""
    # Strip the "SAMMELVEREINBARUNGEN" section header that appears on the first SV entry
    name_cell = _SAMMELVEREINBARUNGEN_HEADER_RE.sub("", name_cell)
    davon_match = re.search(r"\ndavon\s*:", name_cell, re.IGNORECASE)
    name_part = name_cell[: davon_match.start()] if davon_match else name_cell
    # Strip BHO/planning-status notes that may appear between name and 'davon:'
    name_part = _BHO_NOTE_RE.sub("", name_part)
    return " ".join(line.strip() for line in name_part.split("\n") if line.strip())


def _extract_inline_titel_entries(cells: list, cmap: ColumnMap) -> list["TitelEntryProposed"]:
    """Extract Kap./Titel sub-entries embedded in a 2026+ main FinVe row.

    In the 2026 PDF format pdfplumber merges sub-entries into multi-line cells:
      - Col 3 (name): "Project name\\ndavon:\\nKap. 1202, Titel 891 01\\n..."
      - Numeric cols:  "project_total\\nkap1_value\\nkap2_value\\n..."
    Line 0 of each numeric column is the project total (already captured in
    proposed_budget). Lines 1..n correspond to the Kap. entries in the name col.
    """
    name_cell = _cell_of(cells, cmap, "name") or ""
    davon_match = re.search(r"davon\s*:", name_cell, re.IGNORECASE)
    if not davon_match:
        return []

    kap_entries: list[dict] = []
    for line in name_cell[davon_match.end():].split("\n"):
        m = _KAP_TITEL_RE.search(line)
        if m:
            kap_entries.append(
                {"kapitel": m.group(1).strip(), "titel_nr": m.group(2).strip()}
            )

    if not kap_entries:
        return []

    result = []
    for i, kap in enumerate(kap_entries):
        idx = i + 1  # 0 = project total; 1..n = per-Kap values
        result.append(
            TitelEntryProposed(
                titel_key=kap["titel_nr"].replace(" ", "_"),
                kapitel=kap["kapitel"],
                titel_nr=kap["titel_nr"],
                label=f"Kap. {kap['kapitel']}, Titel {kap['titel_nr']}",
                is_nachrichtlich=False,
                **_titel_numeric_fields(cells, cmap, idx),
            )
        )
    return result


def _extract_nachrichtlich_entries(cells: list, cmap: ColumnMap) -> list["TitelEntryProposed"]:
    """Extract individual nachrichtlich entries from a nachrichtlich pdfplumber row.

    In 2026+ PDFs a single row may contain multiple stacked entries:
      - Col 3: "nachrichtlich: Beteiligung Dritter\\nnachrichtlich: Eigenmittel...\\n..."
      - Numeric cols: "value_entry0\\nvalue_entry1\\n..."
    Each label line corresponds to the same-indexed line in the numeric columns.
    """
    label_cell = _cell_of(cells, cmap, "name") or ""

    labels = [
        line.strip()
        for line in label_cell.split("\n")
        if line.strip().lower().startswith("nachrichtlich:")
    ]
    if not labels:
        labels = [label_cell.strip()] if label_cell.strip() else []

    result = []
    for i, label in enumerate(labels):
        result.append(
            TitelEntryProposed(
                titel_key=label[:50],
                kapitel="",
                titel_nr="",
                label=label,
                is_nachrichtlich=True,
                **_titel_numeric_fields(cells, cmap, i),
            )
        )
    return result


def _parse_combined_id_cell(cell: str | None) -> tuple[str | None, int | None, str | None]:
    """Parse the first column which may combine lfd_nr, finve and bedarfsplan.

    The 2026+ format merges the first three columns into one cell, e.g.:
      "B0080 275 N19"  or  "B0121 5100 N 07"

    Sammel-FinVe rows use a YYY prefix instead of B<digits>, e.g.:
      "YYY 315"  or  "YYY 740 N 38"

    Returns (lfd_nr, finve_nr, bedarfsplan_number).
    For older PDFs where only lfd_nr is in col 0, returns (lfd_nr, None, None).
    """
    if not cell:
        return None, None, None
    cell = cell.strip()
    # Combined format: "B<digits> <finve_int> <bedarfsplan>"  or  "YYY <finve_int> <bedarfsplan>"
    m = re.match(r"^(B\d+|YYY)\s+(\d+)\s+(.+)$", cell)
    if m:
        lfd_nr = m.group(1)
        try:
            finve_nr = int(m.group(2))
        except ValueError:
            finve_nr = None
        # A bare dash (‐ or -) in the bedarfsplan position means no bedarfsplan
        bp = m.group(3).strip()
        bedarfsplan = None if bp in ("-", "\u2010", "\u2011", "\u2012", "\u2013", "\u2014") else bp
        return lfd_nr, finve_nr, bedarfsplan
    # Old format: just the lfd_nr (e.g. "B0080")
    if re.match(r"^B\d+$", cell):
        return cell, None, None
    # YYY with finve only (no bedarfsplan): "YYY 315"
    m_yyy = re.match(r"^(YYY)\s+(\d+)$", cell)
    if m_yyy:
        try:
            finve_nr = int(m_yyy.group(2))
        except ValueError:
            finve_nr = None
        return m_yyy.group(1), finve_nr, None
    # Combined without finve_nr: "B0134 L 06" (lfd_nr + bedarfsplan only, no FinVe assigned yet)
    m2 = re.match(r"^(B\d+)\s+(.+)$", cell)
    if m2:
        return m2.group(1), None, m2.group(2).strip()
    return None, None, None


def _is_titel_row(cells: list) -> bool:
    """True if the row is a Haushaltstitel sub-row (contains 'Kap.' and 'Titel')."""
    joined = " ".join(str(c) for c in cells if c)
    return "Kap." in joined and "Titel" in joined


def _is_nachrichtlich_row(cells: list) -> bool:
    joined = " ".join(str(c) for c in cells if c)
    return "nachrichtlich:" in joined.lower()


def _build_titel_entry(cells: list, cmap: ColumnMap) -> TitelEntryProposed:
    """Build a Titel entry for a separate old-format Kap./Titel sub-row."""
    joined = " ".join(str(c) for c in cells if c)
    m_key = re.search(r"Titel\s+(\d+)\s+(\d+)", joined)
    titel_key = f"{m_key.group(1)}_{m_key.group(2)}" if m_key else joined[:50]
    m_kap = re.search(r"Kap\.\s*(\d+)", joined)
    kapitel = m_kap.group(1) if m_kap else ""
    m_tnr = re.search(r"Titel\s+([\d ]+)", joined)
    titel_nr = m_tnr.group(1).strip() if m_tnr else ""
    label = _cell_of(cells, cmap, "name") or joined[:200]
    return TitelEntryProposed(
        titel_key=titel_key,
        kapitel=kapitel,
        titel_nr=titel_nr,
        label=label,
        is_nachrichtlich=False,
        **_titel_numeric_fields(cells, cmap, 0),
    )


def _build_proposed(
    cells: list,
    cmap: ColumnMap,
    year: int,
    finve_nr: int,
    lfd_nr: str | None,
    bedarfsplan_nr: str | None,
    name: str,
    is_sv: bool,
) -> tuple[ProposedFinve, ProposedBudget]:
    """Build the ProposedFinve/ProposedBudget pair for a main FinVe row.

    Used for regular rows and for orphaned-SV recovery — the two callers only
    differ in how name/lfd_nr/bedarfsplan were determined.
    """
    proposed_finve = ProposedFinve(
        id=finve_nr,
        name=name,
        starting_year=_parse_int(_cell_of(cells, cmap, "starting_year")),
        cost_estimate_original=_parse_int(_first_line(_cell_of(cells, cmap, "cost_original"))),
        is_sammel_finve=is_sv,
    )
    proposed_budget = ProposedBudget(
        budget_year=year,
        lfd_nr=lfd_nr,
        fin_ve=finve_nr,
        bedarfsplan_number=bedarfsplan_nr,
        cost_estimate_original=_parse_int(_first_line(_cell_of(cells, cmap, "cost_original"))),
        cost_estimate_last_year=_parse_int(_first_line(_cell_of(cells, cmap, "cost_last_year"))),
        cost_estimate_actual=_parse_int(_first_line(_cell_of(cells, cmap, "cost_actual"))),
        delta_previous_year=_parse_int(_first_line(_cell_of(cells, cmap, "delta_abs"))),
        delta_previous_year_relativ=_parse_float(_first_line(_cell_of(cells, cmap, "delta_rel"))),
        delta_previous_year_reasons=_first_line(_cell_of(cells, cmap, "delta_reasons")),
        spent_two_years_previous=_parse_int(_first_line(_cell_of(cells, cmap, "spent_two_years_previous"))),
        allowed_previous_year=_parse_int(_first_line(_cell_of(cells, cmap, "allowed_previous_year"))),
        spending_residues=_parse_int(_first_line(_cell_of(cells, cmap, "ausgabereste"))),
        year_planned=_parse_int(_first_line(_cell_of(cells, cmap, "year_planned"))),
        next_years=_parse_int(_first_line(_cell_of(cells, cmap, "next_years"))),
        sammel_finve=is_sv,
    )
    return proposed_finve, proposed_budget


def _refresh_sv_suggestions(
    row: HaushaltsParseResultSchema,
    finve_projects: dict[int, list[int]] | None,
    all_projects: list | None,
) -> None:
    """Recompute per-Erläuterung and whole-SV suggestions after new sub-lines.

    Keeps existing project links: the SV-level suggestion only pre-fills
    ``project_ids`` when the FinVe has no linked projects yet.
    """
    if not all_projects:
        return
    row.erlaeuterung_suggestions = suggest_per_erlaeuterung_project(
        row.erlaeuterung_projects, all_projects
    )
    if not (finve_projects or {}).get(row.finve_number):
        sv_suggestions = suggest_projects_for_sv_erlaeuterung(
            row.erlaeuterung_projects, all_projects
        )
        row.suggested_project_ids = sv_suggestions
        row.project_ids = sv_suggestions


@dataclass
class DocumentText:
    """The document text a parse run worked from, for persistence and review."""

    text: str = ""
    model: str = "pdfplumber"
    status: str = "done"


@dataclass
class ExtractedPage:
    """One PDF page after stage 1: its text and the table rows pdfplumber found."""

    number: int  # 1-indexed
    text: str = ""
    rows: list[list] = dataclass_field(default_factory=list)


def _extract_pages(pdf_bytes: bytes, task: Task | None = None) -> list[ExtractedPage]:
    """Stage 1 for the Haushalt: pdfplumber text + table rows, page by page."""
    import pdfplumber

    pages: list[ExtractedPage] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        total_pages = len(pdf.pages)
        for page_idx, page in enumerate(pdf.pages, start=1):
            logger.info("Collecting page %d/%d", page_idx, total_pages)
            if task is not None:
                task.update_state(
                    state="PROGRESS",
                    meta={
                        "current_page": page_idx,
                        "total_pages": total_pages,
                        "rows_found": 0,
                    },
                )
            pages.append(
                ExtractedPage(
                    number=page_idx,
                    text=page.extract_text() or "",
                    rows=[row for row in (page.extract_table() or []) if row],
                )
            )
    return pages


def _parse_pdf(
    pdf_bytes: bytes,
    year: int,
    known_finve_ids: set[int],
    finve_projects: dict[int, list[int]] | None = None,
    all_projects: list | None = None,
    task: Task | None = None,
) -> tuple[HaushaltsParseTaskResult, DocumentText]:
    """Parse a Haushalt PDF into a task result plus the text it worked from."""
    pages = _extract_pages(pdf_bytes, task=task)
    result = _parse_extracted_pages(
        pages,
        year,
        known_finve_ids,
        finve_projects=finve_projects,
        all_projects=all_projects,
    )
    return result, _document_text(pdf_bytes, [page.text for page in pages])


def _parse_extracted_pages(
    pages: list[ExtractedPage],
    year: int,
    known_finve_ids: set[int],
    finve_projects: dict[int, list[int]] | None = None,
    all_projects: list | None = None,
) -> HaushaltsParseTaskResult:
    """Stages 2 and 3: segment the document, map the columns, transfer the values.

    Split out from :func:`_parse_pdf` so the whole parse can be exercised on
    recorded pdfplumber output without carrying a multi-megabyte PDF fixture.
    """
    rows: list[HaushaltsParseResultSchema] = []
    unmatched_rows: list[dict] = []

    current_row: HaushaltsParseResultSchema | None = None

    total_pages = len(pages)
    logger.info("Starting PDF parse: %d pages, year=%d", total_pages, year)

    # Stage 2: the page texts carry the "Tabelle N – …" captions that
    # separate the Bedarfsplan table from the rest of Teil B, and the raw
    # lines the SV page-break recovery scans.
    page_texts: list[str] = [page.text for page in pages]

    sections = _detect_table_sections(page_texts)
    selected = _select_import_section(sections)
    import_pages = {page for section in sections if section.imported for page in section.pages}
    if not import_pages:
        import_pages = set(range(1, total_pages + 1))
    logger.info(
        "Teil B sections: %s — importing %s",
        ", ".join(
            f"Tabelle {s.number or '?'} '{s.title}' (S. {s.pages[0]}–{s.pages[-1]})"
            for s in sections
        ) or "none detected",
        f"Tabelle {selected.number or '?'} '{selected.title}'" if selected else "all pages",
    )

    # Phase 1: flatten the selected section's pages into one table + build a
    # global SV name→finve_nr lookup from raw text.  Processing a single flat
    # stream means page-break artefacts (missing col-0, split Erläuterung
    # blocks) are invisible to the row-processing logic in Phase 2.
    all_table_rows: list[list] = []
    header_rows: list[list] = []
    global_sv_lookup: dict[str, int] = {}

    for page in pages:
        if page.number not in import_pages:
            continue
        if page.rows:
            all_table_rows.extend(page.rows)
            if not header_rows:
                header_rows = [row for row in page.rows if is_header_row(row)]
        global_sv_lookup.update(_build_sv_raw_lookup(page.text))

    logger.info(
        "Collected %d raw table rows; %d SV entries in raw-text lookup",
        len(all_table_rows),
        len(global_sv_lookup),
    )

    # Stage 3: one column mapping for the whole document — every value below
    # is then transferred deterministically through it.
    cmap = resolve_column_map(header_rows)
    if cmap.missing:
        logger.warning(
            "Haushalt column map (%s) has no column for: %s",
            cmap.source, ", ".join(cmap.missing),
        )

    # Phase 2: process flat table in a single pass.
    # Header rows repeat at the top of each page's table — skip them wherever
    # they appear.
    seen_first_header = False
    for cells in all_table_rows:
        if cells is None:
            continue

        # Detect/skip header rows (they repeat on every page)
        if is_header_row(cells):
            seen_first_header = True
            continue
        if not seen_first_header:
            continue

        # Skip empty/separator rows
        if not any(c for c in cells):
            continue

        # Skip the totals row that closes the table
        if _is_table_totals_row(_cell_of(cells, cmap, "name")):
            continue

        # --- Detect main FinVe row ---
        # 2026+ format: first three columns merged into col 0 as "B0080 275 N19"
        # Older format: lfd_nr in col 0, finve_nr as integer in col 1
        lfd_nr, finve_nr, bedarfsplan_nr = _parse_combined_id_cell(_cell_of(cells, cmap, "lfd_nr"))

        if lfd_nr is None:
            # Not the combined format — try old format (finve integer in col 1)
            # But first skip column-number rows like "1 | 2 | 3 | 4 ..."
            raw_col0 = _cell_of(cells, cmap, "lfd_nr")
            if raw_col0 and raw_col0.replace(".", "").strip().isdigit():
                continue

            raw_finve = _cell_of(cells, cmap, "finve_nr")
            try:
                if raw_finve:
                    finve_nr = int(raw_finve.replace(".", "").strip())
            except (ValueError, TypeError):
                pass

        if finve_nr is None:
            if lfd_nr is not None:
                # Has an lfd_nr but no FinVe number (e.g. "B0134 L 06") —
                # project without assigned FinVe yet. Flush previous row and
                # record as unmatched instead of misrouting as a Titel sub-row.
                if current_row is not None:
                    rows.append(current_row)
                    current_row = None
                raw_name = _extract_project_name(_cell_of(cells, cmap, "name"))
                unmatched_rows.append(
                    {
                        "raw_lfd_nr": lfd_nr,
                        "raw_finve_number": None,
                        "raw_bedarfsplan": bedarfsplan_nr,
                        "raw_name": raw_name,
                    }
                )
                continue

            # Not a main FinVe row — check for sub-rows
            if _is_erlaeuterung_row(cells, cmap):
                # Erläuterung block: append to current SV row.
                # With the flat table, continuation rows on subsequent pages
                # follow naturally — no "only-set-once" guard needed.
                if current_row is not None and current_row.is_sammel_finve:
                    erlaeuterung_text = _cell_of(cells, cmap, "name") or ""
                    extracted = _extract_erlaeuterung_projects(erlaeuterung_text)
                    if extracted:
                        current_row.erlaeuterung_projects.extend(extracted)
                        _refresh_sv_suggestions(current_row, finve_projects, all_projects)
            elif _is_nachrichtlich_row(cells):
                # Nachrichtlich row: may contain multiple stacked entries
                if current_row is not None:
                    current_row.proposed_titel_entries.extend(
                        _extract_nachrichtlich_entries(cells, cmap)
                    )
            elif _is_titel_row(cells):
                name_cell = _cell_of(cells, cmap, "name") or ""
                # Orphaned SV row: lost its YYY col-0 at a page break.
                # "davon:" distinguishes it from normal Titel sub-rows.
                if "davon:" in name_cell.lower():
                    sv_name = _extract_project_name(name_cell)
                    recovered_finve_nr = global_sv_lookup.get(sv_name.lower())
                    if recovered_finve_nr is not None:
                        # Flush current row and create a proper SV row
                        if current_row is not None:
                            rows.append(current_row)
                        sv_status = "update" if recovered_finve_nr in known_finve_ids else "new"
                        sv_existing_ids = (finve_projects or {}).get(recovered_finve_nr, [])
                        sv_inline_titel = _extract_inline_titel_entries(cells, cmap)
                        sv_finve, sv_budget = _build_proposed(
                            cells, cmap, year, recovered_finve_nr,
                            lfd_nr="YYY", bedarfsplan_nr=None,
                            name=sv_name, is_sv=True,
                        )
                        current_row = HaushaltsParseResultSchema(
                            finve_number=recovered_finve_nr,
                            name=sv_name,
                            status=sv_status,
                            is_sammel_finve=True,
                            proposed_finve=sv_finve,
                            proposed_budget=sv_budget,
                            proposed_titel_entries=sv_inline_titel,
                            project_ids=sv_existing_ids,
                            suggested_project_ids=[],
                        )
                        logger.info(
                            "Recovered orphaned SV row via raw text: FinVe %d (%s)",
                            recovered_finve_nr, sv_name,
                        )
                    else:
                        logger.warning(
                            "Orphaned SV row could not be recovered (no raw text match): %r",
                            sv_name,
                        )
                elif current_row is not None:
                    # Old-format separate Kap./Titel row
                    current_row.proposed_titel_entries.append(
                        _build_titel_entry(cells, cmap)
                    )
            else:
                # Erläuterung continuation row: subsequent page cells that lack the
                # "Erläuterung:" prefix but contain more bullet-listed project names.
                if (
                    current_row is not None
                    and current_row.is_sammel_finve
                    and _is_erlaeuterung_continuation(cells, cmap)
                ):
                    extracted = _extract_erlaeuterung_projects(_cell_of(cells, cmap, "name") or "")
                    if extracted:
                        current_row.erlaeuterung_projects.extend(extracted)
                        logger.debug(
                            "Erläuterung continuation for FinVe %d: +%d projects (total %d)",
                            current_row.finve_number, len(extracted),
                            len(current_row.erlaeuterung_projects),
                        )
                        _refresh_sv_suggestions(current_row, finve_projects, all_projects)
            continue

        # Flush previous row
        if current_row is not None:
            rows.append(current_row)

        # Resolve lfd_nr and bedarfsplan for old format (separate columns)
        if lfd_nr is None:
            lfd_nr = _cell_of(cells, cmap, "lfd_nr")
        if bedarfsplan_nr is None:
            bedarfsplan_nr = _cell_of(cells, cmap, "bedarfsplan")

        # Full project name = all lines before "davon:" in the name column
        raw_name = _extract_project_name(_cell_of(cells, cmap, "name"))
        is_sv = _is_sammel_finve(raw_name)

        proposed_finve, proposed_budget = _build_proposed(
            cells, cmap, year, finve_nr,
            lfd_nr=lfd_nr, bedarfsplan_nr=bedarfsplan_nr,
            name=raw_name, is_sv=is_sv,
        )

        if finve_nr in known_finve_ids:
            status = "update"
        else:
            status = "new"

        # Extract Kap./Titel entries embedded in multi-line cells (2026+ format).
        # For older PDFs these will appear as separate rows and are handled below.
        inline_titel = _extract_inline_titel_entries(cells, cmap)

        existing_project_ids = (finve_projects or {}).get(finve_nr, [])

        # Compute auto-suggestions only for new FinVes (no existing link).
        # Skip SV rows — their names don't match individual project names.
        suggested_ids: list[int] = []
        if status == "new" and all_projects and not is_sv:
            suggested_ids = suggest_projects_for_finve(raw_name, all_projects)

        current_row = HaushaltsParseResultSchema(
            finve_number=finve_nr,
            name=raw_name,
            status=status,
            is_sammel_finve=is_sv,
            proposed_finve=proposed_finve,
            proposed_budget=proposed_budget,
            proposed_titel_entries=inline_titel,
            project_ids=existing_project_ids if existing_project_ids else suggested_ids,
            suggested_project_ids=suggested_ids,
        )

    # Flush last row
    if current_row is not None:
        rows.append(current_row)

    logger.info(
        "PDF parse complete: %d FinVe rows, %d unmatched rows (column map: %s)",
        len(rows),
        len(unmatched_rows),
        cmap.source,
    )
    return HaushaltsParseTaskResult(
        year=year,
        rows=rows,
        unmatched_rows=unmatched_rows,
        column_map=cmap.to_json(),
        sections=[
            TableSectionSchema(
                number=section.number,
                title=section.title,
                page_from=section.pages[0],
                page_to=section.pages[-1],
                imported=section.imported,
            )
            for section in sections
        ],
    )


def _document_text(pdf_bytes: bytes, page_texts: list[str]) -> DocumentText:
    """The document text stored with the run.

    pdfplumber's own page text by default. With ``HAUSHALT_OCR_ENABLED`` the
    shared stage 1 (Mistral OCR, pymupdf fallback) is run over the same PDF so
    the Haushalt run is inspectable in the same terms as a VIB run.  Either way
    the table values above came from pdfplumber — this text is never parsed for
    numbers.
    """
    from dashboard_backend.core.config import settings

    if not settings.haushalt_ocr_enabled:
        return DocumentText(text="\n".join(page_texts), model="pdfplumber", status="done")

    try:
        ocr = extract_document_text(pdf_bytes)
    except Exception as exc:  # never fail an import over the inspection copy
        logger.warning("Haushalt OCR stage failed, keeping pdfplumber text: %s", exc)
        return DocumentText(text="\n".join(page_texts), model="pdfplumber", status="done")

    if not ocr.text.strip():
        return DocumentText(text="\n".join(page_texts), model="pdfplumber", status="done")
    return DocumentText(text=ocr.text, model=ocr.model, status=ocr.status)


@celery_app.task(bind=True)
def parse_haushalt_pdf(
    self: Task,
    pdf_bytes: bytes,
    year: int,
    pdf_filename: str,
    user_info: dict,
) -> dict:
    """Parse a Haushalt PDF and persist the result.

    Returns {"parse_result_id": int}.
    """
    logger.info(
        "parse_haushalt_pdf started: file=%s year=%d user=%s",
        pdf_filename,
        year,
        user_info.get("username") if user_info else "unknown",
    )
    db = Session()
    try:
        # Load all known Finve IDs for match/new classification
        known_ids: set[int] = {row[0] for row in db.query(Finve.id).all()}
        logger.info("Loaded %d known Finve IDs from DB", len(known_ids))

        # Load existing Finve→Project associations to pre-populate project_ids.
        # Regular FinVes use NULL year (permanent); SV-FinVes use the most recent year per finve.
        from sqlalchemy import func as _func
        finve_projects: dict[int, list[int]] = {}
        # 1. permanent links (regular FinVes)
        for finve_id, project_id in (
            db.query(FinveToProject.finve_id, FinveToProject.project_id)
            .filter(FinveToProject.haushalt_year.is_(None))
            .all()
        ):
            finve_projects.setdefault(finve_id, []).append(project_id)
        # 2. SV-FinVe links: only the most recent year per finve
        latest_year_subq = (
            db.query(
                FinveToProject.finve_id,
                _func.max(FinveToProject.haushalt_year).label("max_year"),
            )
            .filter(FinveToProject.haushalt_year.isnot(None))
            .group_by(FinveToProject.finve_id)
            .subquery()
        )
        for finve_id, project_id in (
            db.query(FinveToProject.finve_id, FinveToProject.project_id)
            .join(
                latest_year_subq,
                (FinveToProject.finve_id == latest_year_subq.c.finve_id)
                & (FinveToProject.haushalt_year == latest_year_subq.c.max_year),
            )
            .all()
        ):
            finve_projects.setdefault(finve_id, []).append(project_id)

        # Load all projects for auto-suggestion matching
        all_projects = db.query(Project).all()
        logger.info("Loaded %d projects for auto-suggestion matching", len(all_projects))

        task_result, document = _parse_pdf(
            pdf_bytes, year, known_ids,
            finve_projects=finve_projects,
            all_projects=all_projects,
            task=self,
        )

        # Build a minimal user-like object from user_info dict for save_parse_result
        class _UserProxy:
            def __init__(self, info: dict):
                self.id = info.get("id")
                self.username = info.get("username")

        user_proxy = _UserProxy(user_info) if user_info else None

        record = save_parse_result(
            db=db,
            year=year,
            filename=pdf_filename,
            user=user_proxy,
            status="SUCCESS",
            result_json=task_result.model_dump(),
            error=None,
            document_text=document.text,
            text_status=document.status,
            text_model=document.model,
            column_map=task_result.column_map.model_dump() if task_result.column_map else None,
            column_map_source=task_result.column_map.source if task_result.column_map else None,
        )
        db.commit()
        logger.info("parse_haushalt_pdf finished: parse_result_id=%d", record.id)
        return {"parse_result_id": record.id}

    except Exception as exc:
        logger.exception("parse_haushalt_pdf failed: %s", exc)
        db.rollback()
        # Save failure record so the user can see what went wrong
        try:
            record = save_parse_result(
                db=db,
                year=year,
                filename=pdf_filename,
                user=None,
                status="FAILURE",
                result_json=None,
                error=str(exc),
            )
            db.commit()
        except Exception:
            db.rollback()
        raise exc
    finally:
        db.close()
