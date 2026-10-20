"""Suggestions for Infraplan rows (tasks/infraplan_matching.py)."""

from __future__ import annotations

from dashboard_backend.tasks.infraplan_matching import (
    ProjectRef,
    preselection,
    strip_pb_prefix,
    suggest_rows,
)


def _row(key="BP_A-1", **values):
    return {"row_key": key, "section": key.split("-")[0], **values}


def test_strip_pb_prefix():
    assert strip_pb_prefix("PB 07: ABS Karlsruhe – Basel") == "ABS Karlsruhe – Basel"
    assert strip_pb_prefix("ABS Hanau – Fulda") == "ABS Hanau – Fulda"


def test_previous_number_wins_with_full_confidence():
    projects = [ProjectRef(1, "Irgendwas"), ProjectRef(2, "Anderes")]

    out = suggest_rows([_row(primary_number="E.16")], projects, {"E.16": [2]})

    assert out["BP_A-1"][0] == {"project_id": 2, "confidence": 1.0, "reason": "NUMBER"}


def test_gvfg_key_against_project_number():
    projects = [ProjectRef(5, "S-Bahn Nürnberg", project_number="7 D 2825_A")]

    out = suggest_rows([_row("GVFG_A-3", primary_number="07 D 2825_A")], projects, {})

    assert out["GVFG_A-3"] == [{"project_id": 5, "confidence": 1.0, "reason": "GVFG_KEY"}]


def test_fuzzy_prefers_subproject_over_superior():
    projects = [
        ProjectRef(10, "ABS Karlsruhe – Basel"),
        ProjectRef(11, "ABS Karlsruhe – Basel Abschnitt 9.2 Schliengen – Eimeldingen", superior_project_id=10),
        ProjectRef(12, "NBS Hannover – Bielefeld"),
    ]
    row = _row(
        bezeichnung="PB 07: ABS/NBS Karlsruhe – Basel",
        massnahme="Abschnitt 9.2 Schliengen – Eimeldingen",
    )

    out = suggest_rows([row], projects, {})

    ids = [s["project_id"] for s in out["BP_A-1"]]
    assert ids[0] == 11
    assert 10 not in ids
    assert 12 not in ids


def test_no_shared_word_no_suggestion():
    out = suggest_rows([_row(massnahme="Elektrifizierung Hof – Regensburg")], [ProjectRef(1, "Knoten Köln")], {})

    assert out["BP_A-1"] == []


def test_preselection_strong_hits_and_best_fuzzy():
    strong = [
        {"project_id": 1, "confidence": 1.0, "reason": "NUMBER"},
        {"project_id": 2, "confidence": 1.0, "reason": "NUMBER"},
        {"project_id": 3, "confidence": 0.9, "reason": "FUZZY"},
    ]
    fuzzy = [
        {"project_id": 3, "confidence": 0.9, "reason": "FUZZY"},
        {"project_id": 4, "confidence": 0.86, "reason": "FUZZY"},
    ]

    assert preselection(strong, 0.85) == ([1, 2], "NUMBER")
    assert preselection(fuzzy, 0.85) == ([3], "FUZZY")
    assert preselection(fuzzy, 0.95) == ([], None)
