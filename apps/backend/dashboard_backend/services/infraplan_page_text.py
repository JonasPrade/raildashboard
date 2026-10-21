"""Text of an Infraplan page with its layout, and value suggestions for the
KPI charts read from it (feature-infraplan-import.md → "Ausbau für den
Import 2027", MCP ``get_infraplan_page_text`` / ``suggest_infraplan_kpi_values``).

The KPI charts are vector graphics: their labels are text on the page. A
bar's value label sits above the bar, the year below it, both at the same
x position. Reading the words with their positions therefore gives most
values without an image. What text cannot tell: whether a bar is a target
(colour) and which segment of a stacked bar a label belongs to — stacked
labels are reported, not assigned.
"""

from __future__ import annotations

import re
from typing import Any

_LINE_TOLERANCE = 2.5
_YEAR_RE = re.compile(r"^(19|20)\d{2}$")
_NUMBER_RE = re.compile(r"^-?\d{1,3}(?:\.\d{3})*(?:,\d+)?%?$|^-?\d+(?:,\d+)?%?$")
# How far above its axis a chart's labels may sit (points).
_CHART_HEIGHT = 260.0


def _clean(words: list[dict]) -> list[dict]:
    # Glyphs without a Unicode mapping come out as "(cid:12)" — noise.
    return [w for w in words if w.get("text") and "(cid:" not in w["text"]]


def _center(word: dict) -> float:
    return (word["x0"] + word["x1"]) / 2


def page_lines(words: list[dict]) -> list[dict[str, Any]]:
    """Words grouped into lines by their top edge, left to right:
    ``[{top, words: [{x, text}]}]`` with ``x`` the horizontal centre."""
    lines: list[dict[str, Any]] = []
    for word in sorted(_clean(words), key=lambda w: (w["top"], w["x0"])):
        if lines and abs(word["top"] - lines[-1]["top"]) <= _LINE_TOLERANCE:
            lines[-1]["items"].append(word)
        else:
            lines.append({"top": word["top"], "items": [word]})
    return [
        {
            "top": round(line["top"]),
            "words": [
                {"x": round(_center(w)), "text": w["text"]}
                for w in sorted(line["items"], key=lambda w: w["x0"])
            ],
        }
        for line in lines
    ]


def layout_text(words: list[dict]) -> list[str]:
    """One string per line: ``"<top>: word@x word@x …"`` — compact enough for
    a whole page, precise enough to pair a chart label with its year."""
    return [
        f"{line['top']}: " + " ".join(f"{w['text']}@{w['x']}" for w in line["words"])
        for line in page_lines(words)
    ]


def parse_number(text: str) -> float | None:
    """German number label ("1.234", "12,5", "84%") → float."""
    text = text.strip()
    if not _NUMBER_RE.match(text):
        return None
    text = text.rstrip("%").replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _axes(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lines that are a year axis: three or more years, left to right, and
    little else (a footnote naming years is not an axis)."""
    axes = []
    for line in lines:
        years = [(w["x"], int(w["text"])) for w in line["words"] if _YEAR_RE.match(w["text"])]
        if (
            len(years) >= 3
            and len(years) >= 0.7 * len(line["words"])
            and [y for _, y in years] == sorted(y for _, y in years)
        ):
            axes.append({"top": line["top"], "years": years})
    return axes


def _title(lines: list[dict[str, Any]], above: float, below: float, left: float, right: float) -> str | None:
    """The text line nearest above a chart's labels within its width."""
    candidates = [
        line for line in lines
        if below < line["top"] < above
        and any(left - 20 <= w["x"] <= right + 20 for w in line["words"])
        and sum(1 for w in line["words"] if parse_number(w["text"]) is None) >= 2
    ]
    if not candidates:
        return None
    line = max(candidates, key=lambda l: l["top"])
    return " ".join(w["text"] for w in line["words"] if left - 20 <= w["x"] <= right + 20)


def suggest_chart_values(words: list[dict], plan_year: int | None = None) -> list[dict[str, Any]]:
    """Per year axis on the page: the number labels above it assigned to the
    nearest year by x position.

    - ``values``: ``{year, value, kind_guess}`` — ``kind_guess`` IST before the
      plan year, ZIEL from it on (the colour, which says it for sure, is not in
      the text).
    - ``stacked``: years with several labels (stacked bars or a line and bars)
      — read those from the image.
    - ``missing``: years without a label — a zero (zeros are not labelled) or
      no bar at all.
    - ``title``: the nearest text line above the chart.
    Unchecked suggestions: write them with ``set_infraplan_kpi_values`` only
    after a cross-check against the totals in the text."""
    lines = page_lines(words)
    charts = []
    axes = _axes(lines)
    for index, axis in enumerate(axes):
        xs = [x for x, _ in axis["years"]]
        step = min(b - a for a, b in zip(xs, xs[1:])) if len(xs) > 1 else 40
        upper = axes[index - 1]["top"] if index else axis["top"] - _CHART_HEIGHT
        upper = max(upper, axis["top"] - _CHART_HEIGHT)
        labels: dict[int, list[float]] = {}
        label_tops: list[float] = []
        for line in lines:
            if not upper < line["top"] < axis["top"]:
                continue
            # Value labels stand alone; numbers in running text do not count.
            if any(parse_number(w["text"]) is None for w in line["words"]):
                continue
            for word in line["words"]:
                value = parse_number(word["text"])
                x_year = min(axis["years"], key=lambda item: abs(item[0] - word["x"]))
                if abs(x_year[0] - word["x"]) > step * 0.45:
                    continue
                labels.setdefault(x_year[1], []).append(value)
                label_tops.append(line["top"])
        values = []
        stacked = []
        for _, year in axis["years"]:
            found = labels.get(year, [])
            if len(found) == 1:
                kind = None if plan_year is None else ("IST" if year < plan_year else "ZIEL")
                values.append({"year": year, "value": found[0], "kind_guess": kind})
            elif len(found) > 1:
                stacked.append({"year": year, "labels": found})
        top = min(label_tops) if label_tops else axis["top"]
        charts.append(
            {
                "axis_top": axis["top"],
                "title": _title(lines, top, upper - 40, xs[0] - step, xs[-1] + step),
                "years": [year for _, year in axis["years"]],
                "values": values,
                "stacked": stacked,
                "missing": [year for _, year in axis["years"] if year not in labels],
            }
        )
    return charts
