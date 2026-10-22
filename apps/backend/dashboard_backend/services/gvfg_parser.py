"""Parser for the GVFG-Bundesprogramm PDF (docs/features/feature-gvfg-import.md).

The programme is a text PDF (exported from Excel), one table per Land and
project kind (kommunal / DB) and part (finanzrelevant / nachrichtlich). pdfplumber
finds the tables and their cells; the numbers are read deterministically from
the text — no OCR, no LLM.

Columns are mapped by their header text against a fixed vocabulary
(``_classify_column``). An unknown column aborts the parse with a clear message
instead of guessing: a new column is a new edition format that needs a look.

A project row of the financial part holds up to four amount lines (∑, A, B, C)
inside one table row; pdfplumber joins them with newlines and drops empty
cells, so each number is assigned to the category line at the same height.

The parse also reads the "Summe über <Land>" rows and checks them against the
sum of the parsed projects (``ParseResult.warnings``).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Any, BinaryIO

import pdfplumber

LAND_BY_CODE = {
    "01": "Schleswig-Holstein",
    "02": "Hamburg",
    "03": "Niedersachsen",
    "04": "Bremen",
    "05": "Nordrhein-Westfalen",
    "06": "Hessen",
    "07": "Rheinland-Pfalz",
    "08": "Baden-Württemberg",
    "09": "Bayern",
    "10": "Saarland",
    "11": "Berlin",
    "12": "Brandenburg",
    "13": "Mecklenburg-Vorpommern",
    "14": "Sachsen",
    "15": "Sachsen-Anhalt",
    "16": "Thüringen",
}

# The underscore before the suffix is sometimes missing ("03 D 4505 A", 2023).
KEY_RE = re.compile(r"(\d{1,2})\s*([GD])\s*(\d+)(?:\s*_\s*|\s+)([A-Z])\b")

CATEGORY_SUM = "SUM"
CATEGORIES = (CATEGORY_SUM, "A", "B", "C")

PART_FINANCIAL = "finanzrelevant"
PART_INFORMATIONAL = "nachrichtlich"

KIND_MUNICIPAL = "kommunal"
KIND_DB = "db"

# Period kinds of the yearly aid columns.
PERIOD_PAID = "ausgezahlt"  # 1967–YYYY and single years before the edition
PERIOD_PAID_EXPECTED = "voraussichtlich"  # "vsl. 2022"
PERIOD_PLANNED = "geplant"  # the edition's five years
PERIOD_REST = "rest"  # "Rest ab YYYY"

_META_FIELDS = (
    "nr",
    "key",
    "city",
    "name",
    "lph",
    "funding_type",
    "funding_rate",
    "start_year",
    "construction_start",
    "commissioning_planned",
    "commissioning_actual",
    "category",
)
_AMOUNT_FIELDS = ("cost_total", "cost_eligible", "aid_total")

# Height difference (pt) within which a number belongs to a category line.
_LINE_TOLERANCE = 4.0


class GvfgParseError(ValueError):
    """The PDF does not look like a GVFG programme we can read (German message)."""


def normalize_key(text: str | None) -> str | None:
    """``"01 G 540 _ A"`` / ``"Projektschlüssel 5 G 7007_A"`` → ``"01 G 540_A"``."""
    if not text:
        return None
    match = KEY_RE.search(text)
    if not match:
        return None
    land, kind, number, suffix = match.groups()
    return f"{int(land):02d} {kind} {number}_{suffix}"


def key_without_suffix(key: str) -> str:
    return key.rsplit("_", 1)[0]


def parse_decimal(text: str | None) -> Decimal | None:
    """German number ``"1.662,00"`` → ``Decimal("1662.00")``; empty → None."""
    if text is None:
        return None
    cleaned = text.strip().replace(".", "").replace(",", ".").replace("−", "-")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


# --- Result types -----------------------------------------------------------


@dataclass
class Period:
    """One yearly aid column: ``label`` as printed, years covered and its kind."""

    label: str
    year_from: int | None
    year_to: int | None
    kind: str


@dataclass
class AmountLine:
    category: str
    # True for a ∑ line the parser added because the PDF printed only A/B/C.
    computed: bool = False
    cost_total: Decimal | None = None
    cost_eligible: Decimal | None = None
    aid_total: Decimal | None = None
    # Period label → amount
    periods: dict[str, Decimal] = field(default_factory=dict)


@dataclass
class ParsedEntry:
    key: str
    key_raw: str
    land: str
    kind: str
    part: str
    page: int
    nr: str | None = None
    city: str | None = None
    name: str | None = None
    lph: str | None = None
    funding_type: str | None = None
    funding_rate: int | None = None
    start_year: int | None = None
    construction_start: int | None = None
    commissioning_planned: int | None = None
    commissioning_actual: int | None = None
    amounts: list[AmountLine] = field(default_factory=list)


@dataclass
class ParsedTotal:
    """A "Summe über <Land>" line, used to check the parse."""

    land: str
    kind: str
    part: str
    category: str
    cost_total: Decimal | None
    cost_eligible: Decimal | None
    aid_total: Decimal | None
    page: int


@dataclass
class ParseResult:
    title: str | None
    year_from: int | None
    year_to: int | None
    stand: str | None
    is_annex: bool
    periods: list[Period]
    entries: list[ParsedEntry]
    totals: list[ParsedTotal]
    warnings: list[str]

    def to_json(self) -> dict[str, Any]:
        """JSON-safe dict (Decimals as strings) for the staged parse result."""

        def convert(value: Any) -> Any:
            if isinstance(value, Decimal):
                return str(value)
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            if isinstance(value, list):
                return [convert(v) for v in value]
            return value

        return convert(asdict(self))


# --- Column classification --------------------------------------------------


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\n", " ")).strip()


def _classify_column(header: str, edition_start: int | None) -> tuple[str, Period | None]:
    """Header text of one column → field name (and the Period for year columns).

    Raises GvfgParseError for a header that is not in the vocabulary.
    """
    h = header.lower()
    if h in ("", "nr."):
        return ("nr" if h == "nr." else "", None)
    if "schlüssel" in h:
        return "key", None
    if "stadt/region" in h:
        return "city", None
    if "bezeichnung" in h:
        return "name", None
    if h == "lph":
        return "lph", None
    if "fördertatbestand" in h:
        return "funding_type", None
    if "fördersatz" in h:
        return "funding_rate", None
    if "mittel" in h and "abfluss" in h:
        return "start_year", None
    if h.startswith("bau-") or h.startswith("baubeginn") or "bau- beginn" in h:
        return "construction_start", None
    if "inbetrieb" in h and "gepl" in h:
        return "commissioning_planned", None
    if "inbetrieb" in h and "tats" in h:
        return "commissioning_actual", None
    if "kategorie" in h or h.startswith("kat. a"):
        return "category", None
    if "gesamtkosten" in h:
        return "cost_total", None
    if "zwf" in h:
        return "cost_eligible", None
    if "insgesamt" in h:
        return "aid_total", None
    span = re.search(r"1967\s*-\s*(\d{4})", h)
    if span:
        year = int(span.group(1))
        return "period", Period(f"1967–{year}", 1967, year, PERIOD_PAID)
    year_match = re.search(r"(\d{4})", h)
    if year_match:
        year = int(year_match.group(1))
        if "rest" in h or h.startswith("ab "):
            return "period", Period(f"ab {year}", year, None, PERIOD_REST)
        if "vsl" in h:
            return "period", Period(f"vsl. {year}", year, year, PERIOD_PAID_EXPECTED)
        kind = PERIOD_PAID if edition_start is not None and year < edition_start else PERIOD_PLANNED
        return "period", Period(str(year), year, year, kind)
    if h in ("bundesfinanzhilfen", "bereits ausgezahlt", "rest ab", "vorhaben/teilvorhaben"):
        return "", None
    raise GvfgParseError(f"Unbekannte Spalte im GVFG-Programm: „{header}“")


@dataclass
class _Columns:
    fields: list[str]
    periods: dict[int, Period]
    # Column index → (x0, x1) of its header cell. Numbers are placed by these
    # spans: some data rows lack a vertical rule, so one data cell can hold the
    # numbers of two columns.
    spans: dict[int, tuple[float, float]]


def _header_columns(
    table: list[list[str | None]],
    edition_start: int | None,
    row_cells: list[list[Any]] | None = None,
) -> tuple[_Columns, int] | None:
    """Find the header rows of a table; returns the column map and the index of
    the first data row, or None when the table has no header (continuation)."""
    first_data = None
    for idx, row in enumerate(table):
        if row and row[0] is not None and re.fullmatch(r"\d+", _clean(row[0]) or "-") and any(
            normalize_key(_clean(c)) for c in row[1:3] if c
        ):
            first_data = idx
            break
    if first_data is None or first_data == 0:
        return None
    header_rows = table[:first_data]
    width = max(len(r) for r in table)
    texts = []
    for col in range(width):
        parts = []
        for row in header_rows:
            cell = _clean(row[col]) if col < len(row) else ""
            # Neither the column numbers ("1 2 3 …", 2023 edition) nor a title
            # row that pdfplumber put into the table are header text.
            if (
                cell
                and not re.fullmatch(r"\d{1,2}", cell)
                and cell != "Mio. €"
                and "Bundesprogramm" not in cell
                and "Personennahverkehr" not in cell
            ):
                parts.append(cell)
        texts.append(" ".join(parts))
    fields: list[str] = []
    periods: dict[int, Period] = {}
    for col, text in enumerate(texts):
        name, period = _classify_column(text, edition_start)
        if name == "" and col > 0 and texts[col - 1] and "rest ab" in texts[col - 1].lower():
            name = ""
        fields.append(name)
        if period is not None:
            periods[col] = period
    # "insgesamt" can slip into the neighbouring header cell (2023, p. 44); the
    # column right after the eligible costs then reads only "Bundesfinanzhilfen".
    if "aid_total" not in fields and "cost_eligible" in fields:
        col = fields.index("cost_eligible") + 1
        if col < len(fields) and fields[col] == "" and texts[col].lower() == "bundesfinanzhilfen":
            fields[col] = "aid_total"
    if "key" not in fields:
        return None
    spans: dict[int, tuple[float, float]] = {}
    for cells in (row_cells or [])[:first_data]:
        for col, bbox in enumerate(cells):
            if bbox is None or col >= len(fields) or not fields[col]:
                continue
            x0, x1 = bbox[0], bbox[2]
            if col not in spans or (x1 - x0) < (spans[col][1] - spans[col][0]):
                spans[col] = (x0, x1)
    return _Columns(fields, periods, spans), first_data


# --- Page parsing -----------------------------------------------------------


def _page_context(text: str) -> tuple[str | None, str | None, str | None]:
    land = re.search(r"Land:\s*([^\n]+?)\s{2,}|Land:\s*([^\n]+)", text)
    land_name = None
    if land:
        land_name = _clean(land.group(1) or land.group(2))
        land_name = re.sub(r"\s*Stand:.*$", "", land_name)
    kind = None
    if re.search(r"kommunale Vorhaben", text):
        kind = KIND_MUNICIPAL
    if re.search(r"DB-Vorhaben", text) and (kind is None or text.find("DB-Vorhaben") < text.find("kommunale Vorhaben")):
        kind = KIND_DB
    part = (
        PART_INFORMATIONAL
        if re.search(r"nachrichtlicher Teil|-\s*Anhang\s*-", text)
        else PART_FINANCIAL
    )
    return land_name, kind, part


def _font_scale(page) -> float:
    """Font size of the page relative to the common 4.2 pt; tolerances scale with it
    (one 2023 page is printed at 2.2 pt, the 2024 edition at 9 pt)."""
    sizes = sorted(c["size"] for c in page.chars)
    if not sizes:
        return 1.0
    return max(sizes[len(sizes) // 2] / 4.2, 0.3)


def _assign(lines: list[tuple[float, str]], top: float, scale: float) -> int | None:
    """Index of the category line at the height of a number."""
    best = min(range(len(lines)), key=lambda i: abs(lines[i][0] - top), default=None)
    if best is None or abs(lines[best][0] - top) > _LINE_TOLERANCE * scale:
        return None
    return best


def _same_land(printed: str, expected: str) -> bool:
    # The header has typos ("Saaarland", "Schleswig-Hollstein").
    return SequenceMatcher(None, printed.lower(), expected.lower()).ratio() >= 0.85


def _canonical_land(printed: str) -> str:
    return max(
        LAND_BY_CODE.values(),
        key=lambda name: SequenceMatcher(None, printed.lower(), name.lower()).ratio(),
    )


def _int(text: str | None) -> int | None:
    match = re.search(r"\d{4}", text or "")
    return int(match.group(0)) if match else None


def _rate(text: str | None) -> int | None:
    match = re.search(r"(\d{1,3})\s*%", text or "")
    return int(match.group(1)) if match else None


_NUMBER_RE = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}|-?\d+,\d{2}")


def _page_totals(text: str, land: str, kind: str, part: str, page_no: int) -> list[ParsedTotal]:
    """The "Summe über <Land>" line and the "Kat. A/C" lines right below it.

    Only the first three numbers are used: costs, eligible costs, aid total.
    """
    totals = []
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if "Summe über" not in line:
            continue
        candidates = [(CATEGORY_SUM, line)]
        for follow in lines[idx + 1 : idx + 6]:
            stripped = follow.strip()
            cat = re.match(r"Kat\.\s*([ABC])\b", stripped)
            if cat:
                candidates.append((cat.group(1), stripped))
            elif stripped and not re.fullmatch(r"(kommunale Vorhaben|DB-Vorhaben)", stripped):
                break
        for category, source in candidates:
            numbers = [parse_decimal(n) for n in _NUMBER_RE.findall(source)]
            if not numbers:
                continue
            numbers = (numbers + [None, None, None])[:3]
            if part == PART_INFORMATIONAL:
                numbers = [numbers[0], numbers[1], numbers[2]]
            totals.append(ParsedTotal(land, kind, part, category, *numbers, page=page_no))
    return totals


def parse_gvfg_pdf(source: str | BinaryIO) -> ParseResult:
    """Parse a GVFG programme (main part or annex) into entries, totals and warnings."""
    entries: list[ParsedEntry] = []
    totals: list[ParsedTotal] = []
    warnings: list[str] = []
    periods_by_label: dict[str, Period] = {}
    title = stand = None
    year_from = year_to = None
    is_annex = False
    last_columns: _Columns | None = None
    # Period labels of the table each entry was read from, parallel to entries.
    layouts: list[tuple[str, ...]] = []

    with pdfplumber.open(source) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            scale = _font_scale(page)
            tol = 3 * scale
            text = page.extract_text(x_tolerance=tol, y_tolerance=tol) or ""
            if year_from is None:
                prog = re.search(r"Bundesprogramm\s+(\d{4})\s*-\s*(\d{4})", text)
                if prog:
                    year_from, year_to = int(prog.group(1)), int(prog.group(2))
                    title = f"GVFG-Bundesprogramm {year_from}–{year_to}"
            if stand is None:
                stand_match = re.search(r"Stand:\s*(\d{2}\.\d{2}\.\d{4})", text)
                if stand_match:
                    stand = stand_match.group(1)
            if re.search(r"-\s*Anhang\s*-", text):
                is_annex = True
            land_name, kind, part = _page_context(text)
            totals.extend(_page_totals(text, land_name or "", kind or "", part, page_no))
            page_words = None

            for table in page.find_tables(
                {"text_x_tolerance": tol, "text_y_tolerance": tol}
            ):
                rows = table.extract(x_tolerance=tol, y_tolerance=tol)
                header = _header_columns(rows, year_from, [r.cells for r in table.rows])
                if header is not None:
                    columns, first_data = header
                    last_columns = columns
                else:
                    columns, first_data = last_columns, 0
                for row_idx, row in enumerate(rows):
                    if columns is None or row_idx < first_data:
                        continue
                    if len(row) != len(columns.fields):
                        continue
                    values = {
                        name: row[col]
                        for col, name in enumerate(columns.fields)
                        if name and name != "period"
                    }
                    key = normalize_key(_clean(values.get("key")))
                    if key is None:
                        continue
                    entry = ParsedEntry(
                        key=key,
                        key_raw=_clean(values.get("key")),
                        land=LAND_BY_CODE.get(key[:2], land_name or ""),
                        # The heading the programme lists it under wins over the key
                        # letter: a few "G" projects sit in the DB tables and vice versa.
                        kind=kind or (KIND_DB if key[3] == "D" else KIND_MUNICIPAL),
                        part=part,
                        page=page_no,
                        nr=_clean(values.get("nr")) or None,
                        city=_clean(values.get("city")) or None,
                        name=_clean(values.get("name")) or None,
                        lph=_clean(values.get("lph")) or None,
                        funding_type=_clean(values.get("funding_type")) or None,
                        funding_rate=_rate(values.get("funding_rate")),
                        start_year=_int(values.get("start_year")),
                        construction_start=_int(values.get("construction_start")),
                        commissioning_planned=_int(values.get("commissioning_planned")),
                        commissioning_actual=_int(values.get("commissioning_actual")),
                    )
                    if land_name and LAND_BY_CODE.get(key[:2]) and not _same_land(land_name, LAND_BY_CODE[key[:2]]):
                        warnings.append(
                            f"S. {page_no}: {key} steht unter „{land_name}“, der Schlüssel "
                            f"gehört zu {LAND_BY_CODE[key[:2]]}."
                        )
                    if page_words is None:
                        page_words = _page_words(page, scale)
                    entry.amounts = _amounts(page_words, table.rows[row_idx].bbox, columns, scale)
                    for col, period in columns.periods.items():
                        periods_by_label.setdefault(period.label, period)
                    layouts.append(tuple(p.label for _, p in sorted(columns.periods.items())))
                    entries.append(entry)

    if year_from is None:
        raise GvfgParseError("Kein GVFG-Bundesprogramm erkannt (Titel „Bundesprogramm JJJJ - JJJJ“ fehlt).")
    if not entries:
        raise GvfgParseError("Im PDF wurden keine Vorhaben gefunden.")
    warnings.extend(_unify_periods(entries, layouts, periods_by_label))
    warnings.extend(_check_totals(entries, totals))
    warnings.extend(_check_lines(entries))
    warnings.extend(_check_duplicates(entries))
    periods = sorted(periods_by_label.values(), key=lambda p: (p.year_from or 0, p.kind != PERIOD_PAID))
    return ParseResult(
        title=title,
        year_from=year_from,
        year_to=year_to,
        stand=stand,
        is_annex=is_annex,
        periods=periods,
        entries=entries,
        totals=totals,
        warnings=warnings,
    )


def _page_words(page, scale: float) -> list[dict[str, Any]]:
    # Words of the whole page, not of a crop: crop() clips the characters of a
    # neighbouring row to the edge, which merges them with this row's numbers.
    return page.extract_words(keep_blank_chars=False, x_tolerance=1.5 * scale, y_tolerance=scale)


def _amounts(
    page_words: list[dict[str, Any]], row_bbox, columns: _Columns, scale: float
) -> list[AmountLine]:
    """Amount lines of one project row, numbers placed by the header spans."""
    x_left, top_edge, x_right, bottom_edge = row_bbox
    words = [
        w
        for w in page_words
        if top_edge <= (w["top"] + w["bottom"]) / 2 <= bottom_edge
        and x_left <= (w["x0"] + w["x1"]) / 2 <= x_right
    ]

    def column_of(word) -> int | None:
        center = (word["x0"] + word["x1"]) / 2
        for col, (x0, x1) in columns.spans.items():
            if x0 <= center <= x1:
                return col
        return None

    cat_col = columns.fields.index("category") if "category" in columns.fields else None
    marker_words = []
    number_words = []
    for word in words:
        col = column_of(word)
        # "∑" sometimes sits a little right of the category column.
        if word["text"] in ("∑", "Σ") and cat_col is not None:
            marker_words.append(word)
            continue
        if col is None:
            continue
        if col == cat_col:
            marker_words.append(word)
        elif columns.fields[col] in _AMOUNT_FIELDS or columns.fields[col] == "period":
            value = parse_decimal(word["text"])
            if value is not None:
                number_words.append((col, word["top"], value))

    lines: list[tuple[float, str]] = []
    for top, text in _group_lines(marker_words, scale):
        # "Kat: C" is a typo in the 2023 edition (09 G 7034_A).
        marker = re.sub(r"Kat\s*[.:]?", "", text).replace(" ", "")
        if marker in ("∑", "Σ"):
            lines.append((top, CATEGORY_SUM))
        elif marker in ("A", "B", "C"):
            lines.append((top, marker))
    single = not lines  # informational part: one amount line, no markers
    if single:
        lines = [(0.0, CATEGORY_SUM)]
    # One AmountLine per printed category line: an entry can carry two C lines
    # (e.g. announced extra costs), so lines are kept in print order.
    amounts = [AmountLine(category=category) for _, category in lines]
    for col, top, value in number_words:
        index = 0 if single else _assign(lines, top, scale)
        if index is None:
            continue
        line = amounts[index]
        name = columns.fields[col]
        if name == "period":
            line.periods[columns.periods[col].label] = value
        else:
            setattr(line, name, value)
    if amounts and all(a.category != CATEGORY_SUM for a in amounts):
        # Some 2023 pages print only the A/B/C lines; the ∑ line is their sum.
        amounts.insert(0, _sum_line(amounts))
    return amounts


def _same_column(printed: Period, expected: Period) -> bool:
    """Two labels for the same column: a paid span from 1967 that ends in another
    year, or the same single year paid / expected ("2022" vs "vsl. 2022")."""
    if printed.kind == expected.kind == PERIOD_PAID and printed.year_from == expected.year_from == 1967:
        return True
    paid = {PERIOD_PAID, PERIOD_PAID_EXPECTED}
    return (
        printed.year_to is not None
        and printed.year_from == printed.year_to == expected.year_from == expected.year_to
        and {printed.kind, expected.kind} <= paid
    )


def _unify_periods(
    entries: list[ParsedEntry], layouts: list[tuple[str, ...]], periods_by_label: dict[str, Period]
) -> list[str]:
    """Map typos in a table header onto the edition's columns.

    A few 2023 tables print "1967-2020" or "2022" where all others print
    "1967-2021" and "vsl. 2022". The layout of most entries is taken as the
    edition's; a deviating label at the same position is renamed when it can
    only mean the same column (``_same_column``). Each rename is a warning.
    """
    counts: dict[tuple[str, ...], int] = defaultdict(int)
    for layout in layouts:
        if layout:  # the informational part has no year columns
            counts[layout] += 1
    if not counts:
        return []
    reference = max(counts, key=lambda layout: counts[layout])  # first seen wins a tie
    aliases: dict[str, str] = {}
    for layout in counts:
        if layout == reference or len(layout) != len(reference):
            continue
        for printed, expected in zip(layout, reference):
            if printed == expected or printed in reference:
                continue
            if _same_column(periods_by_label[printed], periods_by_label[expected]):
                aliases[printed] = expected
    warnings = []
    for printed, expected in aliases.items():
        pages = sorted({e.page for e, layout in zip(entries, layouts) if printed in layout})
        warnings.append(
            f"S. {', '.join(map(str, pages))}: Spalte „{printed}“ als „{expected}“ gelesen "
            "(abweichender Tabellenkopf)."
        )
        del periods_by_label[printed]
    for entry in entries:
        for line in entry.amounts:
            if any(label in aliases for label in line.periods):
                line.periods = {aliases.get(label, label): value for label, value in line.periods.items()}
    return warnings


def _sum_line(parts: list[AmountLine]) -> AmountLine:
    total = AmountLine(category=CATEGORY_SUM, computed=True)
    for name in _AMOUNT_FIELDS:
        values = [getattr(p, name) for p in parts if getattr(p, name) is not None]
        setattr(total, name, sum(values, Decimal(0)) if values else None)
    for part in parts:
        for label, value in part.periods.items():
            total.periods[label] = total.periods.get(label, Decimal(0)) + value
    return total


def _group_lines(words, scale: float) -> list[tuple[float, str]]:
    lines: list[list[Any]] = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(lines[-1][0] - w["top"]) <= 1.5 * scale:
            lines[-1][1].append(w["text"])
        else:
            lines.append([w["top"], [w["text"]]])
    return [(top, " ".join(parts)) for top, parts in lines]


def _check_totals(entries: list[ParsedEntry], totals: list[ParsedTotal]) -> list[str]:
    sums: dict[tuple[str, str, str, str], list[Decimal]] = defaultdict(
        lambda: [Decimal(0), Decimal(0), Decimal(0)]
    )
    for entry in entries:
        for line in entry.amounts:
            bucket = sums[(entry.land, entry.kind, entry.part, line.category)]
            for i, name in enumerate(_AMOUNT_FIELDS):
                bucket[i] += getattr(line, name) or Decimal(0)
    warnings = []
    for total in totals:
        kind = total.kind or KIND_MUNICIPAL
        land = _canonical_land(total.land)
        got = sums.get((land, kind, total.part, total.category))
        expected = [total.cost_total, total.cost_eligible, total.aid_total]
        if got is None:
            warnings.append(
                f"S. {total.page}: Summenzeile {total.land}/{kind}/{total.category} "
                "ohne eingelesene Vorhaben."
            )
            continue
        for label, want, have in zip(("Gesamtkosten", "zwf. Kosten", "Finanzhilfen"), expected, got):
            # The PDF warns of rounding differences in its sums.
            if want is not None and abs(want - have) > Decimal("0.10"):
                category = "∑" if total.category == CATEGORY_SUM else f"Kat. {total.category}"
                warnings.append(
                    f"S. {total.page}: Summenzeile {total.land}, {kind}, {total.part}, {category}: "
                    f"{label} laut PDF {want}, Summe der Vorhaben {have} — bitte prüfen "
                    "(auch die Summenzeilen im PDF sind nicht immer vollständig)."
                )
    return warnings


def _check_lines(entries: list[ParsedEntry]) -> list[str]:
    """∑ line vs. the sum of its A/B/C lines, per entry."""
    warnings = []
    for entry in entries:
        total = next((a for a in entry.amounts if a.category == CATEGORY_SUM), None)
        parts = [a for a in entry.amounts if a.category != CATEGORY_SUM]
        if total is None or total.computed or not parts:
            continue
        for name, label in zip(_AMOUNT_FIELDS, ("Gesamtkosten", "zwf. Kosten", "Finanzhilfen")):
            want = getattr(total, name)
            have = sum((getattr(p, name) or Decimal(0) for p in parts), Decimal(0))
            if want is not None and abs(want - have) > Decimal("0.10"):
                warnings.append(
                    f"S. {entry.page}: {entry.key}: {label} ∑ {want}, Summe der Kategorien {have}."
                )
                break
    return warnings


def _check_duplicates(entries: list[ParsedEntry]) -> list[str]:
    seen: dict[tuple[str, str], int] = {}
    warnings = []
    for entry in entries:
        ref = (entry.key, entry.part)
        if ref in seen:
            warnings.append(f"S. {entry.page}: Schlüssel {entry.key} steht doppelt (auch S. {seen[ref]}).")
        else:
            seen[ref] = entry.page
    return warnings
