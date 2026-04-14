"""Tests for VibEntryUpdateSchema and VibEntrySchema."""
from dashboard_backend.schemas.vib import VibEntryUpdateSchema, VibEntrySchema, VibPfaEntrySchema


def test_vib_entry_update_schema_all_optional():
    # An empty payload must be valid
    schema = VibEntryUpdateSchema()
    assert schema.vib_name_raw is None
    assert schema.pfa_entries is None
    assert schema.project_ids is None


def test_vib_entry_update_schema_partial():
    schema = VibEntryUpdateSchema(vib_name_raw="New Name", status_bau=True)
    assert schema.vib_name_raw == "New Name"
    assert schema.status_bau is True
    assert schema.bauaktivitaeten is None  # not provided


def test_vib_entry_schema_has_project_ids_and_report_year():
    pfa = VibPfaEntrySchema(id=1, nr_pfa="PFA-1")
    schema = VibEntrySchema(
        id=42,
        vib_report_id=5,
        vib_name_raw="Test",
        category="laufend",
        status_planung=False,
        status_bau=False,
        status_abgeschlossen=False,
        ai_extracted=False,
        project_ids=[1, 2],
        report_year=2024,
        pfa_entries=[pfa],
    )
    assert schema.project_ids == [1, 2]
    assert schema.report_year == 2024
    assert len(schema.pfa_entries) == 1
