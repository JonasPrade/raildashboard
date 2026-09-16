"""What the Haushalt import reports about itself while it runs.

The progress the task publishes is all the user sees during a multi-minute
import. It used to send ``rows_found: 0`` on every page, so the page read
"0 Zeilen gefunden" from the first second to the last — indistinguishable from
an import that really finds nothing. These tests hold the counter to the rows
actually read and every stage to a label of its own.
"""

from __future__ import annotations

import contextlib

import pdfplumber
import pytest

from dashboard_backend.tasks import haushalt


class _FakeTask:
    """Records what the task would publish to the result backend."""

    def __init__(self) -> None:
        self.updates: list[dict] = []

    def update_state(self, state: str, meta: dict) -> None:
        assert state == "PROGRESS"
        self.updates.append(meta)


class _FakePage:
    def __init__(self, number: int) -> None:
        self.page_number = number

    def extract_text(self) -> str:
        return "Tabelle 1 - Bedarfsplanmaßnahmen"


@pytest.fixture()
def three_page_pdf(monkeypatch):
    """A PDF of three pages, each carrying two table rows."""

    class _FakePdf:
        pages = [_FakePage(1), _FakePage(2), _FakePage(3)]

    @contextlib.contextmanager
    def _fake_open(_stream):
        yield _FakePdf()

    monkeypatch.setattr(pdfplumber, "open", _fake_open)
    monkeypatch.setattr(
        haushalt,
        "_page_table_rows",
        lambda page: ([["B0001", "275"], ["", "davon:"]], []),
    )


def test_progress_counts_the_rows_actually_read(three_page_pdf):
    task = _FakeTask()

    haushalt._extract_pages(b"%PDF-fake", task=task)

    counts = [update["rows_found"] for update in task.updates]
    assert counts == [2, 4, 6], "the counter has to grow with the pages read"
    assert [u["current_page"] for u in task.updates] == [1, 2, 3]
    assert all(u["total_pages"] == 3 for u in task.updates)


def test_progress_label_names_page_and_rows(three_page_pdf):
    task = _FakeTask()

    haushalt._extract_pages(b"%PDF-fake", task=task)

    assert task.updates[-1]["step"] == "extract"
    assert task.updates[-1]["step_label"] == "Seite 3 / 3 gelesen — 6 Tabellenzeilen"


def test_extraction_without_a_task_stays_silent(three_page_pdf):
    # The offline scripts call the same function with no Celery task attached.
    pages = haushalt._extract_pages(b"%PDF-fake")
    assert [page.number for page in pages] == [1, 2, 3]


def test_report_step_publishes_one_labelled_stage():
    task = _FakeTask()

    haushalt.report_step(task, "save", "141 Maßnahmen — Ergebnis wird gespeichert…")

    assert task.updates == [
        {"step": "save", "step_label": "141 Maßnahmen — Ergebnis wird gespeichert…"}
    ]


def test_report_step_is_a_no_op_without_a_task():
    haushalt.report_step(None, "save", "egal")  # must not raise
