"""The OCR extraction path of the Haushalt import, without an API key.

Mistral OCR hands the report back as markdown tables. Rendering the recorded
pdfplumber rows *into* that markdown and pushing them through the OCR path is a
faithful round trip: it exercises the whole OCR side — markdown parsing, page
assembly, table segmentation, column mapping, value transfer — and proves that
**if** the model returns the grid faithfully, the import produces exactly the
same rows and numbers as the verified path.

What it deliberately cannot prove is whether the model *does* return the grid
faithfully for this report. That is what `HAUSHALT_EXTRACTION=compare` measures
against a real API, and what `scripts/compare_haushalt_extraction.py` reports.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dashboard_backend.services.document_ocr import OcrResult
from dashboard_backend.tasks.haushalt import (
    ExtractedPage,
    _compare_extractions,
    _extract_pages_from_ocr,
    _parse_extracted_pages,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "haushalt_ep12_2027_pages.json"


def _render_markdown_table(rows: list[list]) -> str:
    """Rows of cells → the markdown an OCR model returns for that table."""
    width = max((len(row) for row in rows), default=0)

    def _cell(value) -> str:
        if value is None:
            return ""
        return str(value).replace("|", "\\|").replace("\n", "<br>")

    lines = []
    for index, row in enumerate(rows):
        padded = list(row) + [None] * (width - len(row))
        lines.append("| " + " | ".join(_cell(c) for c in padded) + " |")
        if index == 0:
            lines.append("| " + " | ".join(["---"] * width) + " |")
    return "\n".join(lines)


@pytest.fixture(scope="module")
def recorded_pages() -> list[ExtractedPage]:
    return [
        ExtractedPage(number=entry["number"], text=entry["text"], rows=entry["rows"])
        for entry in json.loads(FIXTURE.read_text(encoding="utf-8"))
    ]


@pytest.fixture(scope="module")
def as_ocr_result(recorded_pages) -> OcrResult:
    """The same document as the OCR service would hand it over."""
    return OcrResult(
        text="\n".join(page.text for page in recorded_pages),
        pages=[page.text for page in recorded_pages],
        tables=[[_render_markdown_table(page.rows)] if page.rows else [] for page in recorded_pages],
        model="mistral-ocr-2512",
        status="done",
    )


# ---------------------------------------------------------------------------
# Page assembly
# ---------------------------------------------------------------------------

def test_ocr_pages_keep_the_document_order_and_page_numbers(recorded_pages, as_ocr_result):
    pages = _extract_pages_from_ocr(as_ocr_result)
    assert [p.number for p in pages] == [p.number for p in recorded_pages]
    assert [p.text for p in pages] == [p.text for p in recorded_pages]


def _empty_as_none(row: list) -> list:
    """pdfplumber returns "" for some empty cells, the markdown path None.

    Both are "no value" to the parser (`_parse_int`, the emptiness checks), so
    the round trip is compared on that footing.
    """
    return [None if (cell is None or str(cell) == "") else cell for cell in row]


def test_ocr_pages_reproduce_the_recorded_cells(recorded_pages, as_ocr_result):
    """The markdown round trip must not lose a cell or shift a column."""
    pages = _extract_pages_from_ocr(as_ocr_result)
    for recorded, from_ocr in zip(recorded_pages, pages):
        assert len(from_ocr.rows) == len(recorded.rows)
        for original, roundtripped in zip(recorded.rows, from_ocr.rows):
            # the OCR path pads every row to the canonical width
            assert _empty_as_none(roundtripped[: len(original)]) == _empty_as_none(list(original))


# ---------------------------------------------------------------------------
# End to end: same rows, same numbers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def both_results(recorded_pages, as_ocr_result):
    from_pdfplumber = _parse_extracted_pages(recorded_pages, 2027, known_finve_ids=set())
    from_ocr = _parse_extracted_pages(
        _extract_pages_from_ocr(as_ocr_result), 2027, known_finve_ids=set()
    )
    return from_pdfplumber, from_ocr


def test_ocr_path_finds_the_same_rows(both_results):
    from_pdfplumber, from_ocr = both_results
    assert [r.row_key for r in from_ocr.rows] == [r.row_key for r in from_pdfplumber.rows]


def test_ocr_path_finds_the_same_tables(both_results):
    from_pdfplumber, from_ocr = both_results
    assert [(s.number, s.row_count) for s in from_ocr.sections] == [
        (s.number, s.row_count) for s in from_pdfplumber.sections
    ]


def test_ocr_path_transfers_the_same_values(both_results):
    from_pdfplumber, from_ocr = both_results
    left = {r.row_key: r.proposed_budget.model_dump() for r in from_pdfplumber.rows}
    right = {r.row_key: r.proposed_budget.model_dump() for r in from_ocr.rows}
    assert left == right


# ---------------------------------------------------------------------------
# The comparison itself
# ---------------------------------------------------------------------------

def test_comparison_reports_two_identical_runs(both_results, as_ocr_result):
    from_pdfplumber, from_ocr = both_results
    comparison = _compare_extractions(from_pdfplumber, from_ocr, as_ocr_result)
    assert comparison.identical is True
    assert comparison.value_differences_total == 0
    assert comparison.rows_only_pdfplumber == []
    assert comparison.rows_only_ocr == []
    assert comparison.rows_matched == comparison.rows_pdfplumber == len(from_pdfplumber.rows)
    assert comparison.ocr_model == "mistral-ocr-2512"


def test_comparison_names_a_changed_value(both_results, as_ocr_result):
    """A single wrong number has to show up as one named difference — that is
    the whole point of the compare mode."""
    from_pdfplumber, from_ocr = both_results
    tampered = from_ocr.model_copy(deep=True)
    row = next(r for r in tampered.rows if r.row_key == "275")
    row.proposed_budget.year_planned = 77_000

    comparison = _compare_extractions(from_pdfplumber, tampered, as_ocr_result)
    assert comparison.identical is False
    assert comparison.value_differences_total == 1
    difference = comparison.value_differences[0]
    assert (difference.row_key, difference.field) == ("275", "year_planned")
    assert (difference.pdfplumber, difference.ocr) == ("77859", "77000")


def test_comparison_names_a_missing_row(both_results, as_ocr_result):
    from_pdfplumber, from_ocr = both_results
    tampered = from_ocr.model_copy(deep=True)
    tampered.rows = [r for r in tampered.rows if r.row_key != "t5:B0094"]

    comparison = _compare_extractions(from_pdfplumber, tampered, as_ocr_result)
    assert comparison.identical is False
    assert comparison.rows_only_pdfplumber == ["t5:B0094"]
    assert comparison.rows_ocr == comparison.rows_pdfplumber - 1


# ---------------------------------------------------------------------------
# HAUSHALT_EXTRACTION — which path supplies the values
# ---------------------------------------------------------------------------

@pytest.fixture()
def wired(monkeypatch, recorded_pages, as_ocr_result):
    """_parse_pdf with both stages stubbed: recorded rows, synthetic OCR."""
    calls: dict[str, int] = {"ocr": 0}

    monkeypatch.setattr(
        "dashboard_backend.tasks.haushalt._extract_pages",
        lambda pdf_bytes, task=None: recorded_pages,
    )

    def _fake_ocr(pdf_bytes, **kwargs):
        calls["ocr"] += 1
        return as_ocr_result

    monkeypatch.setattr("dashboard_backend.tasks.haushalt.extract_document_text", _fake_ocr)
    return calls


def _run(mode: str, monkeypatch):
    monkeypatch.setattr(
        "dashboard_backend.core.config.settings.haushalt_extraction", mode
    )
    from dashboard_backend.tasks.haushalt import _parse_pdf

    return _parse_pdf(b"pdf", 2027, known_finve_ids=set())


def test_default_mode_never_calls_the_ocr_service(wired, monkeypatch):
    result, document = _run("pdfplumber", monkeypatch)
    assert wired["ocr"] == 0
    assert result.extraction_source == "pdfplumber"
    assert result.extraction_comparison is None
    assert document.model == "pdfplumber"


def test_compare_mode_keeps_the_pdfplumber_values_and_records_the_diff(wired, monkeypatch):
    result, document = _run("compare", monkeypatch)
    assert wired["ocr"] == 1
    assert result.extraction_source == "pdfplumber"
    assert result.extraction_comparison is not None
    assert result.extraction_comparison.identical is True
    # the stored document text comes from the OCR stage in this mode
    assert document.model == "mistral-ocr-2512"


def test_ocr_mode_lets_the_ocr_path_supply_the_values(wired, monkeypatch):
    result, _ = _run("ocr", monkeypatch)
    assert result.extraction_source == "ocr"
    assert result.extraction_comparison is not None
    assert len(result.rows) > 0


def test_unknown_mode_falls_back_to_pdfplumber(wired, monkeypatch):
    result, _ = _run("nonsense", monkeypatch)
    assert wired["ocr"] == 0
    assert result.extraction_source == "pdfplumber"


def test_ocr_failure_never_fails_the_import(monkeypatch, recorded_pages):
    """An outage of the external service must not stop an import — the verified
    path carries it and the failure is recorded."""
    monkeypatch.setattr(
        "dashboard_backend.tasks.haushalt._extract_pages",
        lambda pdf_bytes, task=None: recorded_pages,
    )

    def _boom(pdf_bytes, **kwargs):
        raise RuntimeError("503 service unavailable")

    monkeypatch.setattr("dashboard_backend.tasks.haushalt.extract_document_text", _boom)
    result, document = _run("ocr", monkeypatch)

    assert result.extraction_source == "pdfplumber"
    assert len(result.rows) > 0
    assert result.extraction_comparison.ocr_status == "failed"
    assert "503" in result.extraction_comparison.error
    assert document.model == "pdfplumber"


def test_ocr_mode_falls_back_when_the_ocr_path_finds_no_rows(monkeypatch, recorded_pages):
    monkeypatch.setattr(
        "dashboard_backend.tasks.haushalt._extract_pages",
        lambda pdf_bytes, task=None: recorded_pages,
    )
    empty = OcrResult(
        text="kein Text", pages=["kein Text"], tables=[[]], model="mistral-ocr-2512", status="done"
    )
    monkeypatch.setattr(
        "dashboard_backend.tasks.haushalt.extract_document_text", lambda pdf_bytes, **kw: empty
    )
    result, _ = _run("ocr", monkeypatch)

    assert result.extraction_source == "pdfplumber"
    assert len(result.rows) > 0
    assert result.extraction_comparison.rows_ocr == 0

