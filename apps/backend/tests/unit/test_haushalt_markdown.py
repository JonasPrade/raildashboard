"""Markdown tables from the OCR stage → the parser's row shape.

No API key is needed for these: the shape of a markdown table is a written
standard, so the translation can be pinned on synthetic input. Whether Mistral
returns *this* shape for the Haushalt report is the separate question the
comparison mode answers (see `scripts/compare_haushalt_extraction.py`).
"""

from __future__ import annotations

from dashboard_backend.tasks.haushalt_markdown import (
    parse_html_table,
    parse_markdown_table,
    parse_page_tables,
)


def test_parses_a_plain_table():
    markdown = """
| Lfd. Nr. | Nr. FinVe | Bezeichnung |
| --- | --- | --- |
| B0080 275 N19 |  | ABS Angermünde |
""".strip()
    assert parse_markdown_table(markdown) == [
        ["Lfd. Nr.", "Nr. FinVe", "Bezeichnung"],
        ["B0080 275 N19", None, "ABS Angermünde"],
    ]


def test_alignment_row_is_not_a_data_row():
    markdown = "| a | b |\n| :--- | ---: |\n| 1 | 2 |"
    assert parse_markdown_table(markdown) == [["a", "b"], ["1", "2"]]


def test_table_without_outer_pipes():
    markdown = "a | b\n--- | ---\n1 | 2"
    assert parse_markdown_table(markdown) == [["a", "b"], ["1", "2"]]


def test_line_breaks_inside_a_cell_become_stacked_lines():
    """The parser reads a measure's sub-entries as lines inside one cell — that
    is how the pdfplumber path delivers them, so the OCR path must match."""
    markdown = (
        "| Bezeichnung | aktuell |\n| --- | --- |\n"
        "| ABS Angermünde<br>davon:<br>Kap. 1202, Titel 891 01 | 477.871<br>241.852 |"
    )
    rows = parse_markdown_table(markdown)
    assert rows[1][0] == "ABS Angermünde\ndavon:\nKap. 1202, Titel 891 01"
    assert rows[1][1] == "477.871\n241.852"


def test_break_variants_are_all_recognised():
    markdown = "| a |\n| --- |\n| x<br>y<BR/>z<br />w |"
    assert parse_markdown_table(markdown)[1][0] == "x\ny\nz\nw"


def test_escaped_pipe_stays_inside_the_cell():
    markdown = "| a | b |\n| --- | --- |\n| Lp 1\\|2 | 5 |"
    assert parse_markdown_table(markdown)[1] == ["Lp 1|2", "5"]


def test_empty_cell_is_none_like_pdfplumber():
    markdown = "| a | b | c |\n| --- | --- | --- |\n| 1 |  | 3 |"
    assert parse_markdown_table(markdown)[1] == ["1", None, "3"]


def test_short_row_is_padded_so_columns_do_not_shift():
    """A row the model returned one column short must not pull the following
    values into the wrong field."""
    markdown = "| a | b | c |\n| --- | --- | --- |\n| 1 | 2 |"
    rows = parse_markdown_table(markdown)
    assert rows[1] == ["1", "2", None]


def test_width_pads_every_row_to_the_expected_column_count():
    markdown = "| a | b |\n| --- | --- |\n| 1 | 2 |"
    rows = parse_markdown_table(markdown, width=16)
    assert all(len(row) == 16 for row in rows)
    assert rows[1][:3] == ["1", "2", None]


def test_width_never_truncates_a_wider_row():
    markdown = "| a | b | c |\n| --- | --- | --- |\n| 1 | 2 | 3 |"
    rows = parse_markdown_table(markdown, width=2)
    assert rows[1] == ["1", "2", "3"]


def test_prose_around_the_grid_is_ignored():
    markdown = "Tabelle 1 - Bedarfsplanmaßnahmen\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n\nFußnote"
    assert parse_markdown_table(markdown) == [["a", "b"], ["1", "2"]]


def test_empty_input_yields_no_rows():
    assert parse_markdown_table("") == []
    assert parse_markdown_table("   \n  ") == []


def test_page_tables_are_concatenated_in_order():
    first = "| a | b |\n| --- | --- |\n| 1 | 2 |"
    second = "| a | b |\n| --- | --- |\n| 3 | 4 |"
    rows = parse_page_tables([first, second], width=2)
    assert rows == [["a", "b"], ["1", "2"], ["a", "b"], ["3", "4"]]


# ---------------------------------------------------------------------------
# HTML tables — the format the Haushalt asks the OCR stage for
# ---------------------------------------------------------------------------
#
# Markdown has no way to express a line break inside a cell, so the model joins
# the stacked lines of a Haushalt record with spaces and the row geometry is
# lost.  HTML keeps them as <br>, and a merged header cell as colspan/rowspan —
# the same shape pdfplumber returns.


def test_html_keeps_the_stacked_lines_of_a_cell():
    """The point of asking for HTML: <br> survives, a space-join would not."""
    markup = (
        "<table><tr><th>Lfd. Nr.</th><th>Bezeichnung</th><th>Veranschlagt</th></tr>"
        "<tr><td>B0080</td>"
        "<td>ABS Angermünde<br/>davon:<br/>Kap. 1202, Titel 891 01</td>"
        "<td>77.859<br/>22.200</td></tr></table>"
    )
    assert parse_html_table(markup) == [
        ["Lfd. Nr.", "Bezeichnung", "Veranschlagt"],
        ["B0080", "ABS Angermünde\ndavon:\nKap. 1202, Titel 891 01", "77.859\n22.200"],
    ]


def test_html_expands_colspan_the_way_pdfplumber_reports_a_merged_cell():
    """Text in the first column it covers, None in every further one."""
    markup = (
        "<table><tr><th colspan='3'>voraussichtliche Gesamtausgaben</th><th>Gründe</th></tr>"
        "<tr><td>1</td><td>2</td><td>3</td><td>4</td></tr></table>"
    )
    assert parse_html_table(markup) == [
        ["voraussichtliche Gesamtausgaben", None, None, "Gründe"],
        ["1", "2", "3", "4"],
    ]


def test_html_reserves_a_rowspan_column_in_the_rows_below():
    markup = (
        "<table><tr><th rowspan='2'>Lfd. Nr.</th><th colspan='2'>Gesamtausgaben</th></tr>"
        "<tr><th>ursprünglich</th><th>aktuell</th></tr>"
        "<tr><td>B0080</td><td>379.844</td><td>477.871</td></tr></table>"
    )
    assert parse_html_table(markup) == [
        ["Lfd. Nr.", "Gesamtausgaben", None],
        [None, "ursprünglich", "aktuell"],
        ["B0080", "379.844", "477.871"],
    ]


def test_html_drops_inline_markup_but_keeps_its_text():
    markup = "<table><tr><td><b>TABELLEN SUMMEN</b></td><td>&nbsp;</td><td>1&nbsp;000</td></tr></table>"
    assert parse_html_table(markup) == [["TABELLEN SUMMEN", None, "1 000"]]


def test_html_pads_a_short_row_to_the_canonical_width():
    """A row the model returned short must not shift the columns after it."""
    markup = "<table><tr><td>B0080</td><td>275</td></tr></table>"
    assert parse_html_table(markup, width=5) == [["B0080", "275", None, None, None]]


def test_html_never_truncates_a_row_that_is_wider_than_the_width():
    markup = "<table><tr><td>a</td><td>b</td><td>c</td></tr></table>"
    assert parse_html_table(markup, width=2) == [["a", "b", "c"]]


def test_html_reads_several_tables_of_one_page_as_one_row_stream():
    first = "<table><tr><td>a</td></tr></table>"
    second = "<table><tr><td>b</td></tr></table>"
    assert parse_page_tables([first, second], table_format="html") == [["a"], ["b"]]


def test_page_tables_still_default_to_markdown():
    """Sources whose rows are single-line keep the markdown reader."""
    markdown = "| a | b |\n| --- | --- |\n| 1 | 2 |"
    assert parse_page_tables([markdown]) == [["a", "b"], ["1", "2"]]


def test_html_of_an_empty_table_is_no_rows():
    assert parse_html_table("<table></table>") == []
    assert parse_html_table("") == []
