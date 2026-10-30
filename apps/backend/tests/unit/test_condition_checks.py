"""Inner sums of the InfraGO-Zustandsbericht tables (feature-zustandsbericht.md)."""

from __future__ import annotations

import json
from pathlib import Path

from dashboard_backend.services.condition_checks import check_values

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "zustandsbericht_2025.json"


def _tables():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for table in data["tables"]:
        yield table, [{**v, "reference_year": v.get("reference_year", 2025)} for v in table["values"]]


def test_report_2025_passes_except_the_printed_mismatch():
    found = {}
    for table, values in _tables():
        errors = check_values(values)
        if errors:
            found[(table["domain"], table["scope"], table["region"])] = errors
    # Tab. 5 itself does not add up for the Stellwerke: 45+348+1.042+1.280+707+39 = 3.461,
    # but 3.686 rated. Everything else of the report is consistent.
    assert list(found) == [("FAHRWEG", "GESAMT", None)]
    assert len(found[("FAHRWEG", "GESAMT", None)]) == 1
    assert "fw_stellwerke" in found[("FAHRWEG", "GESAMT", None)][0]
    assert "3.461" in found[("FAHRWEG", "GESAMT", None)][0]


def _dist(values, key="fw_gleise", metric="VERTEILUNG_WBW"):
    return [{"class_key": key, "metric": metric, "grade": g, "reference_year": 2025, "value": v}
            for g, v in enumerate(values, start=1)]


def test_distribution_must_add_up_to_100():
    assert check_values(_dist([18.7, 33.3, 32.1, 13.6, 2.3, 0.0])) == []
    errors = check_values(_dist([18.7, 33.3, 23.1, 13.6, 2.3, 0.0]), {"fw_gleise": "Gleise"})
    assert errors == ["Gleise: Notenverteilung ergibt 91 % statt 100 %."]


def test_grade_required_for_distribution_and_forbidden_elsewhere():
    errors = check_values([
        {"class_key": None, "metric": "VERTEILUNG_WBW", "grade": None, "reference_year": 2025, "value": 5},
        {"class_key": None, "metric": "NOTE", "grade": 2, "reference_year": 2025, "value": 3},
    ])
    assert len(errors) == 2
    assert "Note 1–6 fehlt" in errors[0]
    assert "nur bei Verteilungen" in errors[1]


def test_note_range_and_classes_add_up_to_total():
    errors = check_values([
        {"class_key": None, "metric": "NOTE", "grade": None, "reference_year": 2025, "value": 7},
        {"class_key": None, "metric": "WBW_BEWERTET", "grade": None, "reference_year": 2025, "value": 100},
        {"class_key": "a", "metric": "WBW_BEWERTET", "grade": None, "reference_year": 2025, "value": 60},
        {"class_key": "b", "metric": "WBW_BEWERTET", "grade": None, "reference_year": 2025, "value": 30},
    ])
    assert any("nicht zwischen 1 und 6" in e for e in errors)
    assert any("Anlagenklassen ergeben 90, Summe ist 100" in e for e in errors)


def test_quantities_and_renewal_need():
    values = _dist([100, 100, 100, 50, 30, 20], key="fw_weichen", metric="VERTEILUNG_MENGE") + [
        {"class_key": "fw_weichen", "metric": "MENGE_BEWERTET", "grade": None, "reference_year": 2025, "value": 400},
        {"class_key": "fw_weichen", "metric": "ERNEUERUNGSBEDARF_MENGE", "grade": None, "reference_year": 2025, "value": 90},
    ]
    errors = check_values(values, {"fw_weichen": "Weichen"})
    assert errors == ["Weichen: Erneuerungsbedarf 90 passt nicht zu den Mengen der Noten 4–6 (100)."]


def test_empfangsgebaeude_stay_out_of_the_sums():
    values = [
        {"class_key": None, "metric": "WBW_BEWERTET", "grade": None, "reference_year": 2025, "value": 10},
        {"class_key": "pb_bahnsteige", "metric": "WBW_BEWERTET", "grade": None, "reference_year": 2025, "value": 6},
        {"class_key": "pb_fahrtreppen", "metric": "WBW_BEWERTET", "grade": None, "reference_year": 2025, "value": 4},
        {"class_key": "pb_empfangsgebaeude", "metric": "WBW_BEWERTET", "grade": None, "reference_year": 2025, "value": 9},
    ]
    assert check_values(values) == []
