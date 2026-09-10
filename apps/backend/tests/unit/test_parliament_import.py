"""Parsing rules and idempotency of the abgeordnetenwatch import.

The three traps the prototype hit are pinned here: the constituency number lives
only in a label, faction labels carry soft hyphens, and only
``mandate_won == "constituency"`` is a direct mandate.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dashboard_backend.models.parliament import (
    Committee,
    CommitteeMembership,
    Constituency,
    Mandate,
    ParliamentPeriod,
    Politician,
    role_label,
    role_rank,
)
from dashboard_backend.models.parliament.import_run import (
    IMPORT_STATUS_SUCCESS,
    ParliamentImportRun,
)
from dashboard_backend.services.parliament_import import (
    clean_fraction_label,
    constituency_number_from_label,
    constituency_properties,
    current_fraction_label,
    import_politicians,
    land_name,
    split_name,
)

TABLES = [
    ParliamentPeriod.__table__,
    Politician.__table__,
    Constituency.__table__,
    Committee.__table__,
    Mandate.__table__,
    CommitteeMembership.__table__,
    ParliamentImportRun.__table__,
]


# --- pure parsing -----------------------------------------------------------


def test_constituency_number_is_read_from_the_label():
    label = "14 - Rostock – Landkreis Rostock II (Bundestag 2025 - 2029)"
    assert constituency_number_from_label({"label": label}) == 14


@pytest.mark.parametrize("value", [None, {}, {"label": "Rostock"}, {"label": "x - y"}])
def test_constituency_number_missing_is_none(value):
    assert constituency_number_from_label(value) is None


def test_soft_hyphens_are_stripped_from_faction_labels():
    assert clean_fraction_label("BÜND­NIS 90/DIE GRÜ­NEN (Bundestag)") == (
        "BÜNDNIS 90/DIE GRÜNEN"
    )


def test_current_faction_membership_wins_over_an_ended_one():
    memberships = [
        {"fraction": {"label": "Alte Fraktion (Bundestag)"}, "valid_until": "2026-01-01"},
        {"fraction": {"label": "Neue Fraktion (Bundestag)"}, "valid_until": None},
    ]
    assert current_fraction_label(memberships) == "Neue Fraktion"


def test_split_name_falls_back_to_the_label():
    assert split_name({"label": "Tarek Al-Wazir"}) == ("Tarek", "Al-Wazir")
    assert split_name({"first_name": "Lisa", "last_name": "Paus"}) == ("Lisa", "Paus")


def test_strongest_committee_role_wins():
    assert role_rank("chairperson") < role_rank("member")
    assert role_rank("member") < role_rank("alternate_member")
    assert role_label("chairperson") == "Vorsitz"
    # An unknown role stays visible instead of being dropped.
    assert role_label("rapporteur") == "rapporteur"
    assert role_rank("rapporteur") > role_rank("alternate_member")


def test_constituency_properties_accepts_both_field_sets():
    assert constituency_properties({"wkr_id": 298, "name": "St. Wendel"}) == (298, "St. Wendel")
    assert constituency_properties({"WKR_NR": "1", "WKR_NAME": "Flensburg"}) == (1, "Flensburg")


def test_land_name_from_key_or_plain_name():
    assert land_name({"bl": "10"}) == "Saarland"
    assert land_name({"LAND_NAME": "Bayern"}) == "Bayern"
    assert land_name({}) is None


# --- full import ------------------------------------------------------------


class FakeClient:
    """Stands in for the API: same shapes, no network."""

    def __init__(self, mandates, memberships=None):
        self.mandates = mandates
        self.memberships = memberships or {}

    def get(self, path, **params):
        if path == "/parliament-periods":
            return {
                "data": [
                    {
                        "id": 161,
                        "label": "Bundestag 2025 - 2029",
                        "parliament": {"id": 5, "label": "Bundestag"},
                        "start_date_period": "2025-03-25",
                        "end_date_period": "2029-03-24",
                    }
                ]
            }
        raise AssertionError(f"unexpected get: {path}")

    def paged(self, path, **params):
        if path == "/constituencies":
            return iter(
                [
                    {"id": 5001, "number": 1, "name": "Flensburg – Schleswig"},
                    {"id": 5002, "number": 2, "name": "Nordfriesland – Dithmarschen Nord"},
                ]
            )
        if path == "/committees":
            return iter(
                [
                    {"id": 900, "label": "Verkehrsausschuss"},
                    {"id": 901, "label": "Haushaltsausschuss"},
                    {"id": 902, "label": "Sportausschuss"},
                ]
            )
        if path == "/committee-memberships":
            return iter(self.memberships.get(params["committee"], []))
        if path == "/candidacies-mandates":
            return iter(self.mandates)
        raise AssertionError(f"unexpected paged: {path}")


def _mandate(external_id, politician_id, name, won, number, fraction="SPD"):
    return {
        "id": external_id,
        "politician": {
            "id": politician_id,
            "label": name,
            "abgeordnetenwatch_url": f"https://example.invalid/{politician_id}",
        },
        "fraction_membership": [
            {"fraction": {"label": f"{fraction} (Bundestag)"}, "valid_until": None}
        ],
        "electoral_data": {
            "mandate_won": won,
            "constituency": (
                {"label": f"{number} - Irgendwo (Bundestag 2025 - 2029)"} if number else None
            ),
        },
    }


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    for table in TABLES:
        table.create(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()


def _client():
    mandates = [
        _mandate(1, 100, "Direkt Gewählt", "constituency", 1),
        _mandate(2, 101, "Über Liste", "list", 1, fraction="BÜND­NIS 90/DIE GRÜNEN"),
        _mandate(3, 102, "Nachgerückt", "moved_up", 2),
        _mandate(4, 103, "Ohne Wahlkreis", "list", None),
    ]
    memberships = {
        900: [
            {"candidacy_mandate": {"id": 1}, "committee_role": "member"},
            # A second row for the same mandate: the strongest role has to win.
            {"candidacy_mandate": {"id": 1}, "committee_role": "chairperson"},
        ],
        901: [{"candidacy_mandate": {"id": 3}, "committee_role": "alternate_member"}],
    }
    return FakeClient(mandates, memberships)


def test_import_writes_mandates_and_committee_roles(session):
    run = import_politicians(session, client=_client())

    assert run.status == IMPORT_STATUS_SUCCESS
    assert run.stats["mandates"] == 4
    assert run.stats["direct_mandates"] == 1
    assert run.stats["mandates_without_constituency"] == 1
    # 2 constituencies, 1 of them holds a direct mandate.
    assert run.stats["constituencies_without_direct_mandate"] == 1

    direct = session.query(Mandate).filter(Mandate.external_id == 1).one()
    assert direct.is_direct_mandate is True
    assert direct.constituency.number == 1

    # "moved_up" is not a direct mandate — the prototype's rule, kept.
    moved_up = session.query(Mandate).filter(Mandate.external_id == 3).one()
    assert moved_up.is_direct_mandate is False
    assert moved_up.mandate_type == "moved_up"

    listed = session.query(Mandate).filter(Mandate.external_id == 2).one()
    assert listed.fraction_label == "BÜNDNIS 90/DIE GRÜNEN"
    assert "­" not in listed.fraction_label

    membership = (
        session.query(CommitteeMembership)
        .filter(CommitteeMembership.mandate_id == direct.id)
        .one()
    )
    assert membership.role == "chairperson"
    assert membership.role_label == "Vorsitz"

    # Only the two committees this feature tracks are stored.
    assert {c.key for c in session.query(Committee).all()} == {"verkehr", "haushalt"}


def test_import_is_idempotent(session):
    import_politicians(session, client=_client())
    first = {
        "mandates": session.query(Mandate).count(),
        "politicians": session.query(Politician).count(),
        "memberships": session.query(CommitteeMembership).count(),
        "constituencies": session.query(Constituency).count(),
    }

    import_politicians(session, client=_client())
    second = {
        "mandates": session.query(Mandate).count(),
        "politicians": session.query(Politician).count(),
        "memberships": session.query(CommitteeMembership).count(),
        "constituencies": session.query(Constituency).count(),
    }
    assert first == second


def test_dropped_mandate_is_removed_but_the_person_stays(session):
    import_politicians(session, client=_client())

    client = _client()
    client.mandates = [m for m in client.mandates if m["id"] != 3]
    import_politicians(session, client=client)

    assert session.query(Mandate).filter(Mandate.external_id == 3).one_or_none() is None
    # The person outlives the mandate.
    assert session.query(Politician).filter(Politician.external_id == 102).one_or_none() is not None


def test_missing_committee_fails_the_run(session):
    client = _client()

    def only_transport(path, **params):
        if path == "/committees":
            return iter([{"id": 900, "label": "Verkehrsausschuss"}])
        return FakeClient.paged(client, path, **params)

    client.paged = only_transport
    with pytest.raises(RuntimeError):
        import_politicians(session, client=client)

    run = session.query(ParliamentImportRun).order_by(ParliamentImportRun.id.desc()).first()
    assert run.status == "error"
    assert "haushalt" in (run.error or "")
