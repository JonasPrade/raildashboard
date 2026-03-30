"""Unit tests for tasks/finve_matching.py.

Tests cover normalisation, scoring, and project suggestion logic.
No DB access required — all pure Python.
"""
from __future__ import annotations

import pytest

from dashboard_backend.tasks.finve_matching import (
    _normalize,
    _score,
    suggest_projects_for_finve,
    suggest_per_erlaeuterung_project,
    suggest_projects_for_sv_erlaeuterung,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeProject:
    """Minimal stand-in for a Project ORM object."""

    def __init__(self, project_id: int, name: str):
        self.id = project_id
        self.name = name


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------


def test_normalize_lowercases():
    assert _normalize("ABS HAMBURG") == "hamburg"


def test_normalize_strips_abs_prefix():
    assert _normalize("ABS Hamburg–Kiel") == "hamburg kiel"


def test_normalize_strips_nbs_prefix():
    assert _normalize("NBS München") == "münchen"


def test_normalize_strips_abs_nbs_prefix():
    assert _normalize("ABS/NBS Frankfurt") == "frankfurt"


def test_normalize_replaces_hyphens():
    assert _normalize("Hamburg-Kiel") == "hamburg kiel"


def test_normalize_collapses_whitespace():
    assert _normalize("  A   B  ") == "a b"


def test_normalize_unicode_nfc():
    # Precomposed ä vs combining a + umlaut
    precomposed = "\xe4"
    combining = "a\u0308"
    assert _normalize(precomposed) == _normalize(combining)


def test_normalize_empty_string():
    assert _normalize("") == ""


# ---------------------------------------------------------------------------
# _score
# ---------------------------------------------------------------------------


def test_score_identical_names():
    assert _score("Hamburg Kiel", "Hamburg Kiel") == pytest.approx(1.0)


def test_score_completely_different():
    s = _score("AAAA", "ZZZZ")
    assert s < 0.3


def test_score_same_after_strip():
    # "ABS Hamburg" and "Hamburg" should score above threshold
    s = _score("ABS Hamburg", "Hamburg")
    assert s >= 0.45


def test_score_reversed_tokens():
    # Token-set bonus handles reordering — score is high but not necessarily 1.0
    s = _score("Berlin Frankfurt", "Frankfurt Berlin")
    assert s >= 0.7


def test_score_empty_strings():
    assert _score("", "") == 0.0
    assert _score("Hamburg", "") == 0.0


# ---------------------------------------------------------------------------
# suggest_projects_for_finve
# ---------------------------------------------------------------------------


def test_suggest_projects_returns_best_match():
    projects = [
        FakeProject(1, "ABS Hamburg–Kiel"),
        FakeProject(2, "NBS München–Augsburg"),
        FakeProject(3, "Completely Unrelated"),
    ]
    suggestions = suggest_projects_for_finve("ABS Hamburg–Kiel", projects)
    assert 1 in suggestions


def test_suggest_projects_respects_threshold():
    projects = [FakeProject(1, "ZZZZ Unrelated"), FakeProject(2, "Another Different")]
    suggestions = suggest_projects_for_finve("ABS Hamburg–Kiel", projects)
    assert suggestions == []


def test_suggest_projects_max_three():
    projects = [FakeProject(i, f"Hamburg Variation {i}") for i in range(10)]
    suggestions = suggest_projects_for_finve("Hamburg", projects)
    assert len(suggestions) <= 3


def test_suggest_projects_skips_empty_name():
    projects = [FakeProject(1, ""), FakeProject(2, "Hamburg–Kiel")]
    suggestions = suggest_projects_for_finve("ABS Hamburg–Kiel", projects)
    assert 1 not in suggestions


# ---------------------------------------------------------------------------
# suggest_per_erlaeuterung_project  (1:1 per name, allows duplicates)
# ---------------------------------------------------------------------------


def test_suggest_per_erlaeuterung_length_matches_input():
    projects = [FakeProject(1, "Hamburg Kiel"), FakeProject(2, "München Augsburg")]
    names = ["Hamburg Kiel", "München Augsburg", "No Match Anywhere"]
    result = suggest_per_erlaeuterung_project(names, projects)
    assert len(result) == 3
    assert result[0] == 1
    assert result[1] == 2
    assert result[2] is None


# ---------------------------------------------------------------------------
# suggest_projects_for_sv_erlaeuterung  (deduplicated)
# ---------------------------------------------------------------------------


def test_suggest_sv_deduplicates():
    projects = [FakeProject(1, "Hamburg Kiel")]
    # Two names that both match project 1
    names = ["Hamburg Kiel", "Hamburg Kiel"]
    result = suggest_projects_for_sv_erlaeuterung(names, projects)
    assert result.count(1) == 1
