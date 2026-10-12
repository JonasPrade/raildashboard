"""Unit tests for the per-group skipped planning phases (#164)."""

from __future__ import annotations

from types import SimpleNamespace

from dashboard_backend.crud.projects.progress import (
    resolve_hidden_phases,
    resolve_skipped_phases,
)
from dashboard_backend.models.projects.progress_enums import MainPhase


def _project(*group_skips: list[str]) -> SimpleNamespace:
    return SimpleNamespace(
        project_groups=[SimpleNamespace(skipped_phases=skips) for skips in group_skips]
    )


def test_no_groups_skip_nothing():
    assert resolve_skipped_phases(_project()) == set()


def test_single_group_skips_its_phases():
    assert resolve_skipped_phases(_project(["VORPLANUNG", "GENEHMIGUNGSPLANUNG"])) == {
        MainPhase.VORPLANUNG,
        MainPhase.GENEHMIGUNGSPLANUNG,
    }


def test_phase_skipped_only_when_all_groups_skip_it():
    project = _project(["VORPLANUNG", "GENEHMIGUNGSPLANUNG"], ["GENEHMIGUNGSPLANUNG"], [])
    assert resolve_skipped_phases(project) == set()
    project = _project(["VORPLANUNG", "GENEHMIGUNGSPLANUNG"], ["GENEHMIGUNGSPLANUNG"])
    assert resolve_skipped_phases(project) == {MainPhase.GENEHMIGUNGSPLANUNG}


def test_null_and_unknown_values_are_ignored():
    assert resolve_skipped_phases(_project(None)) == set()
    assert resolve_skipped_phases(_project(["VORPLANUNG", "BOGUS"])) == {MainPhase.VORPLANUNG}


def test_hidden_phases_keep_phases_in_use():
    skipped = {MainPhase.VORPLANUNG, MainPhase.GENEHMIGUNGSPLANUNG}
    assert resolve_hidden_phases(skipped, {MainPhase.NICHT_GESTARTET}) == [
        "VORPLANUNG",
        "GENEHMIGUNGSPLANUNG",
    ]
    # Data wins: the project currently sits in Genehmigungsplanung.
    assert resolve_hidden_phases(skipped, {MainPhase.GENEHMIGUNGSPLANUNG}) == ["VORPLANUNG"]
