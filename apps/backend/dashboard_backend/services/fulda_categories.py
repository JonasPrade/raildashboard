"""Category catalog of the Fulda-Runde importer (feature-fulda-import.md).

A category fixes what a line of a Fulda answer states: the project's current
phase ("Ist" / completed without follow-up phase) or an announced future step
(prognosis / new admission). The agent picks the category from the wording of
the question above a list — never from its number, which changes every year.
"""

from __future__ import annotations

from dataclasses import dataclass

from dashboard_backend.models.projects.progress_enums import MainPhase

# Statement kinds. IST and OHNE_FOLGEPHASE set the phase; PROGNOSE and
# NEUAUFNAHME only yield an expected date.
IST = "IST"
OHNE_FOLGEPHASE = "OHNE_FOLGEPHASE"
PROGNOSE = "PROGNOSE"
NEUAUFNAHME = "NEUAUFNAHME"
EXPECTED_KINDS = frozenset({PROGNOSE, NEUAUFNAHME})


@dataclass(frozen=True)
class FuldaCategory:
    key: str
    label: str
    kind: str
    # Phase asserted (IST/OHNE_FOLGEPHASE) or expected (PROGNOSE/NEUAUFNAHME);
    # None = hint only, no observation.
    phase: MainPhase | None

    @property
    def is_expected(self) -> bool:
        return self.kind in EXPECTED_KINDS


FULDA_CATEGORY_LIST: tuple[FuldaCategory, ...] = (
    FuldaCategory("IN_LPH_1_2", "aktuell in der Sammel-FinVe Lph 1/2", IST, MainPhase.VORPLANUNG),
    FuldaCategory(
        "IN_LPH_3_4", "aktuell in der Sammel-FinVe Lph 3/4", IST, MainPhase.GENEHMIGUNGSPLANUNG
    ),
    FuldaCategory("HAS_BAUFINVE", "hat eine Baufinanzierungsvereinbarung", IST, MainPhase.BAU),
    FuldaCategory(
        "COMPLETED_LPH_1_2_NO_FOLLOWUP",
        "Lph 1/2 abgeschlossen, keine Aufnahme in Lph 3/4",
        OHNE_FOLGEPHASE,
        MainPhase.VORPLANUNG,
    ),
    FuldaCategory(
        "COMPLETED_LPH_3_4_NO_FOLLOWUP",
        "Lph 3/4 abgeschlossen, keine Baufinanzierungsvereinbarung",
        OHNE_FOLGEPHASE,
        MainPhase.GENEHMIGUNGSPLANUNG,
    ),
    FuldaCategory("COMPLETES_LPH_1", "Lph 1 wird abgeschlossen", PROGNOSE, None),
    FuldaCategory(
        "COMPLETES_LPH_2",
        "Lph 2 bzw. Lph 1/2 wird abgeschlossen",
        PROGNOSE,
        MainPhase.GENEHMIGUNGSPLANUNG,
    ),
    FuldaCategory("COMPLETES_LPH_3_4", "Lph 3/4 wird abgeschlossen", PROGNOSE, MainPhase.BAU),
    FuldaCategory(
        "NEW_LPH_1_2", "soll neu in die Sammel-FinVe Lph 1/2", NEUAUFNAHME, MainPhase.VORPLANUNG
    ),
    FuldaCategory(
        "NEW_LPH_3_4",
        "soll neu in die Sammel-FinVe Lph 3/4",
        NEUAUFNAHME,
        MainPhase.GENEHMIGUNGSPLANUNG,
    ),
    FuldaCategory(
        "NEW_BAUFINVE", "soll eine Baufinanzierungsvereinbarung erhalten", NEUAUFNAHME, MainPhase.BAU
    ),
)

FULDA_CATEGORIES: dict[str, FuldaCategory] = {c.key: c for c in FULDA_CATEGORY_LIST}

ATTRIBUTED_TO = ("BMV", "DB")


def get_category(key: str | None) -> FuldaCategory | None:
    if not key:
        return None
    return FULDA_CATEGORIES.get(key.strip().upper())
