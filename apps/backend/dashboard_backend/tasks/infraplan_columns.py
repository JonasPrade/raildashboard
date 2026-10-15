"""Stage 3 of the Infraplan import — headers onto fields, cells onto values.

The measure tables of the Infraplan (chapter 2.3) come in three layouts:
Bedarfsplan (eight columns incl. "Bezeichnung" and "Parlamentarische
Befassung"), GVFG (six columns, cost column "Gesamtkosten") and InvKG (six
columns, cost column "GWU").  The column order differs between them, so every
header is mapped onto the canonical fields by its own wording — the same idea
as ``haushalt_columns``, without an LLM stage: an unknown heading is an error
the parser reports instead of a guess.

The value normalisers (German numbers, Inbetriebnahme, Lph, Befassung,
project numbers, GVFG keys) live here as well, so the parser only segments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# The GVFG key normaliser is shared with the GVFG import, so a key from the
# Infraplan matches the key the GVFG import stored on the project.
from dashboard_backend.services.gvfg_parser import normalize_key as normalize_gvfg_key

# ---------------------------------------------------------------------------
# Header → canonical field
# ---------------------------------------------------------------------------

CANONICAL_FIELDS: tuple[str, ...] = (
    "lfd_projekt",  # "Laufende Nummer | Projektnummer"
    "bezeichnung",
    "massnahme",
    "land",
    "state",  # "Realisierungsstand / Lph"
    "ibn",  # "Geplante (oder tatsächliche) Inbetriebnahme"
    "cost",  # "GWU in Mio. €" / "Gesamtkosten in Mio. €"
    "parl",  # "Parlamentarische Befassung"
)

REQUIRED_FIELDS: frozenset[str] = frozenset({"lfd_projekt", "massnahme", "cost"})

# First match wins, so the more specific patterns come first ("Projektnummer"
# also contains "nummer", "Realisierungsstand" must not fall to "land").
_HEADER_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("lfd_projekt", re.compile(r"nummer", re.IGNORECASE)),
    ("state", re.compile(r"realisierung|\blph\b", re.IGNORECASE)),
    ("ibn", re.compile(r"inbetrieb", re.IGNORECASE)),
    ("cost", re.compile(r"\bgwu\b|gesamtkosten", re.IGNORECASE)),
    ("parl", re.compile(r"befassung", re.IGNORECASE)),
    ("bezeichnung", re.compile(r"bezeichnung", re.IGNORECASE)),
    ("massnahme", re.compile(r"ma(ß|ss)nahme", re.IGNORECASE)),
    ("land", re.compile(r"^land$", re.IGNORECASE)),
)


class UnknownColumnError(ValueError):
    """A table header the parser does not know — the layout has changed."""


@dataclass(frozen=True)
class ColumnLayout:
    """Column boundaries of one table header and the field of each column.

    ``edges`` are the left x-coordinates of the columns (ascending); a word
    belongs to the last column whose edge lies left of it.
    """

    edges: tuple[float, ...]
    fields: tuple[str, ...]
    cost_kind: str  # "GWU" | "GESAMTKOSTEN"

    def column_of(self, x0: float) -> int:
        idx = 0
        for i, edge in enumerate(self.edges):
            if x0 + 1.0 >= edge:
                idx = i
        return idx

    def to_dict(self) -> dict:
        return {
            "edges": [round(e, 1) for e in self.edges],
            "fields": list(self.fields),
            "cost_kind": self.cost_kind,
        }


def field_for_header(header_text: str) -> str | None:
    text = " ".join(header_text.split())
    for name, pattern in _HEADER_PATTERNS:
        if pattern.search(text):
            return name
    return None


def resolve_layout(edges: list[float], header_texts: list[str]) -> ColumnLayout:
    """Map the header cell texts of one table onto the canonical fields.

    Raises :class:`UnknownColumnError` for a heading no pattern knows, a
    field that appears twice or a required field that is missing.
    """
    fields: list[str] = []
    for text in header_texts:
        name = field_for_header(text)
        if name is None:
            raise UnknownColumnError(f"Unbekannte Spalte im Infraplan: {text!r}")
        if name in fields:
            raise UnknownColumnError(f"Spalte doppelt erkannt: {text!r} ({name})")
        fields.append(name)
    missing = REQUIRED_FIELDS - set(fields)
    if missing:
        raise UnknownColumnError(f"Pflichtspalten fehlen: {', '.join(sorted(missing))}")
    cost_header = header_texts[fields.index("cost")]
    cost_kind = "GESAMTKOSTEN" if "gesamtkosten" in cost_header.lower() else "GWU"
    return ColumnLayout(edges=tuple(edges), fields=tuple(fields), cost_kind=cost_kind)


# ---------------------------------------------------------------------------
# Value normalisers
# ---------------------------------------------------------------------------

_GERMAN_NUMBER_RE = re.compile(r"^\d{1,3}(?:\.\d{3})*(?:,\d+)?$|^\d+(?:,\d+)?$")


def parse_german_number(text: str | None) -> float | None:
    """``1.720,48`` → 1720.48; anything else → None."""
    if not text:
        return None
    value = text.strip()
    if not _GERMAN_NUMBER_RE.match(value):
        return None
    return float(value.replace(".", "").replace(",", "."))


# "Ref. Teil B 20 | E.1637290100" — the cost is carried by another entry.
_COST_REF_RE = re.compile(r"Ref\.?\s*Teil\s*([A-D])\s*(\d+)", re.IGNORECASE)


def parse_cost_ref(text: str | None) -> tuple[str, int] | None:
    """Target (section, lfd_nr) of a cost reference, or None."""
    if not text:
        return None
    match = _COST_REF_RE.search(text)
    if not match:
        return None
    return f"BP_{match.group(1).upper()}", int(match.group(2))


_YEAR_RE = re.compile(r"(?<!\d)(\d{4})(?!\d)")


def parse_ibn(text: str | None) -> tuple[int | None, str | None]:
    """Normalise the Inbetriebnahme cell to ``(year, qualifier)``.

    ``2030`` → (2030, None); ``offen`` → (None, "OFFEN"); ``bis 2035`` →
    (2035, "BIS"); ``2029/2030`` or ``2022–2029`` → (2030, "SPANNE") — the
    later year counts.  Other text ("mehrere") → (None, None), the raw text
    stays on the entry.
    """
    if not text:
        return None, None
    value = " ".join(text.split())
    if value.lower().startswith("offen"):
        return None, "OFFEN"
    years = [int(y) for y in _YEAR_RE.findall(value)]
    if not years:
        return None, None
    if value.lower().startswith("bis"):
        return max(years), "BIS"
    if len(years) > 1:
        return max(years), "SPANNE"
    return years[0], None


_LPH_RE = re.compile(r"Lph\.?\s*(\d)(?:\s*(?:-|–|/)\s*(\d))?", re.IGNORECASE)


@dataclass(frozen=True)
class StateInfo:
    lph_from: int | None
    lph_to: int | None
    under_construction: bool
    baurecht: bool


def parse_state(text: str | None) -> StateInfo:
    """``Bau`` / ``Lph 4 abgeschlossen – durchgängiges Baurecht`` / ``Lph 3-4`` …"""
    value = " ".join((text or "").split())
    under_construction = value.lower().startswith("bau")
    baurecht = "baurecht" in value.lower()
    lph_from = lph_to = None
    match = _LPH_RE.search(value)
    if match:
        lph_from = int(match.group(1))
        lph_to = int(match.group(2)) if match.group(2) else lph_from
    return StateInfo(lph_from, lph_to, under_construction, baurecht)


def parse_parl(text: str | None) -> str | None:
    """Befassung cell → ``ABGESCHLOSSEN`` | ``LAEUFT`` | ``VORGESEHEN`` | ``NICHT_VEREINBART``."""
    value = " ".join((text or "").split()).lower()
    if not value:
        return None
    if value.startswith("nicht vereinbart"):
        return "NICHT_VEREINBART"
    if value.startswith("abgeschlossen"):
        return "ABGESCHLOSSEN"
    if "verfahren läuft" in value or "übergabe" in value:
        return "LAEUFT"
    if value.startswith("vorgesehen"):
        return "VORGESEHEN"
    return None


# ---------------------------------------------------------------------------
# Project numbers
# ---------------------------------------------------------------------------

_DB_NUMBER_RE = re.compile(r"\b[A-Z]\.\d{6,}\b")
_INVKG_NUMBER_RE = re.compile(r"^(\d{1,3})\)")


def parse_project_numbers(text: str | None, section: str) -> list[str]:
    """Project numbers of the first column after ``lfd_nr |``.

    Bedarfsplan: ``E.1637230040 // X.016030472300201`` (``/`` = none);
    GVFG: the normalised key (``07 D 2825_A``); InvKG: ``InvKG Nr. 6`` from ``6)``.
    """
    value = " ".join((text or "").split())
    if section.startswith("GVFG"):
        key = normalize_gvfg_key(value)
        return [key] if key else []
    if section == "INVKG":
        match = _INVKG_NUMBER_RE.match(value)
        return [f"InvKG Nr. {match.group(1)}"] if match else []
    return _DB_NUMBER_RE.findall(value)
