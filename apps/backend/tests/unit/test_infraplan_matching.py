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


# --- Ausbau 2027: normalisation, aliases, context, previous year ------------------


def test_abbreviations_are_written_out():
    from dashboard_backend.tasks.infraplan_matching import normalize_text

    assert normalize_text("Ubf Augsburg") == normalize_text("Umschlagbahnhof Augsburg")
    assert normalize_text("1gl� Vbk Bad Kleinen") == "eingleisig verbindungskurve bad kleinen"
    assert normalize_text("Abzw. Mönchhof") == "abzweig mönchhof"
    assert normalize_text("Mü-Riem Ü-BW") == "münchen riem überwerfungsbauwerk"
    assert normalize_text("4gl. Ausbau HD Hbf") == "viergleisig ausbau heidelberg hauptbahnhof"
    assert normalize_text("MA Rbf") == "mannheim rangierbahnhof"
    assert normalize_text("HH-Altona") == "hamburg altona"
    assert normalize_text("Ffm Stadion") == normalize_text("Frankfurt am Main Stadion")
    assert normalize_text("Großknoten Köln") == "knoten köln"
    assert normalize_text("zweigleisiger Ausbau") == normalize_text("2gl. Ausbau")
    assert normalize_text("3. Gleis") == normalize_text("drittes Gleis")
    assert normalize_text("TM8") == "teilmaßnahme 8"
    # Only a leading ABS as a word is dropped, not the letters of a word.
    assert normalize_text("Abstellanlage Wandsbek") == "abstellanlage wandsbek"
    assert normalize_text("ABS Lübeck – Schwerin") == "lübeck schwerin"
    # "ma" inside a word and "Main" stay.
    assert normalize_text("Maintal") == "maintal"


def test_identifiers():
    from dashboard_backend.tasks.infraplan_matching import identifiers

    assert identifiers("Ü-BW (DT 107)") == {"DT 107"}
    assert identifiers("Krzbf Braunau (DT 108/109)") == {"DT 108", "DT 109"}
    assert identifiers("Synchronisationsgleise inkl. D-Takt 80–81") == {"DT 80", "DT 81"}
    assert identifiers("PB 07: ABS/NBS Karlsruhe – Basel") == {"PB 7"}
    assert identifiers("ABS/NBS Nürnberg–Erfurt (VDE 8�1)") == {"VDE 8.1"}


def test_dt_alias_is_a_sure_hit_and_d_numbers_are_not():
    projects = [
        ProjectRef(1, "Knoten München (Fußgängersteg)", project_number="D-37", aliases=("DT 105",)),
        ProjectRef(2, "Knoten Hannover (Fußgängerunterführung)", project_number="D-105"),
    ]
    row = _row("BP_C-38", bezeichnung="Großknoten München", massnahme="DT 105 zusätzliche Fußgängerüberquerung Hbf München")

    out = suggest_rows([row], projects, {})

    assert out["BP_C-38"][0]["project_id"] == 1
    assert out["BP_C-38"][0]["reason"] == "ALIAS"
    assert preselection(out["BP_C-38"], 0.85) == ([1], "NUMBER")
    assert 2 not in [s["project_id"] for s in out["BP_C-38"] if s["confidence"] >= 0.85]


def test_context_section_number_finds_the_subproject():
    projects = [
        ProjectRef(10, "ABS/NBS Karlsruhe - Basel"),
        ProjectRef(11, "ABS/NBS Karlsruhe – Basel, Abschnitt 7 Appenweier Kenzingen", superior_project_id=10),
        ProjectRef(12, "ABS/NBS Karlsruhe – Basel, Abschnitt 8 Kenzingen – Müllheim", superior_project_id=10),
        ProjectRef(13, "ABS/NBS Karlsruhe – Basel, Abschnitt 2-6 Rastatt Süd – Offenburg", superior_project_id=10),
    ]
    rows = [
        _row("BP_B-14", bezeichnung="PB 07: ABS/NBS Karlsruhe - Basel, PFA 7B (ABS 7�1–7�4)",
             massnahme="StA 7B, ABS Pfa 7�1-7�4: Appenweier - Kenzingen"),
        _row("BP_A-31", bezeichnung="PB 07: ABS/NBS Karlsruhe - Basel, PFA 8A",
             massnahme="StA 8A NBS, Pfa 8�0-8�4: Kenzingen - Müllheim"),
        _row("BP_B-99", bezeichnung="PB 07: ABS/NBS Karlsruhe – Basel", massnahme="Streckenabschnitt 4"),
    ]

    out = suggest_rows(rows, projects, {})

    assert preselection(out["BP_B-14"], 0.85)[0] == [11]
    assert out["BP_B-14"][0]["reason"] == "CONTEXT"
    assert out["BP_B-14"][0]["confidence"] == 0.9
    assert preselection(out["BP_A-31"], 0.85)[0] == [12]
    # "Abschnitt 2-6" is a range.
    assert preselection(out["BP_B-99"], 0.85)[0] == [13]


def test_context_words_pick_the_named_subproject_of_a_knot():
    projects = [
        ProjectRef(1, "Knoten Hamburg"),
        ProjectRef(2, "Knoten Hamburg Teilmaßnahme Kreuzungsbauwerk Hamburg-Wilhelmsburg", superior_project_id=1),
        ProjectRef(3, "Knoten Hamburg Teilmaßnahme Überwerfungsbauwerk Meckelfeld", superior_project_id=1),
        ProjectRef(4, "Knoten Hamburg Teilmaßnahme Überwerfungsbauwerk Hamburg-Altona Nord", superior_project_id=1),
        ProjectRef(5, "Knoten Hamburg (Südkopf)"),
    ]
    rows = [
        _row("BP_C-48", bezeichnung="Großknoten Hamburg", massnahme="Kreuzungsbauwerk Wilhelmsburg"),
        _row("BP_A-37", bezeichnung="Großknoten Hamburg",
             massnahme="Überwerfungsbauwerk Meckelfeld, 4gl� Ausbau in Meckelfeld"),
        _row("BP_C-99", bezeichnung="Großknoten Hamburg", massnahme="Gleis 25"),
    ]

    out = suggest_rows(rows, projects, {})

    assert preselection(out["BP_C-48"], 0.85)[0] == [2]
    assert preselection(out["BP_A-37"], 0.85)[0] == [3]
    # Nothing fits: the parent is a hint only, and the Bezeichnung alone does
    # not make "Knoten Hamburg (Südkopf)" a match.
    assert preselection(out["BP_C-99"], 0.85) == ([], None)
    assert out["BP_C-99"][0]["project_id"] == 1
    assert out["BP_C-99"][0]["confidence"] < 0.85


def test_context_takes_every_fully_named_subproject():
    projects = [
        ProjectRef(1, "ABS/NBS Leipzig – Dresden (VDE 9)"),
        ProjectRef(2, "3. Baustufe: Riesa – Dresden Neustadt (VDE 9)", superior_project_id=1),
        ProjectRef(3, "Knoten Riesa", superior_project_id=2),
        ProjectRef(4, "Riesa – Abzweig Röderau", superior_project_id=2),
        ProjectRef(5, "Abzweig Röderau – Abzweig Zeithain", superior_project_id=2),
        ProjectRef(6, "Weißig – Böhla", superior_project_id=2),
    ]
    row = _row("BP_B-22", bezeichnung="ABS Leipzig– Dresden (VDE 9)",
               massnahme="3� Baustufe: Knoten Riesa inkl� Röderau - Zeithain")

    out = suggest_rows([row], projects, {})

    assert sorted(preselection(out["BP_B-22"], 0.85)[0]) == [3, 4, 5]


def test_context_stays_a_suggestion_next_to_unnamed_subprojects():
    projects = [
        ProjectRef(1, "Knoten München"),
        ProjectRef(2, "Knoten München Teilmaßnahme 1", superior_project_id=1),
        ProjectRef(3, "Knoten München Teilmaßnahme 2", superior_project_id=1),
        ProjectRef(4, "ABS Knoten München-Riem", superior_project_id=1),
    ]
    row = _row("BP_B-17", bezeichnung="Großknoten München", massnahme="2gl� Neubau MU Daglfing - MU Riem")

    out = suggest_rows([row], projects, {})

    assert preselection(out["BP_B-17"], 0.85) == ([], None)
    best = out["BP_B-17"][0]
    assert (best["project_id"], best["reason"]) == (4, "CONTEXT")
    assert "ohne Namen" in best["detail"]


def test_previous_year_by_text_carries_the_note():
    from dashboard_backend.tasks.infraplan_matching import PreviousLink, PreviousYear, row_text_key

    old = _row("BP_A-7", bezeichnung="Kombinierter Verkehr/Rangierbahnhöfe", massnahme="Ubf Kornwestheim: 3� Modul")
    new = _row("BP_B-3", bezeichnung="Kombinierter Verkehr/Rangierbahnhöfe", massnahme="Ubf Kornwestheim: 3. Modul")
    previous = PreviousYear(
        by_text={row_text_key(old): [PreviousLink(7, "Name und Ort stimmen")]},
        years={f"t:{row_text_key(old)}": 2026},
    )

    out = suggest_rows([new], [ProjectRef(7, "Umschlagbahnhof Kornwestheim, 1.Baustufe")], previous)

    suggestion = out["BP_B-3"][0]
    assert (suggestion["project_id"], suggestion["reason"], suggestion["confidence"]) == (7, "PREVIOUS_YEAR", 0.95)
    assert suggestion["previous_note"] == "Name und Ort stimmen"
    from dashboard_backend.tasks.infraplan_matching import preselection_note

    assert preselection_note(out["BP_B-3"], [7]) == "Vorjahr 2026: Name und Ort stimmen"


def test_project_number_of_a_row_matches_the_project():
    out = suggest_rows(
        [_row("INVKG-1", primary_number="InvKG Nr. 6", massnahme="Strecke Lübbenau-Cottbus")],
        [ProjectRef(5, "Zweigleisiger Ausbau Lübbenau – Cottbus", project_number="InvKG Nr. 6")],
        {},
    )

    assert out["INVKG-1"][0] == {"project_id": 5, "confidence": 1.0, "reason": "NUMBER", "detail": "Projektnummer"}
