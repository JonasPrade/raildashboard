"""Unit tests for the Fulda-Runde importer (#46): category mapping, mapper and
LLM extraction normalisation (mocked — no OCR/network)."""

from __future__ import annotations

import dashboard_backend.tasks.fulda_extraction as fulda_extraction
from dashboard_backend.services.progress_materialization import (
    fulda_category_to_phase,
    fulda_to_spec,
)
from dashboard_backend.tasks.fulda_extraction import (
    extract_fulda_announcements,
    normalize_items,
)


# --- category → phase --------------------------------------------------------


def test_category_phase_mapping():
    assert fulda_category_to_phase("IN_LPH_1_2").value == "VORPLANUNG"
    assert fulda_category_to_phase("IN_LPH_3_4").value == "GENEHMIGUNGSPLANUNG"
    assert fulda_category_to_phase("COMPLETED_LPH_1_2").value == "GENEHMIGUNGSPLANUNG"
    assert fulda_category_to_phase("COMPLETED_LPH_3_4").value == "BAU"
    assert fulda_category_to_phase("HAS_BAUFINVE").value == "BAU"
    assert fulda_category_to_phase("nope") is None
    assert fulda_category_to_phase(None) is None


# --- mapper ------------------------------------------------------------------


def test_fulda_to_spec_from_category():
    spec = fulda_to_spec(
        fulda_announcement_id=9,
        announced_phase=None,
        category="COMPLETED_LPH_3_4",
        observed_date=None,
        source_label="Drs 20/123",
    )
    assert spec is not None
    assert spec.source_type.value == "FULDA_RUNDE"
    assert spec.asserted_state == "BAU"
    assert spec.fulda_announcement_id == 9
    assert spec.confidence is None  # FULDA default 0.7 downstream
    assert "Drs 20/123" in spec.note


def test_fulda_to_spec_announced_phase_overrides_category():
    spec = fulda_to_spec(
        fulda_announcement_id=1,
        announced_phase="IN_BETRIEB",
        category="IN_LPH_1_2",
        observed_date=None,
    )
    assert spec.asserted_state == "IN_BETRIEB"


def test_fulda_to_spec_none_without_phase():
    assert (
        fulda_to_spec(
            fulda_announcement_id=1, announced_phase=None, category="bogus", observed_date=None
        )
        is None
    )


# --- item normalisation ------------------------------------------------------


def test_normalize_items_maps_question_to_category():
    raw = [
        {"question": 1, "project_name": "ABS Augsburg – Donauwörth"},  # → IN_LPH_1_2
        {"question": 6, "project_name": "ABS Hanau – Würzburg"},  # → IN_LPH_3_4
        {"question": 8, "project_name": "ABS Stade – Cuxhaven"},  # → HAS_BAUFINVE (Bau)
        {"question": 13, "project_name": "Budget egal"},  # budget question → dropped
        {"question": 1, "project_name": ""},  # no name → dropped
        {"project_name": "kein Question"},  # no question → dropped
        "garbage",
    ]
    items = normalize_items(raw)
    assert items == [
        {"project_name": "ABS Augsburg – Donauwörth", "category": "IN_LPH_1_2"},
        {"project_name": "ABS Hanau – Würzburg", "category": "IN_LPH_3_4"},
        {"project_name": "ABS Stade – Cuxhaven", "category": "HAS_BAUFINVE"},
    ]


def test_normalize_items_dedupes_same_project_same_question():
    raw = [
        {"question": 1, "project_name": "ABS X", "abschnitt": "Abschnitt A"},
        {"question": 1, "project_name": "ABS X", "abschnitt": "Abschnitt B"},
        {"question": 6, "project_name": "ABS X"},  # different category → kept
    ]
    items = normalize_items(raw)
    assert items == [
        {"project_name": "ABS X", "category": "IN_LPH_1_2"},
        {"project_name": "ABS X", "category": "IN_LPH_3_4"},
    ]


# --- extraction --------------------------------------------------------------


def test_extract_empty_without_llm(monkeypatch):
    monkeypatch.setattr(fulda_extraction.settings, "llm_base_url", "")
    assert extract_fulda_announcements("irgendein Text") == {
        "source_label": None,
        "document_date": None,
        "items": [],
    }


def test_extract_uses_llm(monkeypatch):
    monkeypatch.setattr(fulda_extraction.settings, "llm_base_url", "http://llm.local")
    monkeypatch.setattr(
        fulda_extraction,
        "_call_llm",
        lambda prompt: {
            "source_label": "Drs 20/999",
            "document_date": "2026-01-15",
            "items": [
                {"question": 1, "project_name": "Ausbau A"},
                {"question": 14, "project_name": "Budget"},  # dropped
            ],
        },
    )
    result = extract_fulda_announcements("text")
    assert result["source_label"] == "Drs 20/999"
    assert result["items"] == [{"project_name": "Ausbau A", "category": "IN_LPH_1_2"}]


def test_extract_survives_llm_error(monkeypatch):
    monkeypatch.setattr(fulda_extraction.settings, "llm_base_url", "http://llm.local")

    def _boom(prompt):
        raise RuntimeError("down")

    monkeypatch.setattr(fulda_extraction, "_call_llm", _boom)
    assert extract_fulda_announcements("text")["items"] == []
