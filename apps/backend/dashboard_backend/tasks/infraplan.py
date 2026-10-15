"""Infraplan importer, stage 1 — measure tables of chapter 2.3 → draft rows.

Pipeline (docs/features/feature-infraplan-import.md, "Pipeline"):

  1. Textgewinnung — pdfplumber words *with font size*, and the column
     boundaries of every table header (``find_tables``).  Deterministic: no
     LLM, no OCR.  The result (``PageData``) is plain data, so the tests run
     on a JSON fixture of it instead of the PDF.
  2. Segmentierung — sections by their headings (``Bedarfsplan, Teil A–D``,
     ``GVFG, Kat. A/C``, ``InvKG``), rows by the running number in column 1.
     Superscript footnote markers (smaller font) are split off before the
     words are joined, and the footnote area at the foot of the page is cut
     off and read separately.  A page without a header row reuses the
     columns of the last header of the same section.
  3. Semantik — header texts → canonical fields, values normalised
     (``infraplan_columns``).

Afterwards cost references are resolved, the running numbers are checked
per section (gaps/duplicates → warnings) and the pages carrying KPI charts
are noted for the page-image endpoint.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from statistics import mode

from celery import Task

from dashboard_backend.celery_app import celery_app
from dashboard_backend.schemas.infraplan_import import (
    InfraplanCostRef,
    InfraplanKpiPage,
    InfraplanParseOutput,
    InfraplanParsedRow,
    InfraplanSectionSummary,
    InfraplanWarning,
)
from dashboard_backend.tasks.infraplan_columns import (
    ColumnLayout,
    parse_cost_ref,
    parse_german_number,
    parse_ibn,
    parse_parl,
    parse_project_numbers,
    parse_state,
    resolve_layout,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stage 1 — Textgewinnung
# ---------------------------------------------------------------------------


@dataclass
class HeaderTable:
    """A table header row found by ``find_tables``: bbox and column edges."""

    bbox: tuple[float, float, float, float]  # x0, top, x1, bottom
    edges: list[float]


@dataclass
class PageData:
    number: int  # 1-indexed
    width: float
    height: float
    words: list[dict]  # text, x0, x1, top, bottom, size
    tables: list[HeaderTable] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "width": self.width,
            "height": self.height,
            "words": self.words,
            "tables": [{"bbox": list(t.bbox), "edges": t.edges} for t in self.tables],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PageData":
        return cls(
            number=data["number"],
            width=data["width"],
            height=data["height"],
            words=data["words"],
            tables=[HeaderTable(tuple(t["bbox"]), list(t["edges"])) for t in data.get("tables", [])],
        )


# Only pages that print a table header are worth the (slow) table search.
_HEADER_WORD = "Projektnummer"


def _round(value: float) -> float:
    return round(float(value), 2)


def extract_page(page, number: int) -> PageData:
    """Words with font size and the header tables of one pdfplumber page."""
    words = [
        {
            "text": w["text"],
            "x0": _round(w["x0"]),
            "x1": _round(w["x1"]),
            "top": _round(w["top"]),
            "bottom": _round(w["bottom"]),
            "size": _round(w["size"]),
        }
        for w in page.extract_words(extra_attrs=["size"])
    ]
    tables: list[HeaderTable] = []
    if any(w["text"] == _HEADER_WORD for w in words):
        for table in page.find_tables():
            cells = [c for c in table.rows[0].cells if c] if table.rows else []
            if not cells:
                continue
            x0, top, x1, bottom = table.bbox
            inside = [
                w for w in words
                if top - 1 <= w["top"] and w["bottom"] <= bottom + 1 and x0 - 1 <= w["x0"] <= x1
            ]
            if not any("Nummer" in w["text"] for w in inside):
                continue
            tables.append(
                HeaderTable(
                    bbox=(_round(x0), _round(top), _round(x1), _round(bottom)),
                    edges=[_round(c[0]) for c in cells],
                )
            )
    return PageData(
        number=number,
        width=_round(page.width),
        height=_round(page.height),
        words=words,
        tables=tables,
    )


def extract_pages(pdf_bytes: bytes, page_numbers: list[int] | None = None) -> list[PageData]:
    """Stage 1 for a whole PDF (or the given 1-indexed pages)."""
    import pdfplumber

    pages: list[PageData] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        numbers = page_numbers or list(range(1, len(pdf.pages) + 1))
        for number in numbers:
            page = pdf.pages[number - 1]
            pages.append(extract_page(page, number))
            page.flush_cache()
    return pages


# ---------------------------------------------------------------------------
# Stage 2 — Segmentierung
# ---------------------------------------------------------------------------

SECTION_TITLES: dict[str, str] = {
    "BP_A": "Bedarfsplan, Teil A – im Bau und/oder mit durchgängigem Baurecht",
    "BP_B": "Bedarfsplan, Teil B – Entwurfs- und Genehmigungsplanung",
    "BP_C": "Bedarfsplan, Teil C – Vorplanung",
    "BP_D": "Bedarfsplan, Teil D – Grundlagenermittlung",
    "GVFG_A": "GVFG, Kat. A – endgültig aufgenommene DB-Vorhaben",
    "GVFG_C": "GVFG, Kat. C – bedingt aufgenommene DB-Vorhaben",
    "INVKG": "InvKG – Maßnahmen im Bau",
}

_SECTION_HEADING_RES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^Bedarfsplan,\s*Teil\s*([A-D])\b"), "BP_{}"),
    (re.compile(r"^GVFG,\s*Kat\.\s*([AC])\b"), "GVFG_{}"),
    (re.compile(r"^InvKG\s*[–-]\s*Maßnahmen"), "INVKG"),
)
_KPI_HEADING_RE = re.compile(r"^(Steuerungskennzahl|Informationskennzahl):\s*(.*)$")

# Font sizes relative to the table body (7.5 pt in the 2026 edition): section
# headings are larger, chapter headings much larger, the footnote text smaller
# and the superscript markers smaller still.
_SECTION_HEADING_MIN_RATIO = 1.3
_CHAPTER_HEADING_MIN_RATIO = 1.75
_SUPERSCRIPT_MAX_RATIO = 0.8
_FOOTNOTE_MAX_RATIO = 0.95
_FALLBACK_BODY_SIZE = 7.5

# Words this close are one token (ligatures like "Elektri" + "fi" + "zierung").
_JOIN_GAP = 0.8
_LINE_TOLERANCE = 2.0
_ROW_START_RE = re.compile(r"^(\d{1,3})\s*\|\s*(.*)$")
# The page number sits below the footnotes; nothing of the table is that low.
_PAGE_FOOTER_MARGIN = 55.0


def _group_lines(words: list[dict]) -> list[list[dict]]:
    """Words → lines (by ``top``), each sorted left to right."""
    lines: list[list[dict]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(lines[-1][0]["top"] - word["top"]) <= _LINE_TOLERANCE:
            lines[-1].append(word)
        else:
            lines.append([word])
    return [sorted(line, key=lambda w: w["x0"]) for line in lines]


def _join_words(words: list[dict]) -> str:
    text = ""
    prev: dict | None = None
    for word in sorted(words, key=lambda w: w["x0"]):
        if prev is not None and word["x0"] - prev["x1"] >= _JOIN_GAP:
            text += " "
        text += word["text"]
        prev = word
    return text


_SOFT_BREAK_RE = re.compile(r"\w-$")
_SLASH_BREAK_RE = re.compile(r"\w/$")


def join_cell_lines(lines: list[str]) -> str:
    """Join the lines of one cell, undoing the hyphenation at line ends.

    ``Lehr-`` + ``ter`` → ``Lehrter``; ``Sachsen-`` + ``Anhalt`` →
    ``Sachsen-Anhalt``; ``Brandenburg/`` + ``Sachsen`` → ``Brandenburg/Sachsen``.
    """
    text = ""
    for line in (ln.strip() for ln in lines):
        if not line:
            continue
        if not text:
            text = line
        elif _SOFT_BREAK_RE.search(text) and line[:1].islower():
            text = text[:-1] + line
        elif _SOFT_BREAK_RE.search(text) or _SLASH_BREAK_RE.search(text):
            text += line
        else:
            text += " " + line
    return text


@dataclass
class _RawRow:
    section: str
    lfd_nr: int
    page: int
    top: float
    layout: ColumnLayout
    cell_lines: dict[int, list[str]] = field(default_factory=dict)
    footnote_refs: list[int] = field(default_factory=list)

    def add_line(self, line: list[dict]) -> None:
        by_col: dict[int, list[dict]] = {}
        for word in line:
            by_col.setdefault(self.layout.column_of(word["x0"]), []).append(word)
        for col, words in by_col.items():
            self.cell_lines.setdefault(col, []).append(_join_words(words))

    def cell(self, field_name: str) -> str | None:
        if field_name not in self.layout.fields:
            return None
        text = join_cell_lines(self.cell_lines.get(self.layout.fields.index(field_name), []))
        return text or None


@dataclass
class _Region:
    """A vertical band of one page that holds rows of one section."""

    section: str
    layout: ColumnLayout
    top: float
    bottom: float
    # Starts at the top of a page without its own header: the first lines may
    # still belong to the last row of the previous page.
    continues: bool = False


@dataclass
class _Event:
    top: float
    kind: str  # "section" | "chapter" | "header"
    section: str | None = None
    table: HeaderTable | None = None


@dataclass
class ParseState:
    """What carries over from one page to the next."""

    section: str | None = None
    layouts: dict[str, ColumnLayout] = field(default_factory=dict)
    body_size: float = _FALLBACK_BODY_SIZE
    rows: list[_RawRow] = field(default_factory=list)
    footnotes: dict[int, str] = field(default_factory=dict)
    kpi_pages: list[InfraplanKpiPage] = field(default_factory=list)
    current_kpi: tuple[str, str] | None = None
    in_kpi_chapter: bool = False
    warnings: list[InfraplanWarning] = field(default_factory=list)
    section_pages: dict[str, list[int]] = field(default_factory=dict)


def _section_of_heading(text: str) -> str | None:
    for pattern, template in _SECTION_HEADING_RES:
        match = pattern.match(text)
        if match:
            return template.format(*match.groups())
    return None


def _header_layout(page: PageData, table: HeaderTable) -> tuple[ColumnLayout, float]:
    """Resolve the column layout of one header and the table body font size."""
    x0, top, x1, bottom = table.bbox
    header_words = [
        w for w in page.words
        if top - 1 <= w["top"] and w["bottom"] <= bottom + 1 and x0 - 1 <= w["x0"] <= x1
    ]
    body_size = mode([w["size"] for w in header_words]) if header_words else _FALLBACK_BODY_SIZE
    regular = [w for w in header_words if w["size"] > body_size * _SUPERSCRIPT_MAX_RATIO]
    edges = list(table.edges)
    probe = ColumnLayout(edges=tuple(edges), fields=tuple("?" * len(edges)), cost_kind="GWU")
    texts: list[list[dict]] = [[] for _ in edges]
    for word in regular:
        texts[probe.column_of(word["x0"])].append(word)
    header_texts = [
        join_cell_lines([_join_words(line) for line in _group_lines(col)]) for col in texts
    ]
    return resolve_layout(edges, header_texts), body_size


def _footnote_zone_top(page: PageData, body_size: float, left_edge: float, below: float) -> float | None:
    """Top of the footnote area: the first line opened by a small footnote number
    at the left margin (table rows start further right and in body size)."""
    for line in _group_lines([w for w in page.words if w["top"] > below]):
        first = line[0]
        if (
            first["text"].isdigit()
            and body_size * _SUPERSCRIPT_MAX_RATIO < first["size"] < body_size * _FOOTNOTE_MAX_RATIO
            and first["x0"] < left_edge + 2.0
        ):
            return first["top"] - 0.5
    return None


def _read_footnotes(page: PageData, zone_top: float, body_size: float, left_edge: float, into: dict[int, str]) -> None:
    footer_top = page.height - _PAGE_FOOTER_MARGIN
    words = [
        w for w in page.words
        if zone_top <= w["top"] < footer_top
        and body_size * _SUPERSCRIPT_MAX_RATIO < w["size"] < body_size * _FOOTNOTE_MAX_RATIO
    ]
    current: int | None = None
    parts: dict[int, list[str]] = {}
    for line in _group_lines(words):
        first = line[0]
        if first["text"].isdigit() and first["x0"] < left_edge + 2.0:
            current = int(first["text"])
            parts[current] = [_join_words(line[1:])]
        elif current is not None:
            parts[current].append(_join_words(line))
    for number, lines in parts.items():
        into.setdefault(number, join_cell_lines(lines))


def _page_events(page: PageData, body_size: float) -> list[_Event]:
    events: list[_Event] = []
    for line in _group_lines(page.words):
        size = max(w["size"] for w in line)
        text = _join_words(line)
        if size >= body_size * _CHAPTER_HEADING_MIN_RATIO and re.match(r"^\d+(\.\d+)*\s|^[IVX]+:", text):
            events.append(_Event(top=line[0]["top"], kind="chapter"))
        elif size >= body_size * _SECTION_HEADING_MIN_RATIO:
            section = _section_of_heading(text)
            if section:
                events.append(_Event(top=line[0]["top"], kind="section", section=section))
    for table in page.tables:
        events.append(_Event(top=table.bbox[1], kind="header", table=table))
    return sorted(events, key=lambda e: e.top)


# Gap between two words that separates the two text columns of a page.
_COLUMN_GAP = 15.0
# Chart captions are set in 11.5 pt above a unit line such as "(jährlich in km)".
_CAPTION_MIN_RATIO = 1.4
_CAPTION_MAX_RATIO = 1.65
_UNIT_LINE_RE = re.compile(r"^[(\[]")
# Only the KPI chapters themselves ("3 Steuerungskennzahlen", "I:
# Informationskennzahlen") hold charts; the appendix repeats the KPI headings
# above lists of measures ("II.1 Zugrundeliegende Maßnahmen der …").
_KPI_CHAPTER_RE = re.compile(r"^(\d+|[IVX]+:)\s*(Steuerungs|Informations)kennzahlen$")
_KPI_CHAPTER_MIN_SIZE = 15.0


def _segments(words: list[dict]) -> list[list[dict]]:
    """Lines split at column gaps and by font size, in reading order.

    Splitting by size keeps the text drawn inside a chart (a layer of its
    own, often at the same height) apart from the caption above it.
    Superscripts stay with their line.
    """
    segments: list[list[dict]] = []
    for line in _group_lines(words):
        base = max(w["size"] for w in line)
        by_size: dict[float, list[dict]] = {}
        for word in line:
            size = word["size"]
            if size <= base * _SUPERSCRIPT_MAX_RATIO:
                size = min((s for s in {w["size"] for w in line} if s > size), default=size)
            by_size.setdefault(round(size, 1), []).append(word)
        for group in by_size.values():
            current = [group[0]]
            for word in group[1:]:
                if word["x0"] - current[-1]["x1"] > _COLUMN_GAP:
                    segments.append(current)
                    current = [word]
                else:
                    current.append(word)
            segments.append(current)
    return sorted(segments, key=lambda seg: (seg[0]["top"], seg[0]["x0"]))


def _regular_text(segment: list[dict], size: float) -> str:
    """Text of a heading segment without superscript footnote markers."""
    return _join_words([w for w in segment if w["size"] > size * _SUPERSCRIPT_MAX_RATIO])


def _kpi_title(segments: list[list[dict]], index: int, rest: str) -> str:
    """The KPI name: the rest of the heading plus the following heading lines
    of the same column and size ("Steuerungskennzahl: Umsetzung Kleiner" /
    "und Mittlerer Maßnahmen (KMM)")."""
    head = segments[index]
    size = head[0]["size"]
    parts = [rest] if rest else []
    last_top = head[0]["top"]
    for segment in segments[index + 1:]:
        first = segment[0]
        if first["top"] - last_top > size * 1.6:
            break
        if abs(first["x0"] - head[0]["x0"]) > 3.0 or abs(first["size"] - size) > 0.3:
            continue
        if _KPI_HEADING_RE.match(_join_words(segment)):
            break
        parts.append(_regular_text(segment, size))
        last_top = first["top"]
    return join_cell_lines(parts)


def _detect_kpi_charts(page: PageData, state: ParseState) -> None:
    """Note the pages that carry KPI charts.

    A KPI starts at its heading ("Steuerungskennzahl: …" /
    "Informationskennzahl: …"); its chart often follows on the next page. A
    page counts as a chart page when it holds a chart caption with a unit
    line below it, and the chart belongs to the last KPI heading before it.
    """
    segments = _segments(page.words)
    noted = False
    for i, segment in enumerate(segments):
        size = max(w["size"] for w in segment)
        if size >= _KPI_CHAPTER_MIN_SIZE:
            state.in_kpi_chapter = bool(_KPI_CHAPTER_RE.match(_join_words(segment)))
            state.current_kpi = None
            continue
        if not state.in_kpi_chapter:
            continue
        match = _KPI_HEADING_RE.match(_regular_text(segment, size))
        if match and size >= state.body_size * _SECTION_HEADING_MIN_RATIO:
            kind = "STEUERUNG" if match.group(1).startswith("Steuerung") else "INFORMATION"
            state.current_kpi = (kind, _kpi_title(segments, i, match.group(2).strip()))
            continue
        if noted or state.current_kpi is None:
            continue
        if not state.body_size * _CAPTION_MIN_RATIO <= size <= state.body_size * _CAPTION_MAX_RATIO:
            continue
        top, x0 = segment[0]["top"], segment[0]["x0"]
        has_unit_line = any(
            0 < other[0]["top"] - top <= size * 1.6
            and abs(other[0]["x0"] - x0) <= 3.0
            and abs(other[0]["size"] - size) <= 0.3
            and _UNIT_LINE_RE.match(_join_words(other))
            for other in segments[i + 1:]
        )
        if has_unit_line:
            kind, title = state.current_kpi
            state.kpi_pages.append(InfraplanKpiPage(page=page.number, kind=kind, title=title))
            noted = True


def parse_page(page: PageData, state: ParseState) -> None:
    """Segment one page into rows, carrying section and layout over in ``state``."""
    _detect_kpi_charts(page, state)

    regions: list[_Region] = []
    open_top: float | None = 0.0 if state.section else None
    open_section = state.section
    open_layout = state.layouts.get(state.section) if state.section else None
    left_edge = open_layout.edges[0] if open_layout else 80.0
    first_header_bottom: float | None = None

    events = _page_events(page, state.body_size)
    if open_top == 0.0 and events and events[0].kind == "header":
        open_top = None  # the page brings its own header

    def close(at: float) -> None:
        if open_section and open_layout and open_top is not None and at > open_top:
            regions.append(
                _Region(open_section, open_layout, open_top, at, continues=open_top == 0.0)
            )

    for event in events:
        if event.kind == "chapter":
            close(event.top)
            open_section, open_layout, open_top = None, None, None
        elif event.kind == "section":
            close(event.top)
            open_section, open_layout, open_top = event.section, None, None
        elif event.kind == "header" and event.table is not None:
            close(event.top)
            if open_section is None:
                continue  # a table outside the measure lists
            layout, body_size = _header_layout(page, event.table)
            state.layouts[open_section] = layout
            state.body_size = body_size
            open_layout, open_top = layout, event.table.bbox[3]
            left_edge = layout.edges[0]
            if first_header_bottom is None:
                first_header_bottom = event.table.bbox[3]
        if open_section and open_layout is None and event.kind == "section":
            # A section heading without its header row on this page: the
            # columns of the last header of the same section apply.
            carried = state.layouts.get(open_section)
            if carried is not None:
                open_layout, open_top = carried, event.top

    page_bottom = page.height - _PAGE_FOOTER_MARGIN
    zone = _footnote_zone_top(page, state.body_size, left_edge, first_header_bottom or 0.0)
    if zone is not None:
        _read_footnotes(page, zone, state.body_size, left_edge, state.footnotes)
        page_bottom = min(page_bottom, zone)
    close(page_bottom)
    if open_section and open_layout is None:
        state.warnings.append(
            InfraplanWarning(
                kind="NO_LAYOUT",
                section=open_section,
                page=page.number,
                message=f"Seite {page.number}: keine Kopfzeile für {open_section} gefunden.",
            )
        )
    state.section = open_section

    for region in regions:
        regions_pages = state.section_pages.setdefault(region.section, [])
        if page.number not in regions_pages:
            regions_pages.append(page.number)
        _parse_region(page, region, state)


def _parse_region(page: PageData, region: _Region, state: ParseState) -> None:
    words = [
        w for w in page.words
        if region.top <= w["top"] < region.bottom and w["x0"] >= region.layout.edges[0] - 2.0
    ]
    superscripts = [w for w in words if w["size"] <= state.body_size * _SUPERSCRIPT_MAX_RATIO]
    body = [w for w in words if w["size"] > state.body_size * _SUPERSCRIPT_MAX_RATIO]

    page_rows: list[_RawRow] = []
    current: _RawRow | None = None
    for line in _group_lines(body):
        first_col = [w for w in line if region.layout.column_of(w["x0"]) == 0]
        match = _ROW_START_RE.match(_join_words(first_col)) if first_col else None
        if match:
            current = _RawRow(
                section=region.section,
                lfd_nr=int(match.group(1)),
                page=page.number,
                top=line[0]["top"],
                layout=region.layout,
            )
            page_rows.append(current)
            state.rows.append(current)
            current.add_line(line)
        elif current is not None:
            current.add_line(line)
        elif region.continues and state.rows and state.rows[-1].section == region.section:
            # A row running over from the previous page.
            state.rows[-1].add_line(line)

    for sup in superscripts:
        owner = None
        for row in page_rows:
            if row.top - 3.0 <= sup["top"]:
                owner = row
        if owner is None:
            continue
        for part in sup["text"].split(","):
            if part.strip().isdigit():
                number = int(part)
                if number not in owner.footnote_refs:
                    owner.footnote_refs.append(number)


# ---------------------------------------------------------------------------
# Stage 3 — Semantik
# ---------------------------------------------------------------------------


def _to_row(raw: _RawRow) -> InfraplanParsedRow:
    first = raw.cell("lfd_projekt") or ""
    match = _ROW_START_RE.match(first)
    numbers_raw = match.group(2).strip() if match else None
    numbers = parse_project_numbers(numbers_raw, raw.section)

    state_raw = raw.cell("state")
    state = parse_state(state_raw)
    ibn_raw = raw.cell("ibn")
    ibn_year, ibn_qualifier = parse_ibn(ibn_raw)
    cost_raw = raw.cell("cost")
    ref = parse_cost_ref(cost_raw)
    parl_raw = raw.cell("parl")

    return InfraplanParsedRow(
        row_key=f"{raw.section}-{raw.lfd_nr}",
        section=raw.section,
        lfd_nr=raw.lfd_nr,
        page=raw.page,
        project_numbers_raw=numbers_raw or None,
        project_numbers=numbers,
        primary_number=numbers[0] if numbers else None,
        bezeichnung=raw.cell("bezeichnung"),
        massnahme=raw.cell("massnahme"),
        laender=raw.cell("land"),
        state_raw=state_raw,
        lph_from=state.lph_from,
        lph_to=state.lph_to,
        under_construction=state.under_construction,
        baurecht=state.baurecht,
        ibn_raw=ibn_raw,
        ibn_year=ibn_year,
        ibn_qualifier=ibn_qualifier,
        cost_raw=cost_raw,
        cost_mio=None if ref else parse_german_number(cost_raw),
        cost_kind=raw.layout.cost_kind,
        cost_ref_raw=cost_raw if ref else None,
        cost_ref=InfraplanCostRef(section=ref[0], lfd_nr=ref[1]) if ref else None,
        parl_raw=parl_raw,
        parl_state=parse_parl(parl_raw),
        footnote_refs=raw.footnote_refs,
    )


_MAX_REF_DEPTH = 5


def resolve_cost_refs(rows: list[InfraplanParsedRow]) -> list[InfraplanWarning]:
    """Point every cost reference at the entry that carries the cost."""
    by_key = {(r.section, r.lfd_nr): r for r in rows}
    warnings: list[InfraplanWarning] = []
    for row in rows:
        if row.cost_ref is None:
            continue
        target = by_key.get((row.cost_ref.section, row.cost_ref.lfd_nr))
        depth = 0
        while target is not None and target.cost_ref is not None and depth < _MAX_REF_DEPTH:
            target = by_key.get((target.cost_ref.section, target.cost_ref.lfd_nr))
            depth += 1
        if target is None or target.cost_mio is None:
            warnings.append(
                InfraplanWarning(
                    kind="UNRESOLVED_REF",
                    section=row.section,
                    lfd_nr=row.lfd_nr,
                    page=row.page,
                    message=(
                        f"{row.section} {row.lfd_nr}: Kostenverweis „{row.cost_ref_raw}“ "
                        "ließ sich nicht auflösen."
                    ),
                )
            )
            continue
        row.cost_ref.resolved = True
        row.cost_ref.cost_mio = target.cost_mio
    return warnings


def check_running_numbers(rows: list[InfraplanParsedRow]) -> list[InfraplanWarning]:
    """Running numbers are 1..n per section; report gaps and duplicates."""
    warnings: list[InfraplanWarning] = []
    by_section: dict[str, list[int]] = {}
    for row in rows:
        by_section.setdefault(row.section, []).append(row.lfd_nr)
    for section, numbers in by_section.items():
        seen: set[int] = set()
        for number in numbers:
            if number in seen:
                warnings.append(
                    InfraplanWarning(
                        kind="DUPLICATE",
                        section=section,
                        lfd_nr=number,
                        message=f"{section}: laufende Nummer {number} kommt mehrfach vor.",
                    )
                )
            seen.add(number)
        for number in range(1, max(numbers) + 1):
            if number not in seen:
                warnings.append(
                    InfraplanWarning(
                        kind="GAP",
                        section=section,
                        lfd_nr=number,
                        message=f"{section}: laufende Nummer {number} fehlt.",
                    )
                )
    for section in SECTION_TITLES:
        if section not in by_section:
            warnings.append(
                InfraplanWarning(
                    kind="EMPTY_SECTION",
                    section=section,
                    message=f"Abschnitt „{SECTION_TITLES[section]}“ wurde nicht gefunden.",
                )
            )
    return warnings


@dataclass
class InfraplanParse:
    output: InfraplanParseOutput
    warnings: list[InfraplanWarning]
    kpi_pages: list[InfraplanKpiPage]


def parse_pages(pages: list[PageData]) -> InfraplanParse:
    """Stages 2 and 3 over already extracted pages."""
    state = ParseState()
    for page in pages:
        parse_page(page, state)

    rows = [_to_row(raw) for raw in state.rows]
    for row in rows:
        row.footnotes = {
            str(nr): state.footnotes[nr] for nr in row.footnote_refs if nr in state.footnotes
        }
    warnings = list(state.warnings)
    warnings += check_running_numbers(rows)
    warnings += resolve_cost_refs(rows)

    sections = [
        InfraplanSectionSummary(
            key=key,
            title=title,
            row_count=sum(1 for r in rows if r.section == key),
            pages=state.section_pages.get(key, []),
        )
        for key, title in SECTION_TITLES.items()
    ]
    output = InfraplanParseOutput(
        sections=sections,
        rows=rows,
        footnotes={str(k): v for k, v in sorted(state.footnotes.items())},
        page_count=len(pages),
    )
    return InfraplanParse(output=output, warnings=warnings, kpi_pages=state.kpi_pages)


def parse_infraplan_pdf_bytes(pdf_bytes: bytes) -> InfraplanParse:
    return parse_pages(extract_pages(pdf_bytes))


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------


def report_step(task: Task | None, step: str, label: str) -> None:
    """Tell the poller which stage runs now (no-op outside a worker)."""
    if task is None or not task.request.id:
        return
    task.update_state(state="PROGRESS", meta={"step": step, "step_label": label})


@celery_app.task(bind=True)
def parse_infraplan_pdf(self: Task, parse_result_id: int) -> dict:
    """Parse the PDF stored with draft ``parse_result_id`` and save the result.

    The PDF stays on disk (it belongs to the draft, not to the task), so the
    same task serves the first parse and every re-parse.
    """
    from dashboard_backend.crud.infraplan_import import (
        get_parse_result,
        mark_parse_failed,
        mark_parse_running,
        save_parse_output,
    )
    from dashboard_backend.database import Session
    from dashboard_backend.utils.file_storage import read_infraplan_pdf

    db = Session()
    try:
        record = get_parse_result(db, parse_result_id)
        if record is None:
            raise ValueError(f"Infraplan-Entwurf {parse_result_id} nicht gefunden")
        mark_parse_running(db, record)
        db.commit()

        report_step(self, "extract", "Seiten werden gelesen…")
        pdf_bytes = read_infraplan_pdf(record.pdf_path)
        pages = extract_pages(pdf_bytes)
        report_step(self, "parse", "Tabellen werden ausgewertet…")
        result = parse_pages(pages)
        report_step(self, "save", f"{len(result.output.rows)} Zeilen — Ergebnis wird gespeichert…")
        save_parse_output(db, record, result.output, result.warnings, result.kpi_pages)
        db.commit()
        logger.info(
            "parse_infraplan_pdf finished: id=%d rows=%d warnings=%d",
            record.id, len(result.output.rows), len(result.warnings),
        )
        return {"parse_result_id": record.id}
    except Exception as exc:
        logger.exception("parse_infraplan_pdf failed: %s", exc)
        db.rollback()
        try:
            record = get_parse_result(db, parse_result_id)
            if record is not None:
                mark_parse_failed(db, record, str(exc))
                db.commit()
        except Exception:
            db.rollback()
        raise
    finally:
        db.close()
