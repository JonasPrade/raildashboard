"""Tolerant parsing of the free-text date fields found in VIB / PFA data.

VIB date fields (``baubeginn``, ``inbetriebnahme``, ``datum_pfb``) are free text
and wildly inconsistent: ``"12/2024"``, ``"2024"``, ``"2. Quartal 2025"``,
``"Mitte 2026"``, ``"voraussichtlich Ende 2027"``, ``"01.03.2024"``, ``"-"`` …

``parse_flexible_date`` returns a best-effort :class:`datetime.date` (always with
a concrete day so it can drive recency decay and forecasting), or ``None`` when
nothing date-like is present. Granularity coarser than a day is normalised to a
representative day within the period (mid-month, mid-quarter, mid-year).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from dashboard_backend.models.projects.progress_enums import DatePrecision

_MONTHS = {
    "januar": 1, "jan": 1,
    "februar": 2, "feb": 2,
    "märz": 3, "maerz": 3, "mrz": 3, "mär": 3,
    "april": 4, "apr": 4,
    "mai": 5,
    "juni": 6, "jun": 6,
    "juli": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "okt": 10,
    "november": 11, "nov": 11,
    "dezember": 12, "dez": 12,
}

# Quarter → representative (mid-quarter) month.
_QUARTER_MONTH = {1: 2, 2: 5, 3: 8, 4: 11}

# Coarse keywords → representative month within a year.
_KEYWORD_MONTH = {
    "anfang": 2,
    "frühjahr": 4, "fruehjahr": 4, "frühling": 4, "fruehling": 4,
    "mitte": 7,
    "sommer": 7,
    "herbst": 10,
    "ende": 12,
    "winter": 12,
}

_NULL_TOKENS = {"", "-", "–", "—", "‐", "‑", "n/a", "offen", "unbekannt", "k.a.", "k. a."}


def _safe_date(year: int, month: int, day: int) -> date | None:
    if not (1900 <= year <= 2100) or not (1 <= month <= 12):
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_flexible_date(text: str | None) -> date | None:
    """Best-effort parse of a free-text German date. Returns ``None`` if unparseable."""

    return _parse(text)[0]


# "nach 2031", "ab 2032", "frühestens 2032", "nicht vor 2032", ">2031".
_NOT_BEFORE = re.compile(
    r"(?:\b(nach|ab|frühestens|fruehestens|nicht\s+vor)\s+|>\s*)(\d{4})\b"
)


def parse_flexible_date_with_precision(text: str | None) -> tuple[date | None, DatePrecision]:
    """:func:`parse_flexible_date` plus how precisely the text names the date.

    Full dates are EXACT, month/year MONTH; quarters, coarse keywords and bare
    years are YEAR (their representative day stays the sort value). A lower
    bound („nach 2031“, „ab 2032“, „>2031“) is NOT_BEFORE with the first day
    it allows (2032-01-01) — unlike :func:`parse_flexible_date`, which reads
    it as the year itself.
    """

    if text is not None and not re.search(r"\d{1,2}[./]\d{1,2}[./]\d{4}|\d{4}-\d", text):
        m = _NOT_BEFORE.search(text.lower())
        if m:
            year = int(m.group(2))
            bound = _safe_date(year + 1 if m.group(1) in (None, "nach") else year, 1, 1)
            if bound is not None:
                return bound, DatePrecision.NOT_BEFORE
    return _parse(text)


_EXACT, _MONTH, _YEAR = DatePrecision.EXACT, DatePrecision.MONTH, DatePrecision.YEAR
# Representative day of a bare year ("2028") — mid-year.
_BARE_YEAR = (7, 1)


def commissioning_in_year(year: int) -> tuple[date, DatePrecision]:
    """A commissioning known only by its year: the timetable change
    (Fahrplanwechsel, early December) unless something else is known —
    shown as 12/YYYY, sort value 31 Dec (the latest point of the year)."""

    return date(year, 12, 31), DatePrecision.MONTH


def parse_commissioning_with_precision(text: str | None) -> tuple[date | None, DatePrecision]:
    """:func:`parse_flexible_date_with_precision` for an Inbetriebnahme: a bare
    year („2028“, „voraussichtlich 2028“) becomes the Fahrplanwechsel 12/2028
    (:func:`commissioning_in_year`). Quarters and keywords („Mitte 2028“) say
    more about the time of year and stay as they are."""

    value, precision = parse_flexible_date_with_precision(text)
    if value is not None and precision is _YEAR and (value.month, value.day) == _BARE_YEAR:
        return commissioning_in_year(value.year)
    return value, precision


# Hedges that make a VIB date a prognosis rather than a fact, as printed in
# the PFA tables: „vsl. 2027“, „vsl 2035“, „vsl.2026“, „offen vsl. 2028“,
# „voraussichtlich Ende 2027“, „ca. 2026“, „geplant 2029“, „ab/nach 2031“,
# „frühestens 07/2032“, „bis 2025“, „>2031“.
_TENTATIVE = re.compile(
    r"\b(?:vsl|vorauss\w*|geplant\w*|prognos\w*|ca|circa|etwa|"
    r"ab|nach|bis|frühestens|fruehestens|spätestens|spaetestens|nicht\s+vor|"
    r"angestrebt|avisiert|offen)\b|[>~]"
)
# A milestone reported as reached without a date („erfolgt“, „erfolgte“).
_DONE = re.compile(r"\berfolgt")
# Footnote markers glued to a cell („2002¹“, „offen²“).
_FOOTNOTES = str.maketrans("", "", "¹²³⁴⁵⁶⁷⁸⁹⁰")


@dataclass(frozen=True)
class Milestone:
    """A VIB milestone cell read as fact or prognosis.

    ``is_expected`` is True for a hedged date („vsl. 2027“) and for any date
    after the report's ``as_of`` day. ``value`` is None for a fact without a
    date („erfolgt“).
    """

    value: date | None
    precision: DatePrecision
    is_expected: bool


def read_milestone(
    text: str | None, as_of: date | None, *, commissioning: bool = False
) -> Milestone | None:
    """Read a PFA milestone cell (``datum_pfb``, ``baubeginn``,
    ``inbetriebnahme``) as of the report's ``as_of`` day.

    Returns None when the cell states nothing („offen“, „-“, no date). A
    hedge word or a date after ``as_of`` makes it a prognosis; a period that
    contains ``as_of`` („12/2024“ in the VIB 2024) has its representative day
    on or before it and counts as reached. ``commissioning`` reads a bare year
    as the Fahrplanwechsel (:func:`parse_commissioning_with_precision`).
    """

    if text is None:
        return None
    text = text.translate(_FOOTNOTES)
    parse = parse_commissioning_with_precision if commissioning else parse_flexible_date_with_precision
    value, precision = parse(text)
    lowered = text.lower()
    tentative = bool(_TENTATIVE.search(lowered))
    if value is None:
        if _DONE.search(lowered) and not tentative:
            return Milestone(None, _EXACT, False)
        return None
    expected = (
        tentative
        or precision is DatePrecision.NOT_BEFORE
        or (as_of is not None and value > as_of)
    )
    return Milestone(value, precision, expected)


def _parse(text: str | None) -> tuple[date | None, DatePrecision]:
    if text is None:
        return None, _EXACT
    raw = text.strip()
    if raw.lower() in _NULL_TOKENS:
        return None, _EXACT

    lowered = raw.lower()

    # 1) Full ISO date: 2024-03-15
    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", lowered)
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3))), _EXACT

    # 2) German full date: 01.03.2024 / 1.3.2024
    m = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b", lowered)
    if m:
        return _safe_date(int(m.group(3)), int(m.group(2)), int(m.group(1))), _EXACT

    # 3) Quarter: "Q2 2025", "2. Quartal 2025", "II/2025"
    m = re.search(r"\b([1-4])\s*\.?\s*quartal\b.*?(\d{4})", lowered) or re.search(
        r"\bq\s*([1-4])\b.*?(\d{4})", lowered
    )
    if m:
        return _safe_date(int(m.group(2)), _QUARTER_MONTH[int(m.group(1))], 15), _YEAR
    m = re.search(r"\b(i{1,3}v?|iv)\s*/\s*(\d{4})\b", lowered)
    if m:
        roman = {"i": 1, "ii": 2, "iii": 3, "iv": 4}.get(m.group(1))
        if roman:
            return _safe_date(int(m.group(2)), _QUARTER_MONTH[roman], 15), _YEAR

    # 4) month/year or month.year: "12/2024", "03.2024"
    m = re.search(r"\b(\d{1,2})[/.](\d{4})\b", lowered)
    if m and 1 <= int(m.group(1)) <= 12:
        return _safe_date(int(m.group(2)), int(m.group(1)), 15), _MONTH

    # 5) German month name + year: "März 2024"
    for name, month in _MONTHS.items():
        if re.search(rf"\b{name}\b", lowered):
            ym = re.search(r"\b(\d{4})\b", lowered)
            if ym:
                return _safe_date(int(ym.group(1)), month, 15), _MONTH

    # 6) Coarse keyword + year: "Mitte 2026", "Ende 2027"
    for keyword, month in _KEYWORD_MONTH.items():
        if keyword in lowered:
            ym = re.search(r"\b(\d{4})\b", lowered)
            if ym:
                return _safe_date(int(ym.group(1)), month, 15), _YEAR

    # 7) Bare year (also catches "voraussichtlich 2025", "ca. 2026", ">2024").
    #    For a range like "2024-2026" take the earliest year mentioned.
    years = re.findall(r"\b(20\d{2}|19\d{2})\b", lowered)
    if years:
        return _safe_date(int(min(years)), *_BARE_YEAR), _YEAR

    return None, _EXACT
