"""InfraGO-Zustandsbericht: reports, asset classes and values.

See docs/features/feature-zustandsbericht.md. The MCP tools and the REST
endpoints call the same functions; values written by an agent stay
UNGEPRUEFT until a person releases the year.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from dashboard_backend.models.condition import ConditionAssetClass, ConditionReport, ConditionValue
from dashboard_backend.services.condition_catalog import (
    DEFAULT_CLASSES,
    DOMAINS,
    FAHRWEG_ONLY_SCOPES,
    LAENDER,
    METRICS,
    SCOPES,
)
from dashboard_backend.services.condition_checks import check_values

# Metrics of the public time series (headline figures and grades per class).
SERIES_METRICS = ("NOTE", "ERNEUERUNGSBEDARF_MRD", "NACHHOLBEDARF_MRD", "WBW_BEWERTET")


class ConditionError(ValueError):
    """Invalid input; the message is user-facing (German)."""


class ConditionNotFoundError(ConditionError):
    """The report, class or value does not exist."""


class ConditionCheckError(ConditionError):
    """The values break the inner sums of the table."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(
            "Prüfung fehlgeschlagen — nichts geschrieben:\n- " + "\n- ".join(errors)
        )


def _float(value: Any) -> float | None:
    return None if value is None else float(value)


# ---------------------------------------------------------------------------
# Asset classes
# ---------------------------------------------------------------------------


def ensure_default_classes(db: Session) -> None:
    """Create the asset classes of the 2025 report on first use."""
    existing = {key for (key,) in db.query(ConditionAssetClass.key)}
    added = False
    for order, (key, domain, trade, name, unit) in enumerate(DEFAULT_CLASSES):
        if key not in existing:
            db.add(ConditionAssetClass(
                key=key, domain=domain, trade=trade, name=name, unit=unit, sort_order=order * 10
            ))
            added = True
    if added:
        db.flush()


def list_classes(db: Session, domain: str | None = None) -> list[ConditionAssetClass]:
    ensure_default_classes(db)
    query = db.query(ConditionAssetClass)
    if domain:
        query = query.filter(ConditionAssetClass.domain == domain)
    return query.order_by(ConditionAssetClass.domain, ConditionAssetClass.sort_order).all()


def class_out(c: ConditionAssetClass) -> dict[str, Any]:
    return {
        "key": c.key,
        "domain": c.domain,
        "trade": c.trade,
        "name": c.name,
        "unit": c.unit,
        "sort_order": c.sort_order,
        "description": c.description,
    }


def create_class(
    db: Session,
    *,
    key: str,
    domain: str,
    name: str,
    unit: str | None,
    trade: str | None = None,
    description: str | None = None,
) -> ConditionAssetClass:
    if domain not in DOMAINS:
        raise ConditionError(f"Unbekannter Bereich {domain} ({', '.join(DOMAINS)}).")
    ensure_default_classes(db)
    if db.query(ConditionAssetClass).filter(ConditionAssetClass.key == key).first():
        raise ConditionError(f"Die Anlagenklasse {key} gibt es schon.")
    last = (
        db.query(func.max(ConditionAssetClass.sort_order))
        .filter(ConditionAssetClass.domain == domain)
        .scalar()
    )
    record = ConditionAssetClass(
        key=key, domain=domain, trade=trade, name=name, unit=unit, description=description,
        sort_order=(last or 0) + 10,
    )
    db.add(record)
    db.commit()
    return record


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def get_report_by_year(db: Session, year: int) -> ConditionReport | None:
    return db.query(ConditionReport).filter(ConditionReport.year == year).first()


def report_or_error(db: Session, year: int) -> ConditionReport:
    report = get_report_by_year(db, year)
    if report is None:
        raise ConditionNotFoundError(f"Den Zustandsbericht {year} gibt es nicht.")
    return report


def report_out(db: Session, report: ConditionReport) -> dict[str, Any]:
    counts = dict(
        db.query(ConditionValue.status, func.count(ConditionValue.id))
        .filter(ConditionValue.report_id == report.id)
        .group_by(ConditionValue.status)
        .all()
    )
    return {
        "id": report.id,
        "year": report.year,
        "title": report.title,
        "source_url": report.source_url,
        "published_on": report.published_on,
        "price_basis": report.price_basis,
        "note": report.note,
        "status": report.status,
        "has_pdf": bool(report.pdf_path),
        "values_total": sum(counts.values()),
        "values_unchecked": counts.get("UNGEPRUEFT", 0),
        "accepted_mismatches": report.accepted_mismatches or [],
        "created_at": report.created_at,
        "released_at": report.released_at,
        "released_by": report.released_by_snapshot,
    }


def list_reports(db: Session, *, released_only: bool = False) -> list[dict[str, Any]]:
    query = db.query(ConditionReport)
    if released_only:
        query = query.filter(ConditionReport.status == "FREIGEGEBEN")
    return [report_out(db, r) for r in query.order_by(ConditionReport.year.desc())]


def create_report(
    db: Session,
    *,
    year: int,
    title: str | None = None,
    source_url: str | None = None,
    published_on: date | None = None,
    price_basis: str | None = None,
    note: str | None = None,
    username: str | None = None,
) -> ConditionReport:
    existing = get_report_by_year(db, year)
    if existing is not None:
        raise ConditionError(f"Den Zustandsbericht {year} gibt es schon (id {existing.id}).")
    report = ConditionReport(
        year=year,
        title=title or f"InfraGO-Zustandsbericht {year}",
        source_url=source_url,
        published_on=published_on,
        price_basis=price_basis,
        note=note,
        created_by_snapshot=username,
    )
    db.add(report)
    db.commit()
    return report


_REPORT_FIELDS = ("title", "source_url", "published_on", "price_basis", "note")


def update_report(db: Session, report: ConditionReport, changes: dict[str, Any]) -> ConditionReport:
    for field, value in changes.items():
        if field not in _REPORT_FIELDS:
            raise ConditionError(f"Feld {field} lässt sich nicht ändern.")
        setattr(report, field, value)
    db.commit()
    return report


def attach_pdf(db: Session, report: ConditionReport, pdf_bytes: bytes) -> ConditionReport:
    from dashboard_backend.utils.file_storage import delete_condition_pdf, save_condition_pdf

    old = report.pdf_path
    report.pdf_path = save_condition_pdf(report.year, pdf_bytes)
    try:
        db.commit()
    except Exception:
        delete_condition_pdf(report.pdf_path)
        raise
    delete_condition_pdf(old)
    return report


def delete_report(db: Session, report: ConditionReport) -> None:
    from dashboard_backend.utils.file_storage import delete_condition_pdf

    pdf = report.pdf_path
    db.query(ConditionValue).filter(ConditionValue.report_id == report.id).delete(
        synchronize_session=False
    )
    db.delete(report)
    db.commit()
    delete_condition_pdf(pdf)


def release_report(db: Session, report: ConditionReport, username: str | None) -> int:
    """Mark every value as checked and make the year public."""
    count = (
        db.query(ConditionValue)
        .filter(ConditionValue.report_id == report.id, ConditionValue.status != "GEPRUEFT")
        .update({ConditionValue.status: "GEPRUEFT"}, synchronize_session=False)
    )
    report.status = "FREIGEGEBEN"
    report.released_at = datetime.utcnow()
    report.released_by_snapshot = username
    db.commit()
    return count


# ---------------------------------------------------------------------------
# Values
# ---------------------------------------------------------------------------


def _key(domain, scope, region, class_id, metric, grade, ref_year) -> tuple:
    return (domain, scope, region, class_id, metric, grade, ref_year)


def _validate_table(report: ConditionReport, domain: str, scope: str, region: str | None) -> None:
    if domain not in DOMAINS:
        raise ConditionError(f"Unbekannter Bereich {domain} ({', '.join(DOMAINS)}).")
    if scope not in SCOPES:
        raise ConditionError(f"Unbekannter Netzausschnitt {scope} ({', '.join(SCOPES)}).")
    if scope in FAHRWEG_ONLY_SCOPES and domain != "FAHRWEG":
        raise ConditionError(f"{scope} gibt es nur beim Fahrweg.")
    if scope == "LAND" and region not in LAENDER:
        raise ConditionError(f"Für LAND ein Länderkürzel angeben ({', '.join(LAENDER)}).")
    if scope != "LAND" and region is not None:
        raise ConditionError("Ein Land (region) nur mit scope LAND angeben.")


def set_values(
    db: Session,
    report: ConditionReport,
    *,
    domain: str,
    scope: str,
    region: str | None,
    values: list[dict[str, Any]],
    status: str,
    username: str | None,
    override_reason: str | None = None,
) -> dict[str, Any]:
    """Upsert the values of one table (domain × scope × region); a value of
    None removes the slot. The table is checked as a whole (stored values
    plus these) before anything is written — a failed check writes nothing
    unless ``override_reason`` says why the report itself does not add up.

    Each value: ``class_key`` (None = total), ``metric``, ``grade``,
    ``reference_year`` (default: report year), ``value``, ``source_page``,
    ``source_ref``.
    """
    _validate_table(report, domain, scope, region)
    classes = {c.key: c for c in list_classes(db)}
    by_id = {c.id: c for c in classes.values()}

    incoming: dict[tuple, dict[str, Any]] = {}
    for data in values:
        key = data.get("class_key")
        if key is not None:
            asset_class = classes.get(key)
            if asset_class is None:
                raise ConditionError(
                    f"Unbekannte Anlagenklasse {key} (list_condition_classes; neue mit create_condition_class)."
                )
            if asset_class.domain != domain:
                raise ConditionError(f"{key} gehört nicht zum Bereich {domain}.")
        if data["metric"] not in METRICS:
            raise ConditionError(f"Unbekannte Kennzahl {data['metric']} ({', '.join(METRICS)}).")
        ref_year = data.get("reference_year") or report.year
        if not report.year - 10 <= ref_year <= report.year:
            raise ConditionError(f"Bezugsjahr {ref_year} passt nicht zum Bericht {report.year}.")
        class_id = classes[key].id if key is not None else None
        slot = _key(domain, scope, region, class_id, data["metric"], data.get("grade"), ref_year)
        if slot in incoming:
            raise ConditionError(f"Doppelter Wert: {key or 'Summe'} {data['metric']} {data.get('grade') or ''}".strip())
        incoming[slot] = {**data, "reference_year": ref_year}

    stored = {
        _key(v.domain, v.scope, v.region, v.asset_class_id, v.metric, v.grade, v.reference_year): v
        for v in db.query(ConditionValue).filter(
            ConditionValue.report_id == report.id,
            ConditionValue.domain == domain,
            ConditionValue.scope == scope,
            ConditionValue.region.is_(None) if region is None else ConditionValue.region == region,
        )
    }

    merged: dict[tuple, dict[str, Any]] = {
        slot: {"value": float(v.value)} for slot, v in stored.items()
    }
    for slot, data in incoming.items():
        if data.get("value") is None:
            merged.pop(slot, None)
        else:
            merged[slot] = {"value": float(data["value"])}

    names = {c.key: c.name for c in classes.values()}
    errors = check_values(
        [
            {
                "class_key": by_id[slot[3]].key if slot[3] is not None else None,
                "metric": slot[4],
                "grade": slot[5],
                "reference_year": slot[6],
                "value": item["value"],
            }
            for slot, item in merged.items()
        ],
        names,
    )
    if errors and not override_reason:
        raise ConditionCheckError(errors)
    if errors:
        report.accepted_mismatches = [
            *(report.accepted_mismatches or []),
            {
                "at": datetime.utcnow().isoformat(timespec="seconds"),
                "by": username,
                "table": f"{domain} {scope}{' ' + region if region else ''}",
                "reason": override_reason,
                "errors": errors,
            },
        ]

    stats = {"written": 0, "removed": 0}
    for slot, data in incoming.items():
        existing = stored.get(slot)
        if data.get("value") is None:
            if existing is not None:
                db.delete(existing)
                stats["removed"] += 1
            continue
        if existing is None:
            existing = ConditionValue(
                report_id=report.id,
                domain=domain,
                scope=scope,
                region=region,
                asset_class_id=slot[3],
                metric=slot[4],
                grade=slot[5],
                reference_year=slot[6],
            )
            db.add(existing)
        existing.value = data["value"]
        existing.source_page = data.get("source_page")
        existing.source_ref = data.get("source_ref")
        existing.status = status
        existing.entered_by_snapshot = username
        stats["written"] += 1
    db.commit()
    return {**stats, "accepted_mismatches": errors}


def value_out(v: ConditionValue, class_key: str | None) -> dict[str, Any]:
    return {
        "id": v.id,
        "domain": v.domain,
        "scope": v.scope,
        "region": v.region,
        "class_key": class_key,
        "metric": v.metric,
        "grade": v.grade,
        "reference_year": v.reference_year,
        "value": float(v.value),
        "source_page": v.source_page,
        "source_ref": v.source_ref,
        "status": v.status,
    }


def report_values(
    db: Session,
    report: ConditionReport,
    *,
    checked_only: bool = False,
    domain: str | None = None,
    scope: str | None = None,
    metric: str | None = None,
) -> list[dict[str, Any]]:
    keys = {c.id: c.key for c in list_classes(db)}
    query = db.query(ConditionValue).filter(ConditionValue.report_id == report.id)
    if checked_only:
        query = query.filter(ConditionValue.status == "GEPRUEFT")
    if domain:
        query = query.filter(ConditionValue.domain == domain)
    if scope:
        query = query.filter(ConditionValue.scope == scope)
    if metric:
        query = query.filter(ConditionValue.metric == metric)
    rows = query.order_by(
        ConditionValue.domain, ConditionValue.scope, ConditionValue.region,
        ConditionValue.asset_class_id, ConditionValue.metric, ConditionValue.grade,
        ConditionValue.reference_year,
    )
    return [value_out(v, keys.get(v.asset_class_id)) for v in rows]


def get_value(db: Session, value_id: int) -> ConditionValue:
    value = db.get(ConditionValue, value_id)
    if value is None:
        raise ConditionNotFoundError(f"Den Wert {value_id} gibt es nicht.")
    return value


def correct_value(db: Session, value_id: int, new_value: float, username: str | None) -> dict[str, Any]:
    """A person corrects one value in the release view; it counts as checked.
    The table is checked again but a mismatch only comes back as a warning —
    the person sees the page image next to it."""
    value = get_value(db, value_id)
    value.value = new_value
    value.status = "GEPRUEFT"
    value.entered_by_snapshot = username
    db.flush()
    report = db.get(ConditionReport, value.report_id)
    warnings = _table_errors(db, report, value.domain, value.scope, value.region)
    db.commit()
    keys = {c.id: c.key for c in list_classes(db)}
    return {"value": value_out(value, keys.get(value.asset_class_id)), "warnings": warnings}


def delete_value(db: Session, value_id: int) -> None:
    db.delete(get_value(db, value_id))
    db.commit()


def _table_errors(db: Session, report: ConditionReport, domain: str, scope: str, region: str | None) -> list[str]:
    names = {c.key: c.name for c in list_classes(db)}
    rows = [v for v in report_values(db, report, domain=domain, scope=scope) if v["region"] == region]
    return check_values(rows, names)


# Tables a complete report has: (domain, scope) → metrics expected for every class.
_EXPECTED = {
    ("FAHRWEG", "GESAMT"): ("NOTE", "WBW_BEWERTET", "VERTEILUNG_WBW"),
    ("FAHRWEG", "HLN"): ("NOTE", "WBW_BEWERTET", "VERTEILUNG_WBW"),
    ("PERSONENBAHNHOF", "GESAMT"): ("NOTE", "WBW_BEWERTET", "VERTEILUNG_WBW"),
}


def check_report(db: Session, report: ConditionReport) -> dict[str, Any]:
    """Every table of the year checked again, plus what is missing."""
    values = report_values(db, report)
    tables: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for v in values:
        tables[(v["domain"], v["scope"], v["region"])].append(v)
    names = {c.key: c.name for c in list_classes(db)}

    errors = []
    for (domain, scope, region), rows in sorted(tables.items(), key=lambda t: tuple(str(x) for x in t[0])):
        found = check_values(rows, names)
        if found:
            errors.append({"table": f"{domain} {scope}{' ' + region if region else ''}", "errors": found})

    gaps: list[str] = []
    for (domain, scope), metrics in _EXPECTED.items():
        rows = tables.get((domain, scope, None), [])
        if not rows:
            gaps.append(f"{domain} {scope}: keine Werte")
            continue
        for metric in metrics:
            if not any(r["metric"] == metric and r["reference_year"] == report.year for r in rows):
                gaps.append(f"{domain} {scope}: {metric} fehlt")
    for domain in DOMAINS:
        missing = [
            code for code in LAENDER
            if not any(
                v["metric"] == "NOTE" and v["reference_year"] == report.year
                for v in tables.get((domain, "LAND", code), [])
            )
        ]
        if missing and len(missing) < len(LAENDER):
            gaps.append(f"{domain} LAND: Note fehlt für {', '.join(missing)}")
        elif missing:
            gaps.append(f"{domain} LAND: keine Länderwerte")
    return {
        "year": report.year,
        "status": report.status,
        "values": len(values),
        "unchecked": sum(1 for v in values if v["status"] != "GEPRUEFT"),
        "errors": errors,
        "gaps": gaps,
        "accepted_mismatches": report.accepted_mismatches or [],
    }


# ---------------------------------------------------------------------------
# Public reads
# ---------------------------------------------------------------------------


def public_series(db: Session) -> list[dict[str, Any]]:
    """Headline values and grades of every released year as one series:
    per slot and reference year the newest released report wins (the more
    recent source wins, docs/architecture.md → Principles)."""
    keys = {c.id: c.key for c in list_classes(db)}
    rows = (
        db.query(ConditionValue, ConditionReport.year)
        .join(ConditionReport, ConditionReport.id == ConditionValue.report_id)
        .filter(
            ConditionReport.status == "FREIGEGEBEN",
            ConditionValue.status == "GEPRUEFT",
            ConditionValue.metric.in_(SERIES_METRICS),
        )
        .order_by(ConditionReport.year)
    )
    newest: dict[tuple, dict[str, Any]] = {}
    for v, report_year in rows:
        slot = _key(v.domain, v.scope, v.region, v.asset_class_id, v.metric, v.grade, v.reference_year)
        newest[slot] = {**value_out(v, keys.get(v.asset_class_id)), "report_year": report_year}
    return sorted(
        newest.values(),
        key=lambda r: (r["domain"], r["scope"], r["region"] or "", r["class_key"] or "", r["metric"], r["reference_year"]),
    )


# ---------------------------------------------------------------------------
# PDF pages (MCP import, release view)
# ---------------------------------------------------------------------------


def _pdf_bytes(report: ConditionReport) -> bytes:
    from dashboard_backend.utils.file_storage import read_condition_pdf

    try:
        return read_condition_pdf(report.pdf_path)
    except (FileNotFoundError, ValueError) as exc:
        raise ConditionNotFoundError(
            f"Zum Zustandsbericht {report.year} ist kein PDF gespeichert — erst im Admin hochladen."
        ) from exc


def render_page(report: ConditionReport, page: int, dpi: int = 110) -> bytes:
    """One page of the stored PDF as PNG (1-indexed)."""
    import fitz  # pymupdf

    with fitz.open(stream=_pdf_bytes(report), filetype="pdf") as doc:
        if not 1 <= page <= doc.page_count:
            raise ConditionNotFoundError(f"Seite {page} gibt es nicht (1–{doc.page_count}).")
        return doc[page - 1].get_pixmap(dpi=dpi).tobytes("png")


def page_count(report: ConditionReport) -> int:
    import fitz  # pymupdf

    with fitz.open(stream=_pdf_bytes(report), filetype="pdf") as doc:
        return doc.page_count


def page_words(report: ConditionReport, page: int) -> list[dict]:
    """Words of one page with their position (for ``layout_text``)."""
    from dashboard_backend.tasks.infraplan import extract_pages

    pdf_bytes = _pdf_bytes(report)
    count = page_count(report)
    if not 1 <= page <= count:
        raise ConditionNotFoundError(f"Seite {page} gibt es nicht (1–{count}).")
    return extract_pages(pdf_bytes, [page])[0].words
