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
            "status_planung": False,
            "status_bau": False,
            "status_abgeschlossen": False,
            "strecklaenge_km": None,
            "gesamtkosten_mio_eur": None,
            "entwurfsgeschwindigkeit": None,
            "pfa_entries": [],
            "project_ids": [],
            "suggested_project_ids": [],
            "vib_lfd_nr": None,
        }

    def test_merges_text_fields(self):
        entry = self._base_entry()
        ai = {"bauaktivitaeten": "Gleiserneuerung"}
        result = _merge_ai_result(entry, ai)
        assert result["bauaktivitaeten"] == "Gleiserneuerung"
        assert result["ai_extracted"] is True

    def test_merges_status_booleans(self):
        entry = self._base_entry()
        ai = {"status_bau": True, "status_planung": False}
        result = _merge_ai_result(entry, ai)
        assert result["status_bau"] is True
        assert result["status_planung"] is False

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

    def test_list_coerced_to_string(self):
        entry = self._base_entry()
        ai = {"noch_umzusetzende_massnahmen": ["Teil 1", "Teil 2"]}
        result = _merge_ai_result(entry, ai)
        assert result["noch_umzusetzende_massnahmen"] == "Teil 1\nTeil 2"

    def test_teilinbetriebnahmen_keine_normalized(self):
        entry = self._base_entry()
        ai = {"teilinbetriebnahmen": "- Keine."}
        result = _merge_ai_result(entry, ai)
        assert result["teilinbetriebnahmen"] is None
