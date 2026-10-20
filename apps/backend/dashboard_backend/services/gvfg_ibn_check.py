"""Does the GVFG-Finanzreihe still fund a project after its known commissioning?

Pure check (feature-project-progress.md → „IBN-Plausibilität aus der
GVFG-Finanzreihe“): if the ∑ line of the newest GVFG edition plans a relevant
part of the Bundesfinanzhilfen for years after the known Inbetriebnahme, that
year is doubtful. The check never changes the forecast; it only flags it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

# Final payments (Schlussrechnung) often follow the commissioning by a year or
# two; only a substantial remainder questions the date.
RELEVANT_MIN_AID = Decimal("1")  # Mio. €
RELEVANT_SHARE = Decimal("0.15")  # of the aid in all year columns


@dataclass(frozen=True)
class IbnDoubt:
    ibn_year: int
    ibn_source: str
    edition: str
    aid_after: Decimal  # Mio. €, in year columns starting after ibn_year
    aid_total: Decimal  # Mio. €, all year columns
    periods: list[tuple[str, Decimal]] = field(default_factory=list)  # label → aid after ibn_year


def check_ibn_against_gvfg(
    ibn_year: int,
    ibn_source: str,
    edition: str,
    program_periods: list[dict],
    amounts: dict[str, Decimal],
) -> IbnDoubt | None:
    """``program_periods`` as stored on the edition (label, year_from, …),
    ``amounts`` the ∑-line aid per period label. A column counts as "after"
    only if it starts after ``ibn_year`` — "ab 2030" is not after 2030."""
    total = Decimal(0)
    after = Decimal(0)
    periods: list[tuple[str, Decimal]] = []
    for period in program_periods:
        amount = amounts.get(period.get("label"))
        if not amount or amount <= 0:
            continue
        total += amount
        year_from = period.get("year_from")
        if year_from is not None and year_from > ibn_year:
            after += amount
            periods.append((period["label"], amount))
    if after < RELEVANT_MIN_AID or after < RELEVANT_SHARE * total:
        return None
    return IbnDoubt(
        ibn_year=ibn_year,
        ibn_source=ibn_source,
        edition=edition,
        aid_after=after,
        aid_total=total,
        periods=periods,
    )
