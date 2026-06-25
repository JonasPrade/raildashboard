"""Unit tests for tasks/vib_matching.suggest_subproject_for_pfa.

Pure Python — no DB access; subprojects are minimal stand-ins.
"""
from __future__ import annotations

from dashboard_backend.tasks.vib_matching import suggest_subproject_for_pfa


class FakeProject:
    """Minimal stand-in for a Project ORM object (.id, .name)."""

    def __init__(self, project_id: int, name: str):
        self.id = project_id
        self.name = name


SUBPROJECTS = [
    FakeProject(1, "PFA 1 Frankfurt – Hanau"),
    FakeProject(2, "PFA 2 Hanau – Gelnhausen"),
    FakeProject(3, "PFA 3 Gelnhausen – Fulda"),
]


def test_suggests_best_matching_subproject():
    assert suggest_subproject_for_pfa("Hanau – Gelnhausen", SUBPROJECTS) == 2


def test_no_match_below_threshold_returns_none():
    assert suggest_subproject_for_pfa("Komplett anderer Ort", SUBPROJECTS) is None


def test_empty_text_returns_none():
    assert suggest_subproject_for_pfa("", SUBPROJECTS) is None
    assert suggest_subproject_for_pfa("   ", SUBPROJECTS) is None


def test_no_subprojects_returns_none():
    assert suggest_subproject_for_pfa("Frankfurt – Hanau", []) is None


def test_subproject_without_name_is_skipped():
    subs = [FakeProject(9, ""), FakeProject(1, "PFA 1 Frankfurt – Hanau")]
    assert suggest_subproject_for_pfa("Frankfurt – Hanau", subs) == 1
