"""Snapshot tests for the Haushalt upsert changelog machinery (#86).

These pin the exact changelog entries (field names, JSON-serialised old/new
values, action, ordering) produced by ``upsert_finve`` / ``upsert_budget`` for
a reference import. The #86 refactor must keep this audit output byte-identical.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dashboard_backend.crud.haushalt_import import upsert_budget, upsert_finve
from dashboard_backend.models.haushalt.budget_change_log import (
    BudgetChangeLog,
    BudgetChangeLogEntry,
)
from dashboard_backend.models.haushalt.finve_change_log import (
    FinveChangeLog,
    FinveChangeLogEntry,
)
from dashboard_backend.models.projects.budget import Budget
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.schemas.haushalt_import import ProposedBudget, ProposedFinve

_TABLES = [
    Finve.__table__,
    Budget.__table__,
    FinveChangeLog.__table__,
    FinveChangeLogEntry.__table__,
    BudgetChangeLog.__table__,
    BudgetChangeLogEntry.__table__,
]


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    for t in _TABLES:
        t.create(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _entry_tuples(changelog):
    return [(e.field_name, e.old_value, e.new_value) for e in changelog.entries]


def test_upsert_finve_create_snapshot(db):
    proposed = ProposedFinve(
        id=275, name="ABS Hanau–Würzburg", starting_year=2019,
        cost_estimate_original=1500, is_sammel_finve=False,
    )
    finve, created, changelog = upsert_finve(db, proposed, user=None, haushalt_year=2026)
    db.commit()

    assert created is True
    assert finve.id == 275
    assert changelog.action == "CREATE"
    assert changelog.haushalt_year == 2026
    # None-valued fields are skipped on CREATE; values are json.dumps-serialised.
    assert _entry_tuples(changelog) == [
        ("name", None, '"ABS Hanau\\u2013W\\u00fcrzburg"'),
        ("starting_year", None, "2019"),
        ("cost_estimate_original", None, "1500"),
        ("is_sammel_finve", None, "false"),
    ]


def test_upsert_finve_update_snapshot(db):
    base = ProposedFinve(
        id=275, name="ABS Hanau–Würzburg", starting_year=2019,
        cost_estimate_original=1500, is_sammel_finve=False,
    )
    upsert_finve(db, base, user=None, haushalt_year=2025)
    db.commit()

    changed = ProposedFinve(
        id=275, name="ABS Hanau–Würzburg/Fulda", starting_year=2019,
        cost_estimate_original=1800, is_sammel_finve=False,
    )
    finve, created, changelog = upsert_finve(db, changed, user=None, haushalt_year=2026)
    db.commit()

    assert created is False
    assert changelog.action == "UPDATE"
    assert _entry_tuples(changelog) == [
        ("name", '"ABS Hanau\\u2013W\\u00fcrzburg"', '"ABS Hanau\\u2013W\\u00fcrzburg/Fulda"'),
        ("cost_estimate_original", "1500", "1800"),
    ]
    # The diff also applies the new values to the row.
    assert finve.name == "ABS Hanau–Würzburg/Fulda"
    assert finve.cost_estimate_original == 1800


def test_upsert_finve_no_change_returns_no_changelog(db):
    proposed = ProposedFinve(id=300, name="NBS X", is_sammel_finve=False)
    upsert_finve(db, proposed, user=None, haushalt_year=2025)
    db.commit()
    _, created, changelog = upsert_finve(db, proposed, user=None, haushalt_year=2026)
    assert created is False
    assert changelog is None


def test_upsert_budget_create_and_update_snapshot(db):
    upsert_finve(db, ProposedFinve(id=275, name="ABS", is_sammel_finve=False), None, 2025)
    db.commit()

    base = ProposedBudget(
        budget_year=2025, fin_ve=275, lfd_nr="12", bedarfsplan_number="B0080",
        cost_estimate_original=1500, cost_estimate_actual=1600,
        delta_previous_year=100, delta_previous_year_relativ=6.7,
        delta_previous_year_reasons="Preisstand", spent_two_years_previous=300,
        allowed_previous_year=120, spending_residues=10, year_planned=90,
        next_years=980, sammel_finve=False,
    )
    budget, created, changelog = upsert_budget(db, base, user=None, haushalt_year=2025)
    db.commit()

    assert created is True
    assert changelog.action == "CREATE"
    assert _entry_tuples(changelog) == [
        ("lfd_nr", None, '"12"'),
        ("bedarfsplan_number", None, '"B0080"'),
        ("cost_estimate_original", None, "1500"),
        ("cost_estimate_actual", None, "1600"),
        ("delta_previous_year", None, "100"),
        ("delta_previous_year_relativ", None, "6.7"),
        ("delta_previous_year_reasons", None, '"Preisstand"'),
        ("spent_two_years_previous", None, "300"),
        ("allowed_previous_year", None, "120"),
        ("spending_residues", None, "10"),
        ("year_planned", None, "90"),
        ("next_years", None, "980"),
        ("sammel_finve", None, "false"),
    ]

    changed = base.model_copy(update={"cost_estimate_actual": 1700, "year_planned": None})
    budget2, created2, changelog2 = upsert_budget(db, changed, user=None, haushalt_year=2026)
    db.commit()

    assert created2 is False
    assert budget2.id == budget.id
    assert changelog2.action == "UPDATE"
    assert _entry_tuples(changelog2) == [
        ("cost_estimate_actual", "1600", "1700"),
        ("year_planned", "90", None),
    ]
    assert budget2.cost_estimate_actual == 1700
    assert budget2.year_planned is None


# ---------------------------------------------------------------------------
# Measures without a FinVe number are matched on their key (#127 follow-up)
# ---------------------------------------------------------------------------

def _keyed(finve_key: str, name: str, **kwargs) -> ProposedFinve:
    return ProposedFinve(
        id=None,
        finve_key=finve_key,
        name=name,
        temporary_finve_number=True,
        **kwargs,
    )


def test_keyed_finve_gets_an_id_from_the_database(db):
    """Tabellen 2–5 print no FinVe number, so the row is created with an
    auto-assigned id and remembers the key it was identified by."""
    finve, created, _ = upsert_finve(
        db, _keyed("t4:F 03 E 0793", "Bau FinVe Wilhelmshaven"), None, 2027
    )
    assert created is True
    assert finve.id is not None
    assert finve.finve_key == "t4:F 03 E 0793"
    assert finve.temporary_finve_number is True


def test_same_key_updates_the_same_row_in_the_next_year(db):
    first, _, _ = upsert_finve(
        db, _keyed("t2:SV 52/2017", "Sammelvereinbarung 52", cost_estimate_original=53_301), None, 2026
    )
    db.flush()
    second, created, changelog = upsert_finve(
        db, _keyed("t2:SV 52/2017", "Sammelvereinbarung 52", cost_estimate_original=91_369), None, 2027
    )
    assert created is False
    assert second.id == first.id
    assert _entry_tuples(changelog) == [("cost_estimate_original", "53301", "91369")]


def test_different_keys_stay_separate_rows(db):
    first, _, _ = upsert_finve(db, _keyed("t4:F 03 E 0793", "Bau FinVe"), None, 2027)
    db.flush()
    second, created, _ = upsert_finve(db, _keyed("t4:F 03 E 0793#2", "Bau FinVe"), None, 2027)
    assert created is True
    assert second.id != first.id


def test_keyed_finve_does_not_collide_with_a_numbered_one(db):
    numbered, _, _ = upsert_finve(
        db, ProposedFinve(id=275, name="ABS Angermünde- Grenze D/PL"), None, 2027
    )
    db.flush()
    keyed, created, _ = upsert_finve(db, _keyed("t5:B0094", "Mitteldeutsches Revier"), None, 2027)
    assert created is True
    assert keyed.id != numbered.id
    assert numbered.finve_key is None


def test_budget_of_a_keyed_measure_uses_the_assigned_finve_id(db):
    finve, _, _ = upsert_finve(db, _keyed("t3:F08Q0770", "Digitaler Knoten Stuttgart"), None, 2027)
    db.flush()
    budget, created, _ = upsert_budget(
        db,
        ProposedBudget(budget_year=2027, fin_ve=finve.id, cost_estimate_actual=383_234),
        None,
        2027,
    )
    assert created is True
    assert budget.fin_ve == finve.id
    assert budget.cost_estimate_actual == 383_234


def test_keyed_finve_id_cannot_collide_with_a_printed_number(db):
    """FinVe numbers are the primary key and are inserted explicitly, so the
    sequence never learns about them. A keyed measure must therefore take its
    id from the reserved band, not the next sequence value."""
    upsert_finve(db, ProposedFinve(id=5108, name="ABS mit gedruckter Nummer"), None, 2027)
    db.flush()

    keyed, created, _ = upsert_finve(db, _keyed("t5:B0091", "Mitteldeutsches Revier"), None, 2027)
    assert created is True
    assert keyed.id >= 900_000


def test_keyed_finves_get_consecutive_ids_from_the_band(db):
    first, _, _ = upsert_finve(db, _keyed("t2:SV 52/2017", "SV 52"), None, 2027)
    db.flush()
    second, _, _ = upsert_finve(db, _keyed("t2:SV 53/2017", "SV 53"), None, 2027)
    db.flush()
    assert (first.id, second.id) == (900_000, 900_001)


def test_reimport_reuses_the_id_instead_of_taking_a_new_one(db):
    first, _, _ = upsert_finve(db, _keyed("t4:F 03 E 0793", "Bau FinVe"), None, 2026)
    db.flush()
    again, created, _ = upsert_finve(db, _keyed("t4:F 03 E 0793", "Bau FinVe"), None, 2027)
    assert created is False
    assert again.id == first.id

