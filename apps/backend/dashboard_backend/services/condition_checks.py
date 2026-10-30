"""Plausibility checks for the values of one table of the InfraGO-Zustandsbericht.

The report's tables carry inner sums: a grade distribution adds up to 100 %,
the quantities per grade add up to the rated quantity, the classes add up to
the total. A value misread by an agent breaks one of them, so the server
refuses the write (feature-zustandsbericht.md → "Import über MCP + Skill").

Pure functions on plain dicts — no database.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from dashboard_backend.services.condition_catalog import GRADES, METRICS

# Classes outside the portfolio sums (Tab. 7 excludes the Empfangsgebäude).
EXCLUDED_FROM_TOTALS = {"pb_empfangsgebaeude"}

# Metrics whose classes add up to the total of the scope.
_SUMMED = ("WBW", "WBW_BEWERTET", "WBW_ANTEIL", "MENGE_BEWERTET", "MENGE_GESAMT",
           "ERNEUERUNGSBEDARF_MRD", "NACHHOLBEDARF_MRD")


def _tolerance(metric: str, total: float) -> float:
    unit = METRICS[metric][0]
    if unit == "%":
        return 0.3
    if unit == "Menge":
        return max(2.0, abs(total) * 0.002)
    return max(0.3, abs(total) * 0.002)


def _fmt(value: float) -> str:
    text = f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return text.rstrip("0").rstrip(",") if "," in text else text


def check_values(values: Iterable[dict[str, Any]], names: dict[str | None, str] | None = None) -> list[str]:
    """Errors for the values of one table (one domain, scope and region).

    Each value: ``class_key`` (None = total of the scope), ``metric``,
    ``grade``, ``reference_year``, ``value``. Returns German messages; an
    empty list means the table is consistent.
    """
    names = names or {}
    errors: list[str] = []

    def label(key: str | None) -> str:
        return "Summe" if key is None else names.get(key, key)

    by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for v in values:
        by_year[v["reference_year"]].append(v)

    for year, rows in sorted(by_year.items()):
        prefix = f"{year}: " if len(by_year) > 1 else ""
        # (class, metric) → value; (class, metric) → {grade: value}
        single: dict[tuple[str | None, str], float] = {}
        graded: dict[tuple[str | None, str], dict[int, float]] = defaultdict(dict)

        for v in rows:
            metric, grade, value = v["metric"], v.get("grade"), float(v["value"])
            where = f"{prefix}{label(v['class_key'])} {metric}"
            if metric not in METRICS:
                errors.append(f"{where}: unbekannte Kennzahl.")
                continue
            needs_grade = METRICS[metric][1]
            if needs_grade and grade not in GRADES:
                errors.append(f"{where}: Note 1–6 fehlt.")
                continue
            if not needs_grade and grade is not None:
                errors.append(f"{where}: Note nur bei Verteilungen angeben.")
                continue
            if value < 0:
                errors.append(f"{where}: negativer Wert {_fmt(value)}.")
            if metric == "NOTE" and not 1 <= value <= 6:
                errors.append(f"{where}: Note {_fmt(value)} liegt nicht zwischen 1 und 6.")
            if METRICS[metric][0] == "%" and value > 100:
                errors.append(f"{where}: {_fmt(value)} % über 100.")
            if needs_grade:
                graded[(v["class_key"], metric)][grade] = value
            else:
                single[(v["class_key"], metric)] = value

        for (key, metric), dist in graded.items():
            total = sum(dist.values())
            if metric == "VERTEILUNG_WBW":
                if abs(total - 100) > _tolerance(metric, 100):
                    errors.append(
                        f"{prefix}{label(key)}: Notenverteilung ergibt {_fmt(total)} % statt 100 %."
                    )
            else:
                rated = single.get((key, "MENGE_BEWERTET"))
                if rated is not None and abs(total - rated) > _tolerance("MENGE_BEWERTET", rated):
                    errors.append(
                        f"{prefix}{label(key)}: Mengen je Note ergeben {_fmt(total)}, "
                        f"bewertete Menge ist {_fmt(rated)}."
                    )
                need = single.get((key, "ERNEUERUNGSBEDARF_MENGE"))
                if need is not None and all(g in dist for g in (4, 5)):
                    bad = sum(dist.get(g, 0) for g in (4, 5, 6))
                    if abs(bad - need) > _tolerance("ERNEUERUNGSBEDARF_MENGE", need):
                        errors.append(
                            f"{prefix}{label(key)}: Erneuerungsbedarf {_fmt(need)} passt nicht zu "
                            f"den Mengen der Noten 4–6 ({_fmt(bad)})."
                        )

        for key in {k for k, _ in single}:
            rated, stock = single.get((key, "MENGE_BEWERTET")), single.get((key, "MENGE_GESAMT"))
            if rated is not None and stock is not None and rated > stock:
                errors.append(
                    f"{prefix}{label(key)}: bewertete Menge {_fmt(rated)} größer als Bestand {_fmt(stock)}."
                )
            wbw, rated_wbw = single.get((key, "WBW")), single.get((key, "WBW_BEWERTET"))
            if wbw is not None and rated_wbw is not None and rated_wbw > wbw + 0.05:
                errors.append(
                    f"{prefix}{label(key)}: bewerteter WBW {_fmt(rated_wbw)} größer als WBW {_fmt(wbw)}."
                )

        for metric in _SUMMED:
            total = single.get((None, metric))
            parts = [
                value for (key, m), value in single.items()
                if m == metric and key is not None and key not in EXCLUDED_FROM_TOTALS
            ]
            if total is None or len(parts) < 2:
                continue
            if abs(sum(parts) - total) > _tolerance(metric, total):
                errors.append(
                    f"{prefix}{metric}: Anlagenklassen ergeben {_fmt(sum(parts))}, Summe ist {_fmt(total)}."
                )

    return errors
