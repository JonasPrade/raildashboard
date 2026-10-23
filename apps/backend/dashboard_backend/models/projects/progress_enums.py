"""Enumerations for the project-progress / planning-state feature.

All enums inherit from ``str`` so SQLAlchemy stores their *value* in a plain
``String`` column (same approach as ``vib_entry.category``) and Pydantic /
``make gen-api`` emit clean TypeScript string unions.
"""

from __future__ import annotations

import enum


class MainPhase(str, enum.Enum):
    """Ordered main planning phases (linear, always present).

    The ordering decides ties, lets lower bounds (FinVe) raise the headline and
    detects set-backs (a newer report with a lower phase), see
    ``services.progress_derivation``.
    """

    NICHT_GESTARTET = "NICHT_GESTARTET"
    VORPLANUNG = "VORPLANUNG"  # LP1-2
    GENEHMIGUNGSPLANUNG = "GENEHMIGUNGSPLANUNG"  # LP3-4
    BAU = "BAU"
    IN_BETRIEB = "IN_BETRIEB"

    @property
    def order(self) -> int:
        return _MAIN_PHASE_ORDER[self]


# Explicit order index for ``max()`` over lower bounds. Kept as a module-level
# dict (rather than ``list.index``) so it is O(1) and unambiguous.
_MAIN_PHASE_ORDER: dict["MainPhase", int] = {
    MainPhase.NICHT_GESTARTET: 0,
    MainPhase.VORPLANUNG: 1,
    MainPhase.GENEHMIGUNGSPLANUNG: 2,
    MainPhase.BAU: 3,
    MainPhase.IN_BETRIEB: 4,
}


class ParallelState(str, enum.Enum):
    """State of a conditional parallel track (PF / parliamentary)."""

    OFFEN = "OFFEN"
    LAEUFT = "LAEUFT"
    ABGESCHLOSSEN = "ABGESCHLOSSEN"

    @property
    def order(self) -> int:
        return _PARALLEL_STATE_ORDER[self]


_PARALLEL_STATE_ORDER: dict["ParallelState", int] = {
    ParallelState.OFFEN: 0,
    ParallelState.LAEUFT: 1,
    ParallelState.ABGESCHLOSSEN: 2,
}


class LifecycleStatus(str, enum.Enum):
    """Orthogonal lifecycle overlay; does not change the phase value.

    ERSETZT: replaced by another project (``replaced_by_project_id``); it stays
    with its history but leaves parent aggregations and the default lists
    (docs/features/feature-project-replacement.md)."""

    AKTIV = "AKTIV"
    PAUSIERT = "PAUSIERT"
    ABGEBROCHEN = "ABGEBROCHEN"
    ERSETZT = "ERSETZT"


# Lifecycle states of projects that no longer run; hidden from the default
# project lists and map (feature-project-replacement.md, W2).
ENDED_LIFECYCLES = frozenset({LifecycleStatus.ABGEBROCHEN.value, LifecycleStatus.ERSETZT.value})


class SourceType(str, enum.Enum):
    """Origin of an observation. VIB/FINVE are materialised in Phase 2."""

    VIB = "VIB"
    FINVE = "FINVE"
    FULDA_RUNDE = "FULDA_RUNDE"
    BAUPORTAL = "BAUPORTAL"
    MEDIEN = "MEDIEN"
    INFRAPLAN = "INFRAPLAN"
    GVFG = "GVFG"
    MANUELL = "MANUELL"


class ObservationTrack(str, enum.Enum):
    """Which track an observation / document link belongs to."""

    MAIN = "MAIN"
    PF = "PF"
    PARL = "PARL"


class DatePrecision(str, enum.Enum):
    """How precisely a date is known (docs/features/feature-project-progress.md
    → „Datumsqualifikation“). The stored date stays the technical sort value;
    the precision decides how it is shown and whether it is a real point in
    time at all."""

    EXACT = "EXACT"  # published day
    MONTH = "MONTH"  # only month known; sort value = 1st of the month
    YEAR = "YEAR"  # only year known; sort value = 1 Jan
    NOT_BEFORE = "NOT_BEFORE"  # only a lower bound, no date ("nach 2031")
    ASSUMED = "ASSUMED"  # derived from a rule, not published
