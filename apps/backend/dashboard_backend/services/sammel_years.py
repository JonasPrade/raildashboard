"""Year-by-year listing of a Sammelfinanzierungsvereinbarung (SV-FinVe).

A Sammel-FinVe is concluded once (``Finve.starting_year``) but its project list
is rewritten with every Haushalt edition: projects enter (Leistungsphase starts),
stay, or drop out (typically moved on to the next Leistungsphase). The year
links (``finve_to_project.haushalt_year``) record which projects an edition
lists. These helpers turn them into per-edition diffs and into the „listed
since“ wording — the conclusion year says nothing about when a single project
was added (docs/features/feature-haushalt-import.md → „Jahresvergleich“).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SammelYearDiff:
    """One Haushalt edition compared with the previous one.

    ``previous_year`` is ``None`` for the earliest edition known: everything it
    lists is ``kept`` (unknown whether it is new), nothing is ``added``."""

    year: int
    previous_year: int | None
    added: list[int] = field(default_factory=list)
    kept: list[int] = field(default_factory=list)
    removed: list[int] = field(default_factory=list)


def sammel_year_diffs(
    edition_years: set[int] | list[int], links: dict[int, set[int]]
) -> list[SammelYearDiff]:
    """Diff each Haushalt edition against the previous one, oldest first.

    ``edition_years`` are the editions that carry the FinVe (budget years);
    years that only appear in ``links`` count as editions too. ``links`` maps
    an edition year to the project ids it lists."""
    years = sorted(set(edition_years) | set(links))
    diffs: list[SammelYearDiff] = []
    previous: int | None = None
    for year in years:
        current = links.get(year, set())
        if previous is None:
            diffs.append(SammelYearDiff(year=year, previous_year=None, kept=sorted(current)))
        else:
            before = links.get(previous, set())
            diffs.append(
                SammelYearDiff(
                    year=year,
                    previous_year=previous,
                    added=sorted(current - before),
                    kept=sorted(current & before),
                    removed=sorted(before - current),
                )
            )
        previous = year
    return diffs


def format_years(years: list[int] | set[int]) -> str:
    """Compact year list: consecutive runs as ranges („2025–2027, 2029“)."""
    ordered = sorted(set(years))
    runs: list[tuple[int, int]] = []
    for year in ordered:
        if runs and year == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], year)
        else:
            runs.append((year, year))
    return ", ".join(str(a) if a == b else f"{a}–{b}" for a, b in runs)


def listing_label(listed_years: list[int] | set[int], first_edition_year: int | None) -> str | None:
    """„Haushalt 2026–2027“ — and, when the project is already in the earliest
    edition read in, a hint that it may have been listed before."""
    if not listed_years:
        return None
    label = f"Haushalt {format_years(listed_years)}"
    if first_edition_year is not None and min(listed_years) <= first_edition_year:
        label += " (erster eingelesener Jahrgang – Aufnahme ggf. früher)"
    return label
