"""Fulda-Runde categories and derivation (feature-fulda-import.md)."""

from __future__ import annotations

from datetime import date

from dashboard_backend.models.projects.progress_enums import DatePrecision, MainPhase, SourceType
from dashboard_backend.services.fulda_categories import (
    FULDA_CATEGORY_LIST,
    IST,
    NEUAUFNAHME,
    OHNE_FOLGEPHASE,
    PROGNOSE,
    get_category,
)
from dashboard_backend.services.progress_derivation import SOURCE_TYPE_DEFAULT_TRUST
from dashboard_backend.services.progress_materialization import fulda_to_spec

DOC_DATE = date(2026, 6, 3)


def _spec(category, expected_date=None):
    return fulda_to_spec(
        fulda_announcement_id=1,
        category=category,
        document_date=DOC_DATE,
        expected_date=expected_date,
        drucksache="21/5855",
    )


def test_trust_is_below_vib():
    assert SOURCE_TYPE_DEFAULT_TRUST[SourceType.FULDA_RUNDE] == 0.55
    assert (
        SOURCE_TYPE_DEFAULT_TRUST[SourceType.MEDIEN]
        < SOURCE_TYPE_DEFAULT_TRUST[SourceType.FULDA_RUNDE]
        < SOURCE_TYPE_DEFAULT_TRUST[SourceType.VIB]
    )


def test_catalog_keys_are_unique_and_kinds_known():
    keys = [c.key for c in FULDA_CATEGORY_LIST]
    assert len(keys) == len(set(keys))
    assert {c.kind for c in FULDA_CATEGORY_LIST} == {IST, OHNE_FOLGEPHASE, PROGNOSE, NEUAUFNAHME}
    assert get_category("in_lph_3_4").key == "IN_LPH_3_4"
    assert get_category("nope") is None
    assert get_category(None) is None


def test_ist_line_asserts_phase_at_document_date():
    spec = _spec("IN_LPH_3_4")
    assert spec.source_type is SourceType.FULDA_RUNDE
    assert spec.asserted_state == MainPhase.GENEHMIGUNGSPLANUNG.value
    assert spec.observed_date == DOC_DATE
    assert spec.is_expected is False
    assert spec.confidence is None  # source default (0.55)
    assert spec.note == "Fulda-Runde (Drs. 21/5855)"


def test_completed_without_followup_keeps_the_phase():
    assert _spec("COMPLETED_LPH_1_2_NO_FOLLOWUP").asserted_state == MainPhase.VORPLANUNG.value
    assert _spec("COMPLETED_LPH_3_4_NO_FOLLOWUP").asserted_state == "GENEHMIGUNGSPLANUNG"


def test_prognosis_is_an_expected_date_not_a_phase():
    spec = _spec("COMPLETES_LPH_3_4", expected_date=date(2026, 12, 31))
    assert spec.is_expected is True
    assert spec.asserted_state == MainPhase.BAU.value
    assert spec.observed_date == date(2026, 12, 31)


def test_prognosis_without_date_falls_back_to_year_end():
    spec = _spec("NEW_BAUFINVE")
    assert spec.is_expected is True
    assert spec.observed_date == date(2026, 12, 31)


def test_hint_only_and_unknown_categories_yield_nothing():
    assert _spec("COMPLETES_LPH_1") is None
    assert _spec("bogus") is None


def test_fallback_year_end_is_year_only():
    assert _spec("NEW_BAUFINVE").date_precision is DatePrecision.YEAR
    assert _spec("COMPLETES_LPH_3_4", expected_date=date(2027, 3, 1)).date_precision is DatePrecision.EXACT
