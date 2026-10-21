"""Master data checks (services/project_data_checks.py, MCP check_project_data)."""

from __future__ import annotations

from dashboard_backend.services.project_data_checks import ProjectRecord, run_checks


def _ids(findings, key="projects"):
    return [sorted(p["id"] for p in f[key]) for f in findings]


def test_duplicate_numbers_and_sibling_names():
    projects = [
        ProjectRecord(1505, "ABS/NBS Stuttgart - Singen - Grenze D/CH (Gäubahn)", "2-040-V01"),
        ProjectRecord(1829, "Stuttgart - Singen (Gäubahn) Teilmaßnahme 8", "2-040-V01 TM8", 1505),
        ProjectRecord(2221, "Pfaffensteigtunnel (ABS Stuttgart – Singen)", "2-040-V01  TM8", 1505),
        ProjectRecord(1494, "ABS Grenze NL/D – Kaldenkirchen – Rheydt-Odenkirchen"),
        ProjectRecord(1781, "Kaldenkirchen Teilmaßnahme Rheydt – Rheydt-Odenkirchen", "2-025-V01 TM2", 1494),
        ProjectRecord(1782, "Kaldenkirchen Teilmaßnahme Rheydt – Rheydt-Odenkirchen", "2-025-V01 TM3", 1494),
        ProjectRecord(9, "Kaldenkirchen Teilmaßnahme Rheydt – Rheydt-Odenkirchen", None, None),
    ]

    result = run_checks(projects, ["duplicate_number", "duplicate_sibling_name"])

    assert _ids(result["duplicate_number"]) == [[1829, 2221]]
    assert _ids(result["duplicate_sibling_name"]) == [[1781, 1782]]


def test_gvfg_land_code_against_group_entries_and_infraplan_rows():
    projects = [
        # S4 Hamburg carries the key of the Schleswig-Holstein share.
        ProjectRecord(
            2269, "S-Bahn S4 Hamburg – Ahrensburg – Bad Oldesloe", "01 D 508_A",
            infraplan_entries=[(2026, "GVFG_A-16", "02 D 508_A", "Hamburg"), (2026, "GVFG_A-19", "01 D 508_A", "Schleswig-Holstein")],
        ),
        ProjectRecord(2, "Stadtbahn Karlsruhe", "09 G 111_T", groups=["GVFG BW", "GVFG"]),
        ProjectRecord(3, "Breisgau-S-Bahn", "08 D 153_S", groups=["GVFG BW"], gvfg_entries=[("08 D 153_S", "Baden-Württemberg")]),
        ProjectRecord(4, "Ohne Schlüssel", "2-040-V01", groups=["GVFG BW"]),
    ]

    findings = run_checks(projects, ["gvfg_land_mismatch"])["gvfg_land_mismatch"]

    assert [f["id"] for f in findings] == [2269, 2]
    assert findings[0]["land_of_number"] == "Schleswig-Holstein"
    assert findings[0]["reasons"] == ["Infraplan 2026 GVFG_A-16: 02 D 508_A (Hamburg)"]
    assert findings[1]["reasons"] == ["Projektgruppe „GVFG BW“ (Baden-Württemberg)"]


def test_unnamed_subprojects():
    projects = [
        ProjectRecord(1501, "Knoten Mannheim"),
        ProjectRecord(1810, "Knoten Mannheim Teilmaßnahme 8", "K-004-V01 TM8", 1501),
        ProjectRecord(1811, "Knoten Mannheim TM9", None, 1501, description="Nordkopf Worms"),
        ProjectRecord(1690, "Knoten Mannheim (Schnellfahrweichen)", "D-169", 1501),
        ProjectRecord(1926, "Projektbündel 8: Dortmund – Hamm – Bielefeld"),
        ProjectRecord(1534, "ABS Hamm – Bielefeld", "D-13", 1926),
    ]

    findings = run_checks(projects, ["unnamed_subproject"])["unnamed_subproject"]

    assert [(f["id"], f["has_description"]) for f in findings] == [(1810, False), (1811, True)]
