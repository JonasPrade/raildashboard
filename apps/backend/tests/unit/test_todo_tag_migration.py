"""The todo-tags migration moves the "@LLM" marker out of task titles and descriptions."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20261022003_todo_tags_and_history.py"
)
_spec = importlib.util.spec_from_file_location("todo_tags_migration", _MIGRATION)
migration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migration)


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("@LLM Infraplan 2026 einlesen", "Infraplan 2026 einlesen"),
        ("@LLM: VIB prüfen", "VIB prüfen"),
        ("[@LLM] Geometrie zeichnen", "Geometrie zeichnen"),
        ("VIB prüfen @LLM", "VIB prüfen"),
        ("Teil für Jonas, dann @llm - Rest", "Teil für Jonas, dann Rest"),
        ("@LLM", "@LLM"),  # nothing else left: keep the title
        ("Mail an llm-team", "Mail an llm-team"),
    ],
)
def test_strip_llm_marker(title, expected):
    assert migration.strip_llm_marker(title) == expected


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("@LLM\n\nDie Unterprojekte …", "Die Unterprojekte …"),
        ("@LLM\r\nText", "Text"),
        ("@LLM", "@LLM"),  # no line break: not a marker line
        ("@LLM\n", None),
        ("Danach durch das LLM (@LLM): prüfen", "Danach durch das LLM (@LLM): prüfen"),
        (None, None),
    ],
)
def test_strip_llm_line(description, expected):
    assert migration.strip_llm_line(description) == expected


def test_seeded_tag_names_fit_the_column():
    assert len(migration.LLM_TAG) <= 50
    assert len(migration.JONAS_TAG) <= 50
