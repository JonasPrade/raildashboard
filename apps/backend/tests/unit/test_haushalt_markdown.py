"""Markdown tables from the OCR stage → the parser's row shape.

No API key is needed for these: the shape of a markdown table is a written
standard, so the translation can be pinned on synthetic input. Whether Mistral
returns *this* shape for the Haushalt report is the separate question the
comparison mode answers (see `scripts/compare_haushalt_extraction.py`).
"""

from __future__ import annotations

from dashboard_backend.tasks.haushalt_markdown import parse_markdown_table, parse_page_tables


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
