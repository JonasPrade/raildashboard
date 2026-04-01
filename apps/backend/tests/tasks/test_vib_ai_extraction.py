from dashboard_backend.tasks.vib_ai_extraction import _merge_ai_result


class TestMergeAiResult:
    def _base_entry(self) -> dict:
        return {
            "vib_section": "B.4.1.1",
            "vib_name_raw": "Test",
            "category": "laufend",
            "raw_text": "raw",
            "bauaktivitaeten": None,
            "teilinbetriebnahmen": None,
            "verkehrliche_zielsetzung": None,
            "durchgefuehrte_massnahmen": None,
            "noch_umzusetzende_massnahmen": None,
            "planungsstand": None,
            "project_status": None,
            "strecklaenge_km": None,
            "gesamtkosten_mio_eur": None,
            "entwurfsgeschwindigkeit": None,
            "pfa_entries": [],
            "project_id": None,
            "suggested_project_ids": [],
            "vib_lfd_nr": None,
        }

    def test_merges_text_fields(self):
        entry = self._base_entry()
        ai = {"bauaktivitaeten": "Gleiserneuerung", "project_status": "Bau"}
        result = _merge_ai_result(entry, ai)
        assert result["bauaktivitaeten"] == "Gleiserneuerung"
        assert result["project_status"] == "Bau"
        assert result["ai_extracted"] is True

    def test_merges_numeric_fields(self):
        entry = self._base_entry()
        ai = {"strecklaenge_km": "42.5", "gesamtkosten_mio_eur": 1200}
        result = _merge_ai_result(entry, ai)
        assert result["strecklaenge_km"] == 42.5
        assert result["gesamtkosten_mio_eur"] == 1200.0

    def test_invalid_float_is_skipped(self):
        entry = self._base_entry()
        ai = {"strecklaenge_km": "not-a-number"}
        result = _merge_ai_result(entry, ai)
        assert result["strecklaenge_km"] is None

    def test_pfa_entries_replaced(self):
        entry = self._base_entry()
        ai = {"pfa_entries": [{"nr_pfa": "1", "oertlichkeit": "Berlin"}]}
        result = _merge_ai_result(entry, ai)
        assert result["pfa_entries"] == [{"nr_pfa": "1", "oertlichkeit": "Berlin"}]

    def test_null_ai_values_do_not_overwrite(self):
        entry = self._base_entry()
        entry["bauaktivitaeten"] = "existing value"
        ai = {"bauaktivitaeten": None}
        result = _merge_ai_result(entry, ai)
        assert result["bauaktivitaeten"] == "existing value"
