"""Unit tests for the superior-project (Über-/Unterprojekt) hierarchy rules."""
from __future__ import annotations

import pytest

from dashboard_backend.crud.projects.projects import (
    ProjectHierarchyError,
    ancestor_ids,
    check_superior_project,
)

# tree: 1 → 2 → 3 (3 is the deepest child), 4 is a separate root
TREE = {1: None, 2: 1, 3: 2, 4: None}


def _parent_of(project_id: int):
    return TREE.get(project_id)


def _exists(project_id: int) -> bool:
    return project_id in TREE


def _check(project_id, superior_project_id, tree=None):
    parents = TREE if tree is None else tree
    check_superior_project(
        project_id,
        superior_project_id,
        exists=lambda pid: pid in parents,
        parent_of=parents.get,
    )


class TestAncestorIds:
    def test_returns_chain_nearest_first(self):
        assert ancestor_ids(3, _parent_of) == [2, 1]

    def test_root_has_no_ancestors(self):
        assert ancestor_ids(1, _parent_of) == []

    def test_stops_on_corrupt_cycle(self):
        cyclic = {1: 2, 2: 1}
        assert ancestor_ids(1, cyclic.get) == [2]


class TestCheckSuperiorProject:
    def test_allows_unrelated_parent(self):
        _check(3, 4)  # does not raise

    def test_clearing_the_parent_is_always_allowed(self):
        _check(1, None)

    def test_rejects_self_reference(self):
        with pytest.raises(ProjectHierarchyError, match="sich selbst"):
            _check(2, 2)

    def test_rejects_unknown_parent(self):
        with pytest.raises(ProjectHierarchyError, match="existiert nicht"):
            _check(2, 999)

    def test_rejects_direct_child_as_parent(self):
        # 2 is the parent of 3 — making 3 the parent of 2 would close a cycle
        with pytest.raises(ProjectHierarchyError, match="Zyklus"):
            _check(2, 3)

    def test_rejects_deeper_descendant_as_parent(self):
        with pytest.raises(ProjectHierarchyError, match="Zyklus"):
            _check(1, 3)

    def test_new_project_only_needs_an_existing_parent(self):
        _check(None, 1)
        with pytest.raises(ProjectHierarchyError, match="existiert nicht"):
            _check(None, 999)
