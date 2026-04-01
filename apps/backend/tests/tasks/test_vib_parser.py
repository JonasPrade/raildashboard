"""Unit tests for VIB parser helper functions."""
import pytest
from dashboard_backend.tasks.vib import _is_two_column_page, _extract_page_text_columns


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
