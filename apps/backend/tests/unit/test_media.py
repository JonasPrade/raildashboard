"""Unit tests for the Medien/Presse importer (#48): mapper, HTML stripping and
LLM extraction (mocked — no live network)."""

from __future__ import annotations

import datetime

import dashboard_backend.tasks.media_extraction as media_extraction
from dashboard_backend.services.progress_materialization import media_to_spec
from dashboard_backend.tasks.media_extraction import (
    _html_to_text,
    _normalize_phase,
    extract_media_report,
)


# --- mapper ------------------------------------------------------------------


def test_media_to_spec_low_trust_main_with_note():
    spec = media_to_spec(
        media_report_id=4,
        asserted_phase="IN_BETRIEB",
        observed_date=datetime.date(2026, 5, 1),
        publication="Tagesschau",
        url="https://example.org/a",
        quote="Strecke in Betrieb genommen",
    )
    assert spec is not None
    assert spec.source_type.value == "MEDIEN"
    assert spec.track.value == "MAIN"
    assert spec.asserted_state == "IN_BETRIEB"
    assert spec.media_report_id == 4
    assert spec.confidence is None  # MEDIEN default 0.4 applied downstream
    assert "Tagesschau" in spec.note
    assert "in Betrieb genommen" in spec.note


def test_media_to_spec_invalid_phase_returns_none():
    assert (
        media_to_spec(media_report_id=1, asserted_phase=None, observed_date=None) is None
    )
    assert (
        media_to_spec(media_report_id=1, asserted_phase="WHATEVER", observed_date=None)
        is None
    )


# --- HTML stripping ----------------------------------------------------------


def test_html_to_text_strips_tags_scripts_styles():
    html = (
        "<html><head><style>.x{color:red}</style></head>"
        "<body><script>evil()</script><h1>Baubeginn</h1>"
        "<p>Die&nbsp;Strecke &amp; mehr.</p></body></html>"
    )
    text = _html_to_text(html)
    assert "Baubeginn" in text
    assert "Die Strecke & mehr." in text
    assert "evil" not in text
    assert "color:red" not in text


def test_normalize_phase():
    assert _normalize_phase("bau") == "BAU"
    assert _normalize_phase("IN_BETRIEB") == "IN_BETRIEB"
    assert _normalize_phase("nonsense") is None
    assert _normalize_phase(None) is None


# --- extraction --------------------------------------------------------------


def test_extract_returns_empty_without_llm(monkeypatch):
    monkeypatch.setattr(media_extraction.settings, "llm_base_url", "")
    result = extract_media_report("Irgendein Pressetext über ein Bahnprojekt.")
    assert result == {
        "publication": None,
        "published_date": None,
        "project_name": None,
        "phase": None,
        "observed_date": None,
        "quote": None,
    }


def test_extract_uses_llm_and_validates_phase(monkeypatch):
    monkeypatch.setattr(media_extraction.settings, "llm_base_url", "http://llm.local")
    monkeypatch.setattr(
        media_extraction,
        "call_llm_json",
        lambda system_prompt, prompt: {
            "publication": "FAZ",
            "published_date": "2026-03-01",
            "project_name": "Ausbau Hanau–Würzburg",
            "phase": "bau",  # lowercase → normalised
            "observed_date": "2026-02-15",
            "quote": "Bauarbeiten haben begonnen",
        },
    )
    result = extract_media_report("text", url="https://faz.net/x")
    assert result["publication"] == "FAZ"
    assert result["phase"] == "BAU"  # validated + upper-cased
    assert result["project_name"] == "Ausbau Hanau–Würzburg"


def test_extract_drops_invalid_phase(monkeypatch):
    monkeypatch.setattr(media_extraction.settings, "llm_base_url", "http://llm.local")
    monkeypatch.setattr(
        media_extraction, "call_llm_json", lambda system_prompt, prompt: {"phase": "Halbfertig"}
    )
    assert extract_media_report("text")["phase"] is None


def test_extract_survives_llm_error(monkeypatch):
    monkeypatch.setattr(media_extraction.settings, "llm_base_url", "http://llm.local")

    def _boom(system_prompt, prompt):
        raise RuntimeError("llm down")

    monkeypatch.setattr(media_extraction, "call_llm_json", _boom)
    assert extract_media_report("text")["phase"] is None
