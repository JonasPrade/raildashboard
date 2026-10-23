"""Unit tests for the PFA → subproject suggestion in tasks/vib_matching
(feature-vib-import.md → Phase 8). The cases follow real VIB 2023 tables."""

from dataclasses import dataclass

from dashboard_backend.tasks.vib_matching import (
    pfa_row_key,
    place_stop_tokens,
    project_section_numbers,
    suggest_subproject_for_pfa,
)


@dataclass
class FakeProject:
    id: int
    name: str
    project_number: str | None = None


def _suggest(nr, ort, candidates, label=None, stop=frozenset()):
    return suggest_subproject_for_pfa(nr, ort, label, candidates, stop)


# Karlsruhe–Basel: the sections are grandchildren of the linked bundle.
KARLSRUHE = [
    (FakeProject(1504, "ABS/NBS Karlsruhe - Basel"), 1),
    (FakeProject(1503, "ABS Kehl - Appenweier"), 1),
    (FakeProject(2203, "ABS/NBS Karlsruhe – Basel, Abschnitt 1 Karlsruhe – Rastatt Süd", "2-005-V02-Abschnitt1"), 2),
    (FakeProject(2204, "ABS/NBS Karlsruhe – Basel, Abschnitt 2-6 Rastatt Süd – Offenburg", "2-005-V02-Abschnitt2-6"), 2),
    (FakeProject(2205, "ABS/NBS Karlsruhe – Basel, Abschnitt 7 Appenweier Kenzingen", "2-005-V02-Abschnitt7"), 2),
    (FakeProject(2206, "ABS/NBS Karlsruhe – Basel, Abschnitt 8 Kenzingen – Müllheim", "2-005-V02-Abschnitt8"), 2),
]

# Nürnberg–Erfurt: the numbers sit in the project number.
NUERNBERG = [
    (FakeProject(1860, "Nürnberg - Erfurt (VDE 8.1) Teilmaßnahnme 4", "2-010-V07 TM4"), 1),
    (FakeProject(1861, "Nürnberg - Erfurt (VDE 8.1) Teilmaßnahnme 5", "2-010-V07 TM5"), 1),
    (FakeProject(2222, "VDE 8 Neubaustrecke Ebensfeld – Erfurt Stadt", "BSWAG 2023 FD 4 PFA 1+2"), 1),
    (FakeProject(2223, "VDE 8 Teilabschnittt Nürnberg Hbf – Fürth", "BSWAG 2023 FD 4 PF 11, 14"), 1),
    (FakeProject(2224, "VDE 8 Güterzugtunnel Fürth", "BSWAG 2023 FD 4 PF 13"), 1),
    (FakeProject(2225, "VDE 8 Fürth – Eltersdorf", "BSWAG 2023 FD 4 PF 15-16"), 1),
    (FakeProject(2227, "VDE 8 Baiersdorf – Forchheim", "BSWAG 2023 FD 4 PF 18"), 1),
    (FakeProject(2231, "VDE 8 Hallstadt – Ebensfeld", "BSWAG 2023 FD 4 PF 23-25"), 1),
]
NUERNBERG_STOP = place_stop_tokens("Lfd. Vorhaben Nr. 9 – ABS/NBS Nürnberg–Erfurt (VDE Nr. 8.1)")


def test_section_numbers_of_projects():
    assert project_section_numbers("Abschnitt 7 Appenweier", "2-005-V02-Abschnitt7") == {"7"}
    assert project_section_numbers(None, "2-005-V02-Abschnitt2-6") == {"2", "3", "4", "5", "6"}
    assert project_section_numbers(None, "BSWAG 2023 FD 4 PF 11, 14") == {"11", "14"}
    assert project_section_numbers(None, "BSWAG 2023 FD 4 PFA 1+2") == {"1", "2"}
    assert project_section_numbers("RRX Abschnitt 3 Düsseldorf Wehrhahn – Abzw. Duisburg") == {"3"}
    # No keyword, no number: VDE, Teilmaßnahme, place names with "Pf"/"Ba".
    assert project_section_numbers("Nürnberg - Erfurt (VDE 8.1) Teilmaßnahnme 5", "2-010-V07 TM5") == set()
    assert project_section_numbers("Pfaffenhofen – Bamberg 2") == set()


def test_main_number_matches_the_grandchild_not_a_foreign_sibling():
    # Today: 7.1 → "ABS Kehl - Appenweier" (wrong) and the grandchildren are never seen.
    s = _suggest("7.1", "Appenweier-Hohberg", KARLSRUHE)
    assert s.project_id == 2205 and s.kind == "nummer" and s.strong
    assert "7" in s.reason
    assert _suggest("1", "Karlsruhe-Rastatt Süd", KARLSRUHE).project_id == 2203
    assert _suggest("2–6", "Rastatt Süd-Offenburg", KARLSRUHE).project_id == 2204
    assert _suggest("8.4", "Bad Krotzingen–Müllheim (NBS)", KARLSRUHE).project_id == 2206


def test_numbers_in_project_number_lists_and_ranges():
    assert _suggest("11", "Nürnberg Hbf (km 0,00–km 1,75)", NUERNBERG, stop=NUERNBERG_STOP).project_id == 2223
    assert _suggest("14", "Nürnberg–Fürth (km 1,75–km 4,517)", NUERNBERG, stop=NUERNBERG_STOP).project_id == 2223
    assert _suggest("16b", "Fürth Nord (km 12,40–km 16,40)", NUERNBERG, stop=NUERNBERG_STOP).project_id == 2225
    assert _suggest("2.4", "Erfurt Land (km 94,450–km 102,050)", NUERNBERG, stop=NUERNBERG_STOP).project_id == 2222
    assert _suggest("24", "Zapfendorf (km 8,950–km 15,100)", NUERNBERG, stop=NUERNBERG_STOP).project_id == 2231


def test_exact_number_beats_main_number():
    cands = [(FakeProject(1, "PFA 3 Gesamt"), 1), (FakeProject(2, "PFA 3.1 Nord"), 1)]
    assert _suggest("3.1", None, cands).project_id == 2
    assert _suggest("3.2", None, cands).project_id == 1


def test_deeper_project_wins_on_equal_number():
    cands = [(FakeProject(1, "Abschnitt 4 Mitte"), 1), (FakeProject(2, "Abschnitt 4 Mitte, Bauabschnitt"), 2)]
    assert _suggest("4", None, cands).project_id == 2


def test_ambiguous_number_falls_back_to_the_name():
    cands = [(FakeProject(1, "PFA 5 Essen"), 1), (FakeProject(2, "PFA 5 Bochum"), 1)]
    s = _suggest("5", "Stadtgebiet Bochum", cands)
    assert s.project_id == 2 and s.kind == "name" and not s.strong
    assert _suggest("5", "Stadtgebiet Dortmund", cands) is None


def test_place_name_match_without_number():
    cands = [
        (FakeProject(1, "Abschnitt Bad Kleinen – Rostock"), 1),
        (FakeProject(2, "Abschnitt Lübeck – Schönberg"), 1),
    ]
    stop = place_stop_tokens("ABS Lübeck/Hagenow Land–Rostock–Stralsund")
    s = _suggest("2.1", "Bad Kleinen", cands, label="Bad Kleinen – Rostock", stop=stop)
    assert s.project_id == 1 and s.kind == "name"


def test_names_of_the_whole_line_do_not_decide():
    # "Nürnberg" is in the Vorhaben name: "Nürnberg Hbf" must not land on a
    # "Nürnberg - Erfurt Teilmaßnahme" (today's wrong suggestion).
    tm = [(FakeProject(1861, "Nürnberg - Erfurt (VDE 8.1) Teilmaßnahnme 5"), 1)]
    assert _suggest(None, "Nürnberg Hbf", tm, stop=NUERNBERG_STOP) is None
    # A subproject that only repeats the parent's name gets nothing either.
    dup = [(FakeProject(2250, "VDE 1 - ABS Lübeck/Hagenow Land – Rostock – Stralsund"), 1)]
    stop = place_stop_tokens("Lfd. Vorhaben Nr. 2 – ABS Lübeck/Hagenow Land–Rostock–Stralsund (VDE Nr. 1)")
    assert _suggest("2", "Hagenow Land-Schwerin (a)", dup, label="Hagenow Land-Bad Kleinen (a)", stop=stop) is None


def test_close_runner_up_gives_no_name_suggestion():
    cands = [(FakeProject(1, "Fürth – Eltersdorf"), 1), (FakeProject(2, "Fürth – Erlangen"), 1)]
    assert _suggest(None, "Fürth", cands) is None


def test_empty_input():
    assert _suggest(None, None, KARLSRUHE) is None
    assert _suggest("", "   ", KARLSRUHE) is None
    assert _suggest("7.1", "Appenweier", []) is None
    assert _suggest(None, "Hanau", [(FakeProject(9, ""), 1)]) is None


def test_row_key_ignores_noise():
    assert pfa_row_key("3.0a¹", "Düsseldorf-Unterrath (a) – Kalkum (km 1,2–3,4)") == pfa_row_key(
        "3.0a", "Düsseldorf-Unterrath – Kalkum"
    )
    assert pfa_row_key("2–6", None) == ("2-6", "")


def test_free_text_section_name_match_for_fulda():
    from dashboard_backend.tasks.vib_matching import suggest_subproject_by_name

    subs = [FakeProject(1, "PFA 1 Frankfurt – Hanau"), FakeProject(2, "PFA 2 Hanau – Gelnhausen"),
            FakeProject(9, "")]
    assert suggest_subproject_by_name("Hanau – Gelnhausen", subs) == 2
    assert suggest_subproject_by_name("Komplett anderer Ort", subs) is None
    assert suggest_subproject_by_name("  ", subs) is None
