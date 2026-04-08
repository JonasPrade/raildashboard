"""Tests for VIB Pydantic schema changes (m:n project relation)."""
from dashboard_backend.schemas.vib import VibEntryProposed, VibConfirmEntryInput


class TestVibEntryProposedM2n:
    def test_has_project_ids_not_project_id(self):
        entry = VibEntryProposed(vib_name_raw="Test")
        assert hasattr(entry, "project_ids")
        assert not hasattr(entry, "project_id")

    def test_project_ids_defaults_to_empty_list(self):
        entry = VibEntryProposed(vib_name_raw="Test")
        assert entry.project_ids == []

    def test_project_ids_accepts_multiple(self):
        entry = VibEntryProposed(vib_name_raw="Test", project_ids=[1, 2, 3])
        assert entry.project_ids == [1, 2, 3]


class TestVibConfirmEntryInputM2n:
    def test_has_project_ids_not_project_id(self):
        entry = VibConfirmEntryInput(vib_name_raw="Test")
        assert hasattr(entry, "project_ids")
        assert not hasattr(entry, "project_id")

    def test_project_ids_defaults_to_empty_list(self):
        entry = VibConfirmEntryInput(vib_name_raw="Test")
        assert entry.project_ids == []
