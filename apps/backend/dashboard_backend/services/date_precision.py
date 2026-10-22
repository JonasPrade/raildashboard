"""Date qualification of planning-state dates (pure, no DB).

A stored date is only the technical sort value; :class:`DatePrecision` says
how much of it is known. Everything that shows a date to a person goes through
:func:`format_date` / :func:`date_text`, so a year-only or lower-bound date
never reads like a published day. See docs/features/feature-project-progress.md
→ „Datumsqualifikation“.
"""

from __future__ import annotations

import calendar
from datetime import date

from dashboard_backend.models.projects.progress_enums import DatePrecision


def as_precision(value: DatePrecision | str | None) -> DatePrecision:
    """Tolerant conversion; unknown or missing values count as EXACT."""

    if isinstance(value, DatePrecision):
        return value
    try:
        return DatePrecision(value) if value else DatePrecision.EXACT
    except ValueError:
        return DatePrecision.EXACT


def normalize_sort_date(value: date | None, precision: DatePrecision | str | None) -> date | None:
    """Sort value of a coarse date: MONTH → 1st of the month, YEAR → 1 Jan.
    EXACT, NOT_BEFORE (the lower bound) and ASSUMED keep their day."""

    if value is None:
        return None
    precision = as_precision(precision)
    if precision is DatePrecision.MONTH:
        return value.replace(day=1)
    if precision is DatePrecision.YEAR:
        return value.replace(month=1, day=1)
    return value


def format_date(value: date | None, precision: DatePrecision | str | None) -> str | None:
    """German display text of a date at its precision.

    EXACT 06.02.2026 · MONTH 02/2027 · YEAR 2028 · NOT_BEFORE „nach 2031“ for
    a bound on 1 Jan (else „frühestens 07/2032“) · ASSUMED „ca. 07/2028
    (Annahme)“.
    """

    if value is None:
        return None
    precision = as_precision(precision)
    if precision is DatePrecision.MONTH:
        return value.strftime("%m/%Y")
    if precision is DatePrecision.YEAR:
        return str(value.year)
    if precision is DatePrecision.NOT_BEFORE:
        if value.month == 1 and value.day == 1:
            return f"nach {value.year - 1}"
        return f"frühestens {value.strftime('%m/%Y')}"
    if precision is DatePrecision.ASSUMED:
        return f"ca. {value.strftime('%m/%Y')} (Annahme)"
    return value.strftime("%d.%m.%Y")


def date_text(
    value: date | None, precision: DatePrecision | str | None, label: str | None = None
) -> str | None:
    """:func:`format_date` plus the optional free-text label („nach 2031 –
    Priorisierung 2027 offen“). A label without a date stands alone."""

    base = format_date(value, precision)
    label = (label or "").strip() or None
    if base and label:
        return f"{base} – {label}"
    return base or label


def derived_precision(base: DatePrecision | str | None) -> DatePrecision:
    """Precision of a date computed from ``base`` by a rule (e.g. Baubeginn +
    6 months): a lower bound stays a lower bound, anything else is an
    assumption."""

    return (
        DatePrecision.NOT_BEFORE
        if as_precision(base) is DatePrecision.NOT_BEFORE
        else DatePrecision.ASSUMED
    )


def add_months(value: date, months: int) -> date:
    """``value`` shifted by whole months (day clamped to the month length)."""

    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def covered_period(value: date, precision: DatePrecision | str | None) -> tuple[date, date] | None:
    """The days a date may stand for, or None for an open lower bound.

    YEAR → the whole year, MONTH → the whole month, EXACT / ASSUMED → the day
    itself, NOT_BEFORE → None (no point in time at all).
    """

    precision = as_precision(precision)
    if precision is DatePrecision.NOT_BEFORE:
        return None
    if precision is DatePrecision.YEAR:
        return date(value.year, 1, 1), date(value.year, 12, 31)
    if precision is DatePrecision.MONTH:
        last = calendar.monthrange(value.year, value.month)[1]
        return value.replace(day=1), value.replace(day=last)
    return value, value


def in_period(
    value: date | None,
    precision: DatePrecision | str | None,
    start: date | None,
    end: date | None,
) -> bool:
    """Whether a qualified date falls into the filter period [start, end].

    A NOT_BEFORE date never counts as a hit (it is not a date); a YEAR or
    MONTH date counts when its period overlaps the filter. Open filter ends
    are unbounded.
    """

    if value is None:
        return False
    period = covered_period(value, precision)
    if period is None:
        return False
    first, last = period
    if start is not None and last < start:
        return False
    if end is not None and first > end:
        return False
    return True
