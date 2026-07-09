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
