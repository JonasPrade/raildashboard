"""Build small GVFG-Bundesprogramm PDFs for tests.

The real programme PDFs are not part of the repository. This draws the same
structure — ruled table, header row, project rows with ∑/A/C lines, the
"Summe über" lines below — with pymupdf, so pdfplumber finds the table the way
it does in the real document.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import fitz

_FONT = fitz.Font("cjk")  # has "∑"; the base-14 fonts do not
_SIZE = 4.2
_LINE = 6.0

FINANCIAL_HEADERS = [
    "Nr.",
    "Schlüssel",
    "Stadt/Region",
    "Bezeichnung/ Beschreibung",
    "Lph",
    "Fördertatbestand",
    "Fördersatz",
    "Beginn- jahr Mittel- abfluss",
    "Bau- beginn",
    "Inbetrieb- nahme gepl.",
    "Inbetrieb- nahme tats.",
    "Kategorie (A, B, C)",
    "Gesamtkosten",
    "zwf. Kosten",
    "insgesamt",
    "1967-2023",
    "2024",
    "2025",
    "Rest ab 2030",
]
INFO_HEADERS = FINANCIAL_HEADERS[:11] + ["Gesamtkosten", "zwf. Kosten", "Bundes- finanzhilfen insgesamt"]
_WIDTHS = {
    "Nr.": 14,
    "Schlüssel": 44,
    "Stadt/Region": 40,
    "Bezeichnung/ Beschreibung": 110,
    "Lph": 20,
    "Fördertatbestand": 60,
    "Fördersatz": 30,
    "insgesamt": 44,  # room for "Bundesfinanzhilfen" in one line
}


@dataclass
class Row:
    """One project: meta values by header, and amount lines (marker, values)."""

    meta: dict[str, str]
    lines: list[tuple[str, list[str]]] = field(default_factory=list)


def _text(writer: fitz.TextWriter, x: float, y: float, text: str) -> None:
    writer.append((x, y), text, font=_FONT, fontsize=_SIZE)


def build_pdf(
    pages: list[dict],
    *,
    title: str = "Bundesprogramm 2025 - 2029 für die Vorhaben des öffentlichen",
    stand: str = "18.07.2025",
) -> bytes:
    """``pages``: [{"land", "kind" ("kommunale Vorhaben"/"DB-Vorhaben"),
    "informational": bool, "rows": [Row], "total": [(marker, [values])]}];
    an optional "headers" replaces the printed header texts of that page
    (same columns, e.g. a typo), Row.meta still uses the default names."""
    doc = fitz.open()
    for spec in pages:
        page = doc.new_page(width=842, height=595)
        writer = fitz.TextWriter(page.rect)
        _text(writer, 50, 24, "Bundesministerium für Verkehr")
        _text(writer, 405, 24, f"Land: {spec['land']}")
        _text(writer, 754, 24, f"Stand: {stand}")
        _text(writer, 398, 30, spec["kind"])
        if spec.get("informational"):
            _text(writer, 395, 36, "- nachrichtlicher Teil -")
        _text(writer, 350, 50, title)

        headers = INFO_HEADERS if spec.get("informational") else FINANCIAL_HEADERS
        printed = spec.get("headers", headers)
        xs = [30.0]
        for header in headers:
            xs.append(xs[-1] + _WIDTHS.get(header, 34))
        top = 70.0
        header_bottom = top + 4 * _LINE
        for col, header in enumerate(printed):
            for i, part in enumerate(header.split(" ")):
                _text(writer, xs[col] + 1, top + (i + 1) * _LINE - 1, part)

        y = header_bottom
        row_edges = [top, header_bottom]
        for row in spec["rows"]:
            n_lines = max(len(row.lines), 1)
            meta_y = y + _LINE - 1
            for col, header in enumerate(headers):
                value = row.meta.get(header)
                if value:
                    _text(writer, xs[col] + 1, meta_y, value)
            amount_cols = [i for i, h in enumerate(headers) if i >= headers.index("Gesamtkosten")]
            cat_col = headers.index("Kategorie (A, B, C)") if "Kategorie (A, B, C)" in headers else None
            for i, (marker, values) in enumerate(row.lines):
                line_y = y + (i + 1) * _LINE - 1
                if cat_col is not None and marker:
                    _text(writer, xs[cat_col] + 12, line_y, marker)
                for col, value in zip(amount_cols, values):
                    if value:
                        width = _FONT.text_length(value, fontsize=_SIZE)
                        _text(writer, xs[col + 1] - 2 - width, line_y, value)
            y += n_lines * _LINE + 2
            row_edges.append(y)

        for edge in row_edges:
            page.draw_line((xs[0], edge), (xs[-1], edge), width=0.3)
        for x in xs:
            page.draw_line((x, top), (x, row_edges[-1]), width=0.3)

        ty = row_edges[-1] + 12
        for marker, values in spec.get("total", []):
            label = f"Summe über {spec['land']}" if marker == "∑" else f"Kat. {marker}"
            _text(writer, 300, ty, label + "  " + "  ".join(values))
            ty += _LINE + 2
        writer.write_text(page)
    return doc.tobytes()
