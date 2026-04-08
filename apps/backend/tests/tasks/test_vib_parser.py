"""Unit tests for VIB parser helper functions."""
import pytest
from dashboard_backend.tasks.vib import _is_two_column_page, _extract_page_text_columns
from dashboard_backend.tasks.vib import _VORHABEN_SECTION_RE


def _make_word(x0: float, top: float, text: str) -> dict:
    return {"x0": x0, "top": top, "text": text}


class TestIsTwoColumnPage:
    def test_empty_words_returns_false(self):
        assert _is_two_column_page([]) is False

    def test_all_left_column_is_single_column(self):
        words = [_make_word(50, i * 10, "word") for i in range(20)]
        assert _is_two_column_page(words) is False

    def test_mixed_columns_is_two_column(self):
        left = [_make_word(50, i * 10, "left") for i in range(10)]
        right = [_make_word(300, i * 10, "right") for i in range(5)]
        assert _is_two_column_page(left + right) is True

    def test_exactly_15_percent_right_is_two_column(self):
        left = [_make_word(50, i * 10, "l") for i in range(17)]
        right = [_make_word(300, i * 10, "r") for i in range(3)]
        assert _is_two_column_page(left + right) is True

    def test_under_threshold_is_single_column(self):
        left = [_make_word(50, i * 10, "l") for i in range(98)]
        right = [_make_word(300, i * 10, "r") for i in range(2)]
        assert _is_two_column_page(left + right) is False


class TestVorhabenSectionRe:
    def test_matches_standard_format(self):
        m = _VORHABEN_SECTION_RE.search("B.4.1.3  Some long heading with artifacts")
        assert m is not None
        assert (m.group(1) or m.group(2)).replace(" ", ".") == "B.4.1.3"

    def test_matches_ocr_space_variant(self):
        m = _VORHABEN_SECTION_RE.search("B 4.2.1  Heading text")
        assert m is not None
        assert (m.group(1) or m.group(2)).replace(" ", ".") == "B.4.2.1"

    def test_matches_markdown_heading_format(self):
        m = _VORHABEN_SECTION_RE.search("# B.4.1.3  Heading with hash prefix")
        assert m is not None
        assert (m.group(1) or m.group(2)).replace(" ", ".") == "B.4.1.3"

    def test_matches_double_hash_heading(self):
        m = _VORHABEN_SECTION_RE.search("## B.4.2.5  Another heading")
        assert m is not None
        assert (m.group(1) or m.group(2)).replace(" ", ".") == "B.4.2.5"

    def test_does_not_match_toc_subsection(self):
        # B.4 without two trailing levels must not match
        m = _VORHABEN_SECTION_RE.search("B.4.1  Section overview")
        assert m is None

    def test_matches_multiline(self):
        text = "Some preamble\nB.4.1.5\nMore content"
        m = _VORHABEN_SECTION_RE.search(text)
        assert m is not None


from dashboard_backend.tasks.vib import _extract_status_flags


class TestExtractStatusFlags:
    def test_detects_bau(self):
        _, bau, _ = _extract_status_flags("Projektstand: Bau\nEinige weitere Infos")
        assert bau is True

    def test_detects_planung(self):
        planung, _, _ = _extract_status_flags("Planungsstand: Planung\nDetails")
        assert planung is True

    def test_returns_all_false_when_absent(self):
        assert _extract_status_flags("Kein Hinweis auf Status") == (False, False, False)

    def test_returns_all_false_for_none_input(self):
        assert _extract_status_flags(None) == (False, False, False)

    def test_case_insensitive_bau(self):
        _, bau, _ = _extract_status_flags("Status: bau")
        assert bau is True

    def test_case_insensitive_planung(self):
        planung, _, _ = _extract_status_flags("Status: planung")
        assert planung is True

    def test_detects_abgeschlossen(self):
        _, _, abgeschlossen = _extract_status_flags("Der Abschnitt ist abgeschlossen.")
        assert abgeschlossen is True

    def test_multiple_flags(self):
        planung, bau, _ = _extract_status_flags("Planung läuft, Bau begonnen")
        assert planung is True
        assert bau is True


class TestVibEntryProposedProjectIds:
    """Parser must produce project_ids (list), not project_id (scalar)."""

    def test_suggested_ids_become_project_ids(self):
        from dashboard_backend.schemas.vib import VibEntryProposed
        entry = VibEntryProposed(
            vib_name_raw="Test",
            project_ids=[42],
            suggested_project_ids=[42],
        )
        assert entry.project_ids == [42]
        assert not hasattr(entry, "project_id")

    def test_no_suggestions_gives_empty_project_ids(self):
        from dashboard_backend.schemas.vib import VibEntryProposed
        entry = VibEntryProposed(vib_name_raw="Test")
        assert entry.project_ids == []
