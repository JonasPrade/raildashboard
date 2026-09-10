"""Tables from the OCR stage → the row shape the parser reads.

The Haushalt parser works on rows of cells, the way ``pdfplumber.extract_table``
returns them: one list per row, one string per column, sub-entries stacked as
newline-separated lines inside a cell.  The OCR stage returns the same table as
markup, so the OCR path only has to translate that markup into the same shape —
every downstream stage (segmentation, column mapping, value transfer) then works
unchanged on either source.

Two markups, and the difference matters for this report.  **Markdown** has no
way to express a line break inside a cell: the model joins the stacked lines of
a Haushalt record with spaces, and which value belongs to which sub-entry is
lost for good.  **HTML** keeps them as ``<br>`` and expresses a merged header
cell as ``colspan``/``rowspan`` — the same shape pdfplumber returns, where the
spanned columns come back as ``None``.  The Haushalt therefore asks the OCR
stage for ``table_format="html"``; the markdown reader stays for sources whose
rows are single-line.

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
from html.parser import HTMLParser

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
    # A non-breaking space is a space to the parser — HTML entities decode to
    # U+00A0 and the number "1 000" must not become unparseable because of it.
    text = _LINE_BREAK_RE.sub("\n", value).replace("\u00a0", " ")
    lines = [" ".join(line.split()) for line in text.split("\n")]
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


def parse_page_tables(
    tables: list[str],
    width: int | None = None,
    table_format: str = "markdown",
) -> list[list]:
    """Every table of one page, concatenated into one row stream.

    A page of Teil B holds one logical table; the model may still return it as
    several fragments (a page break inside the grid, a caption between two
    halves). Concatenating them in order is what the pdfplumber path does too.

    ``table_format`` selects the reader — ``"html"`` for markup that carries the
    stacked lines of a cell, ``"markdown"`` otherwise.
    """
    read = parse_html_table if table_format == "html" else parse_markdown_table
    rows: list[list] = []
    for markup in tables:
        rows.extend(read(markup, width=width))
    return rows


# ---------------------------------------------------------------------------
# HTML tables
# ---------------------------------------------------------------------------

def _to_int(value: str | None, default: int = 1) -> int:
    """A colspan/rowspan attribute → a usable count (garbage counts as 1)."""
    try:
        count = int((value or "").strip())
    except (TypeError, ValueError):
        return default
    return count if count > 0 else default


class _TableRowCollector(HTMLParser):
    """Every ``<tr>`` of every ``<table>`` in one page, as rows of cells.

    Spans are expanded the way pdfplumber reports a merged cell: the text sits
    in the first column it covers, every further column it covers is ``None``.
    A ``rowspan`` therefore reserves its columns in the rows below, and the
    cells of those rows move right past the reservation.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str | None]] = []
        self._row: dict[int, str | None] | None = None
        self._cell: list[str] | None = None
        self._cell_column = 0
        self._colspan = 1
        # column -> number of following rows the column is still reserved for
        self._reserved: dict[int, int] = {}

    # -- rows ---------------------------------------------------------------
    def _start_row(self) -> None:
        self._row = {}
        for column, rows_left in list(self._reserved.items()):
            self._row[column] = None
            if rows_left <= 1:
                del self._reserved[column]
            else:
                self._reserved[column] = rows_left - 1

    def _close_row(self) -> None:
        if self._row is None:
            return
        self._close_cell()
        row = self._row
        self._row = None
        if row:
            self.rows.append([row.get(column) for column in range(max(row) + 1)])

    # -- cells --------------------------------------------------------------
    def _next_free_column(self) -> int:
        assert self._row is not None
        column = 0
        while column in self._row:
            column += 1
        return column

    def _start_cell(self, attrs: list[tuple[str, str | None]]) -> None:
        if self._row is None:
            self._start_row()
        self._close_cell()
        attributes = dict(attrs)
        self._colspan = _to_int(attributes.get("colspan"))
        rowspan = _to_int(attributes.get("rowspan"))
        self._cell_column = self._next_free_column()
        for offset in range(self._colspan):
            column = self._cell_column + offset
            # Claim the column now so the next cell of this row lands beside it.
            self._row[column] = None  # type: ignore[index]
            if rowspan > 1:
                self._reserved[column] = rowspan - 1
        self._cell = []

    def _close_cell(self) -> None:
        if self._cell is None or self._row is None:
            self._cell = None
            return
        self._row[self._cell_column] = _clean_cell("".join(self._cell))
        self._cell = None
        self._colspan = 1

    # -- HTMLParser hooks ---------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._close_row()
            self._start_row()
        elif tag in ("td", "th"):
            self._start_cell(attrs)
        elif tag == "br" and self._cell is not None:
            self._cell.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th"):
            self._close_cell()
        elif tag == "tr":
            self._close_row()
        elif tag == "table":
            self._close_row()
            self._reserved.clear()

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def close(self) -> None:  # noqa: D102 - inherited
        super().close()
        self._close_row()


def parse_html_table(markup: str, width: int | None = None) -> list[list]:
    """One HTML table → rows of cells, as ``extract_table`` would return them.

    ``width`` pads every row to that many columns exactly as the markdown
    reader does, so a row the model returned short does not shift the columns
    that follow it.
    """
    collector = _TableRowCollector()
    collector.feed(markup or "")
    collector.close()

    rows = [row for row in collector.rows if row]
    if not rows:
        return []

    target = max(width or 0, max(len(row) for row in rows))
    return [row + [None] * (target - len(row)) for row in rows]
