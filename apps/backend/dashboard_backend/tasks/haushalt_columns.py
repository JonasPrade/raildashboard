"""Stage 3 of the Haushalt import — mapping the PDF's columns onto the schema.

The Anlage VWIB, Teil B table carries the same sixteen logical columns every
year, but each report year shuffles the headings ("Vorhalten für 2027 ff." vs
"Vorbehalten für 2028 ff.", "Verausgabt bis 2024" vs "bis 2025").  Hard-coding
the indices ties the parser to one year; mapping the *headings* onto the
canonical fields once per document unties it.

Detection order (first that yields every required field wins):

1. ``detect_column_map`` — deterministic keyword match against the table's own
   header rows.  Covers every layout seen so far and needs no external service.
2. ``llm_column_map`` — one LLM call per document, only the header texts, never
   a value.  Handles a heading nobody anticipated.
3. ``LEGACY_COLUMN_MAP`` — the fixed 2026 layout, so a PDF whose header rows
   pdfplumber cannot recover still parses as it did before.

Values are always transferred deterministically through the resulting map: no
number ever passes through a model.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Canonical column order — also the fallback index of each field, because the
# 2026 report happens to list them in exactly this order.
CANONICAL_COLUMNS: tuple[str, ...] = (
    "lfd_nr",
    "finve_nr",
    "bedarfsplan",
    "name",
    "starting_year",
    "cost_original",
    "cost_last_year",
    "cost_actual",
    "delta_abs",
    "delta_rel",
    "delta_reasons",
    "spent_two_years_previous",
    "allowed_previous_year",
    "ausgabereste",
    "year_planned",
    "next_years",
)

LEGACY_COLUMN_MAP: dict[str, int] = {name: i for i, name in enumerate(CANONICAL_COLUMNS)}

# German labels for the review UI — the reviewer checks the mapping, not the
# field names of the Python schema.
COLUMN_LABELS: dict[str, str] = {
    "lfd_nr": "Lfd. Nr.",
    "finve_nr": "Nr. FinVe",
    "bedarfsplan": "Nr. Bedarfsplan Schiene",
    "name": "Bezeichnung der Investitionsmaßnahme",
    "starting_year": "Aufnahmejahr",
    "cost_original": "Gesamtausgaben ursprünglich",
    "cost_last_year": "Gesamtausgaben Vorjahr",
    "cost_actual": "Gesamtausgaben aktuell",
    "delta_abs": "Δ zum Vorjahr (€1.000)",
    "delta_rel": "Δ zum Vorjahr (%)",
    "delta_reasons": "Gründe",
    "spent_two_years_previous": "Verausgabt bis",
    "allowed_previous_year": "Bewilligt",
    "ausgabereste": "Übertragene Ausgabereste",
    "year_planned": "Veranschlagt",
    "next_years": "Vorbehalten für Folgejahre",
}

# Without these four the row-detection logic itself breaks, so an incomplete
# match on any of them sends the mapping on to the next detection stage.
REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {"lfd_nr", "name", "cost_actual", "year_planned"}
)

# Header patterns per field, strongest first.  They are matched against the
# whitespace-normalised, lower-cased concatenation of every header row cell in
# a column, so a pattern may rely on words from different header rows.
_HEADER_PATTERNS: dict[str, tuple[str, ...]] = {
    "lfd_nr": (r"\blfd\b",),
    "finve_nr": (r"\bnr\.?\s*finve\b", r"\bfinve[- ]?nr\b"),
    "bedarfsplan": (r"\bbedarfsplan\b",),
    "name": (r"\bbezeichnung\b", r"\bma(ß|ss)nahme\b"),
    "starting_year": (r"\baufnahme\b", r"^jahr$"),
    "cost_original": (r"\burspr(ü|ue)nglich\b",),
    # "Vorjahr" alone is the previous year's total; "zum Vorjahr" is the delta
    # column — anchor the strong pattern so the two never swap.
    "cost_last_year": (r"(?<!zum )\bvorjahr\b",),
    "cost_actual": (r"\baktuell\b",),
    "delta_abs": (r"\bzum vorjahr\b", r"\bver(ä|ae)nderung\b"),
    "delta_rel": (r"^%$", r"(?:^|\s)%(?:\s|$)"),
    "delta_reasons": (r"\bgr(ü|ue)nde\b",),
    "spent_two_years_previous": (r"\bverausgabt\b",),
    "allowed_previous_year": (r"\bbewilligt\b",),
    "ausgabereste": (r"\bausgabereste\b",),
    "year_planned": (r"\bveranschlagt\b",),
    "next_years": (r"\bvor(be)?halten\b",),
}

_COMPILED_PATTERNS: dict[str, tuple[re.Pattern, ...]] = {
    field_name: tuple(re.compile(p, re.IGNORECASE) for p in patterns)
    for field_name, patterns in _HEADER_PATTERNS.items()
}

# Words that only ever appear in a header row of this table.  Two hits make a
# row a header row — data rows carry project names and numbers instead.
_HEADER_KEYWORDS: tuple[str, ...] = (
    "lfd",
    "finve",
    "bedarfsplan",
    "bezeichnung",
    "aufnahme",
    "ursprünglich",
    "gesamtausgaben",
    "verausgabt",
    "bewilligt",
    "ausgabereste",
    "veranschlagt",
    "gründe",
)


def normalize_header(value: str | None) -> str:
    """Lower-case, collapse whitespace — the form the patterns match against."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().lower()


def is_column_number_row(cells: list) -> bool:
    """True for the "1 | 2 | 3 | …" row printed under the headings."""
    numbers = [str(c).strip() for c in cells if c is not None and str(c).strip()]
    if len(numbers) < 4:
        return False
    if not all(n.isdigit() for n in numbers):
        return False
    return [int(n) for n in numbers] == list(range(1, len(numbers) + 1))


# The unit row under the headings ("Jahr | €1.000 | % | …") carries no
# keyword, but it is what tells "%" (the relative delta) from "€1.000".
_UNIT_CELL_RE = re.compile(r"^(?:€\s?1\.000|%|jahr|t€|mio\.?\s?€)$", re.IGNORECASE)


def is_unit_row(cells: list) -> bool:
    """True for the row that gives each column's unit rather than its name."""
    values = [normalize_header(c) for c in cells if c is not None and str(c).strip()]
    return bool(values) and all(_UNIT_CELL_RE.match(v) for v in values)


def is_header_row(cells: list) -> bool:
    """True for one of the repeated heading rows at the top of every page."""
    if is_column_number_row(cells) or is_unit_row(cells):
        return True
    joined = normalize_header(" ".join(str(c) for c in cells if c))
    if not joined:
        return False
    return sum(1 for keyword in _HEADER_KEYWORDS if keyword in joined) >= 2


@dataclass(frozen=True)
class ColumnMap:
    """Which table column carries which canonical field, and how we know."""

    indices: dict[str, int]
    headers: dict[str, str] = field(default_factory=dict)
    source: str = "fallback"  # "header" | "llm" | "fallback"

    def index(self, field_name: str) -> int | None:
        return self.indices.get(field_name)

    @property
    def missing(self) -> list[str]:
        """Canonical fields this document has no column for."""
        return [name for name in CANONICAL_COLUMNS if name not in self.indices]

    @property
    def is_complete(self) -> bool:
        return REQUIRED_COLUMNS.issubset(self.indices)

    def to_json(self) -> dict:
        """Serialisable form for the parse result and the review UI."""
        return {
            "source": self.source,
            "columns": [
                {
                    "field": name,
                    "label": COLUMN_LABELS[name],
                    "index": self.indices.get(name),
                    "header": self.headers.get(name),
                }
                for name in CANONICAL_COLUMNS
            ],
            "missing": self.missing,
        }


def column_header_texts(header_rows: list[list]) -> list[str]:
    """Per column, the normalised concatenation of all its header row cells."""
    width = max((len(row) for row in header_rows), default=0)
    texts: list[str] = []
    for col in range(width):
        parts = []
        for row in header_rows:
            if is_column_number_row(row):
                continue
            if col < len(row) and row[col]:
                parts.append(str(row[col]))
        texts.append(normalize_header(" ".join(parts)))
    return texts


def detect_column_map(header_rows: list[list]) -> ColumnMap:
    """Match the table's own headings against the canonical fields.

    Every (field, column) pair that matches scores by pattern priority; the
    pairs are then assigned greedily, strongest first, so an ambiguous heading
    goes to the field whose match is the more specific one.
    """
    texts = column_header_texts(header_rows)
    if not texts:
        return ColumnMap(indices={}, headers={}, source="header")

    candidates: list[tuple[int, str, int]] = []
    for field_name, patterns in _COMPILED_PATTERNS.items():
        for priority, pattern in enumerate(patterns):
            score = len(patterns) - priority
            for col, text in enumerate(texts):
                if text and pattern.search(text):
                    candidates.append((score, field_name, col))

    candidates.sort(key=lambda c: (-c[0], c[1], c[2]))

    indices: dict[str, int] = {}
    headers: dict[str, str] = {}
    used_columns: set[int] = set()
    for _score, field_name, col in candidates:
        if field_name in indices or col in used_columns:
            continue
        indices[field_name] = col
        headers[field_name] = texts[col]
        used_columns.add(col)

    return ColumnMap(indices=indices, headers=headers, source="header")


_LLM_SYSTEM_PROMPT = """Du ordnest Spaltenüberschriften einer Haushaltstabelle \
(Anlage VWIB, Teil B, Bundeshaushalt) den festen Zielfeldern zu.

Antworte ausschließlich mit JSON der Form
{"columns": {"<zielfeld>": <spaltenindex>, ...}}.

Zielfelder und ihre Bedeutung:
- lfd_nr: Laufende Nummer der Zeile (z. B. "B0080")
- finve_nr: Nummer der Finanzierungsvereinbarung
- bedarfsplan: Nummer im Bedarfsplan Schiene
- name: Bezeichnung der Investitionsmaßnahme
- starting_year: Jahr der Aufnahme in den Einzelplan
- cost_original: voraussichtliche Gesamtausgaben, ursprünglich
- cost_last_year: voraussichtliche Gesamtausgaben, Vorjahr
- cost_actual: voraussichtliche Gesamtausgaben, aktuell
- delta_abs: Veränderung zum Vorjahr in €1.000
- delta_rel: Veränderung zum Vorjahr in Prozent
- delta_reasons: Gründe der Veränderung
- spent_two_years_previous: bereits verausgabte Ausgaben
- allowed_previous_year: bewilligte Ausgaben des laufenden Jahres
- ausgabereste: übertragene Ausgabereste
- year_planned: für das Haushaltsjahr veranschlagte Ausgaben
- next_years: für die Folgejahre vorbehaltene Ausgaben

Nutze jeden Spaltenindex höchstens einmal. Lass ein Zielfeld weg, wenn die \
Tabelle keine passende Spalte hat. Gib keine Werte und keinen Fließtext aus."""


def llm_column_map(header_rows: list[list]) -> ColumnMap | None:
    """Ask the configured LLM to map the headings. Returns None when unusable.

    One call per document, headers only.  Best-effort like every other LLM step
    in the importers: any failure falls through to the caller's next option.
    """
    from dashboard_backend.core.config import settings

    if not settings.llm_base_url:
        return None

    texts = column_header_texts(header_rows)
    if not any(texts):
        return None

    from dashboard_backend.services.llm import call_llm_json, summarise_error

    prompt = "Spaltenüberschriften:\n" + "\n".join(
        f"{i}: {text or '(leer)'}" for i, text in enumerate(texts)
    )
    try:
        raw = call_llm_json(_LLM_SYSTEM_PROMPT, prompt)
    except Exception as exc:  # best-effort — the fallback map still parses
        logger.warning("Haushalt column mapping via LLM failed: %s", summarise_error(exc))
        return None

    columns = raw.get("columns") if isinstance(raw, dict) else None
    if not isinstance(columns, dict):
        logger.warning("Haushalt column mapping via LLM returned no 'columns' object")
        return None

    indices: dict[str, int] = {}
    headers: dict[str, str] = {}
    used_columns: set[int] = set()
    for field_name in CANONICAL_COLUMNS:
        value = columns.get(field_name)
        if not isinstance(value, int) or isinstance(value, bool):
            continue
        if not 0 <= value < len(texts) or value in used_columns:
            continue
        indices[field_name] = value
        headers[field_name] = texts[value]
        used_columns.add(value)

    if not indices:
        return None
    return ColumnMap(indices=indices, headers=headers, source="llm")


def resolve_column_map(header_rows: list[list]) -> ColumnMap:
    """The map the parser transfers values through: header → LLM → legacy."""
    detected = detect_column_map(header_rows)
    if detected.is_complete:
        logger.info(
            "Haushalt column map from table header: %d of %d fields mapped",
            len(detected.indices), len(CANONICAL_COLUMNS),
        )
        return detected

    logger.warning(
        "Haushalt header detection incomplete (missing %s) — trying LLM mapping",
        sorted(REQUIRED_COLUMNS - set(detected.indices)),
    )
    from_llm = llm_column_map(header_rows)
    if from_llm is not None and from_llm.is_complete:
        logger.info("Haushalt column map from LLM: %d fields mapped", len(from_llm.indices))
        return from_llm

    logger.warning("Haushalt column map falling back to the fixed 2026 layout")
    return ColumnMap(
        indices=dict(LEGACY_COLUMN_MAP),
        headers=dict(zip(CANONICAL_COLUMNS, column_header_texts(header_rows))),
        source="fallback",
    )
