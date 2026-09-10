"""Markdown tables from the OCR stage → the row shape the parser reads.

The Haushalt parser works on rows of cells, the way ``pdfplumber.extract_table``
returns them: one list per row, one string per column, sub-entries stacked as
newline-separated lines inside a cell.  Mistral OCR returns the same table as
markdown (``table_format="markdown"``), so the OCR path only has to translate
that markdown into the same shape — every downstream stage (segmentation,
column mapping, value transfer) then works unchanged on either source.

What the translation has to survive:

* a leading and trailing pipe, or neither
* the alignment row (``|---|:---:|``) that carries no data
* ``<br>`` (and its variants) where a cell holds several stacked lines
* ``\\|`` for a pipe inside a cell
* rows shorter or longer than the header, which markdown does not forbid

This module is deliberately free of OCR specifics so it can be tested without an
API key — the shape of a markdown table is a written standard, the content of a
particular OCR response is not.
"""

from __future__ import annotations

import re

# "| --- | :---: | ---: |" — the alignment row under the header
_ALIGNMENT_ROW_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")

# Line breaks inside a cell: markdown has no newline, so OCR emits a <br>
_LINE_BREAK_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)

# An escaped pipe belongs to the cell, not to the grid
_ESCAPED_PIPE = "\x00ESCAPED_PIPE\x00"


def _split_cells(line: str) -> list[str]:
    """Split one markdown row into its cells, honouring escaped pipes."""
    protected = line.replace("\\|", _ESCAPED_PIPE)
    stripped = protected.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.replace(_ESCAPED_PIPE, "|") for cell in stripped.split("|")]


def _clean_cell(value: str) -> str | None:
    """Normalise one cell: ``<br>`` becomes a newline, empty becomes None.

    ``None`` rather than ``""`` because that is what pdfplumber returns for an
    empty cell, and the parser's emptiness checks rely on it.
    """
    text = _LINE_BREAK_RE.sub("\n", value)
    lines = [line.strip() for line in text.split("\n")]
    joined = "\n".join(line for line in lines if line)
    return joined or None


def parse_markdown_table(markdown: str, width: int | None = None) -> list[list]:
    """One markdown table → rows of cells, as ``extract_table`` would return them.

    ``width`` pads every row to that many columns (and never truncates below it),
    so a row the model returned short does not shift the values of the columns
    that follow it.  Without ``width`` the widest row decides.
    """
    rows: list[list[str]] = []
    for line in (markdown or "").splitlines():
        if not line.strip():
            continue
        if _ALIGNMENT_ROW_RE.match(line):
            continue
        if "|" not in line:
            # A caption or stray prose line above the grid — not a row
            continue
        rows.append(_split_cells(line))

    if not rows:
        return []

    target = max(width or 0, max(len(row) for row in rows))
    return [
        [_clean_cell(cell) for cell in row] + [None] * (target - len(row))
        for row in rows
    ]


def parse_page_tables(tables: list[str], width: int | None = None) -> list[list]:
    """Every table of one page, concatenated into one row stream.

    A page of Teil B holds one logical table; the model may still return it as
    several fragments (a page break inside the grid, a caption between two
    halves). Concatenating them in order is what the pdfplumber path does too.
    """
    rows: list[list] = []
    for markdown in tables:
        rows.extend(parse_markdown_table(markdown, width=width))
    return rows
