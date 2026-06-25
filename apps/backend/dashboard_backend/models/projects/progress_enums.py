"""Enumerations for the project-progress / planning-state feature.

All enums inherit from ``str`` so SQLAlchemy stores their *value* in a plain
``String`` column (same approach as ``vib_entry.category``) and Pydantic /
``make gen-api`` emit clean TypeScript string unions.
"""

from __future__ import annotations

import enum


class MainPhase(str, enum.Enum):
    """Ordered main planning phases (linear, always present).

    The ordering is the backbone of the *lower-bound* derivation rule: most
    sources assert a monotone lower bound, so the headline phase is the
    ``max`` over the credible lower bounds (see ``services.progress_derivation``).
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
    """Orthogonal lifecycle overlay; does not change the phase value."""

    AKTIV = "AKTIV"
    PAUSIERT = "PAUSIERT"
    ABGEBROCHEN = "ABGEBROCHEN"


class SourceType(str, enum.Enum):
    """Origin of an observation. VIB/FINVE are materialised in Phase 2."""

    VIB = "VIB"
    FINVE = "FINVE"
    FULDA_RUNDE = "FULDA_RUNDE"
    BAUPORTAL = "BAUPORTAL"
    MEDIEN = "MEDIEN"
    MANUELL = "MANUELL"


class ObservationTrack(str, enum.Enum):
    """Which track an observation / document link belongs to."""

    MAIN = "MAIN"
    PF = "PF"
    PARL = "PARL"
