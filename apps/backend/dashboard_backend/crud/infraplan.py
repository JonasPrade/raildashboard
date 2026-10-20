"""Reads of the confirmed Infraplan years and the KPIs.

See docs/features/feature-infraplan-import.md ("Kosten", "Anzeige",
"Kennzahlen"). Writing years lives in ``crud/infraplan_import.py``.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from dashboard_backend.models.infraplan import (
    InfraplanEntry,
    InfraplanEntryProject,
    InfraplanKpi,
    InfraplanKpiValue,
    InfraplanReport,
)
from dashboard_backend.models.projects.project import Project
from dashboard_backend.services.infraplan_kpis import DEFAULT_KPIS
from dashboard_backend.tasks.infraplan import SECTION_TITLES


class InfraplanKpiError(ValueError):
    """Invalid KPI input; the message is user-facing (German)."""


def _float(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _resolve_cost(entry: InfraplanEntry, by_id: dict[int, InfraplanEntry]) -> InfraplanEntry | None:
    """The entry that carries the cost of ``entry`` (references followed)."""
    seen: set[int] = set()
    current: InfraplanEntry | None = entry
    while current is not None and current.cost_mio is None and current.cost_ref_entry_id:
        if current.id in seen:
            return None
        seen.add(current.id)
        current = by_id.get(current.cost_ref_entry_id)
    if current is None or current.cost_mio is None:
        return None
    return current


def _load_refs(db: Session, entries: list[InfraplanEntry]) -> dict[int, InfraplanEntry]:
    """The entries plus every entry their cost references reach."""
    by_id = {e.id: e for e in entries}
    pending = {e.cost_ref_entry_id for e in entries if e.cost_ref_entry_id} - set(by_id)
    while pending:
        loaded = db.query(InfraplanEntry).filter(InfraplanEntry.id.in_(pending)).all()
        for entry in loaded:
            by_id[entry.id] = entry
        pending = {e.cost_ref_entry_id for e in loaded if e.cost_ref_entry_id} - set(by_id)
    return by_id


def entry_dict(entry: InfraplanEntry, year: int, by_id: dict[int, InfraplanEntry]) -> dict[str, Any]:
    carrier = _resolve_cost(entry, by_id)
    return {
        "id": entry.id,
        "report_year": year,
        "section": entry.section,
        "section_title": SECTION_TITLES.get(entry.section, entry.section),
        "lfd_nr": entry.lfd_nr,
        "page": entry.page,
        "project_numbers": entry.project_numbers or [],
        "primary_number": entry.primary_number,
        "bezeichnung": entry.bezeichnung,
        "massnahme": entry.massnahme,
        "laender": entry.laender,
        "state_raw": entry.state_raw,
        "lph_from": entry.lph_from,
        "lph_to": entry.lph_to,
        "under_construction": bool(entry.under_construction),
        "baurecht": bool(entry.baurecht),
        "ibn_raw": entry.ibn_raw,
        "ibn_year": entry.ibn_year,
        "ibn_qualifier": entry.ibn_qualifier,
        "cost_mio": _float(entry.cost_mio),
        "cost_kind": entry.cost_kind,
        "cost_ref_raw": entry.cost_ref_raw,
        "cost_ref_entry_id": entry.cost_ref_entry_id,
        "resolved_cost_mio": _float(carrier.cost_mio) if carrier is not None else None,
        "parl_raw": entry.parl_raw,
        "parl_state": entry.parl_state,
        "footnotes": entry.footnotes or {},
    }


# --- Per project -----------------------------------------------------------------


def _subtree_ids(db: Session, root_id: int) -> list[int]:
    ids, frontier = [root_id], [root_id]
    while frontier:
        frontier = [
            pid for (pid,) in db.query(Project.id).filter(Project.superior_project_id.in_(frontier))
        ]
        frontier = [pid for pid in frontier if pid not in ids]
        ids.extend(frontier)
    return ids


def _linked(db: Session, project_ids: list[int]):
    return (
        db.query(InfraplanEntry, InfraplanReport, InfraplanEntryProject)
        .join(InfraplanEntryProject, InfraplanEntryProject.entry_id == InfraplanEntry.id)
        .join(InfraplanReport, InfraplanReport.id == InfraplanEntry.report_id)
        .filter(InfraplanEntryProject.project_id.in_(project_ids))
        .order_by(InfraplanReport.year.desc(), InfraplanEntry.section, InfraplanEntry.lfd_nr)
        .all()
    )


def cost_forecast(
    rows: list[tuple[InfraplanEntry, int]], by_id: dict[int, InfraplanEntry], *, from_subprojects: bool
) -> dict[str, Any] | None:
    """Sum over the cost carriers of the newest year in ``rows`` — collective
    GWU and references count once (deduplicated by carrying entry)."""
    if not rows:
        return None
    year = max(y for _, y in rows)
    carriers: dict[int, InfraplanEntry] = {}
    for entry, entry_year in rows:
        if entry_year != year:
            continue
        carrier = _resolve_cost(entry, by_id)
        if carrier is not None:
            carriers[carrier.id] = carrier
    if not carriers:
        return None
    is_gvfg = all(c.cost_kind == "GESAMTKOSTEN" for c in carriers.values())
    label = (
        f"Gesamtkosten (Länderangabe, Infraplan {year})"
        if is_gvfg
        else f"Gesamtkostenprognose (Infraplan {year})"
    )
    footnotes: dict[str, str] = {}
    for entry, entry_year in rows:
        if entry_year == year:
            footnotes.update(entry.footnotes or {})
    return {
        "year": year,
        "total_mio": round(float(sum(c.cost_mio for c in carriers.values())), 2),
        "label": label,
        "from_subprojects": from_subprojects,
        "is_gvfg": is_gvfg,
        "entry_ids": sorted(carriers),
        "footnotes": footnotes,
    }


def project_infraplan(db: Session, project_id: int) -> dict[str, Any]:
    """Entries of all years linked to the project, the newest year overall,
    whether the project dropped out of it, and the cost forecast (own rows,
    else the sum over the subproject tree)."""
    latest = db.query(func.max(InfraplanReport.year)).scalar()
    own = _linked(db, [project_id])
    by_id = _load_refs(db, [entry for entry, _r, _l in own])
    names = dict(db.query(Project.id, Project.name).filter(Project.id == project_id))
    entries = [
        {
            **entry_dict(entry, report.year, by_id),
            "project_id": link.project_id,
            "project_name": names.get(link.project_id),
            "assignment_source": link.assignment_source,
            "assignment_note": link.note,
        }
        for entry, report, link in own
    ]
    years = {report.year for _e, report, _l in own}

    forecast = cost_forecast([(e, r.year) for e, r, _l in own], by_id, from_subprojects=False)
    if forecast is None:
        descendants = [pid for pid in _subtree_ids(db, project_id) if pid != project_id]
        if descendants:
            sub = _linked(db, descendants)
            sub_by_id = _load_refs(db, [entry for entry, _r, _l in sub])
            # An entry linked to several subprojects is one row.
            unique = {entry.id: (entry, report.year) for entry, report, _l in sub}
            forecast = cost_forecast(list(unique.values()), sub_by_id, from_subprojects=True)
    return {
        "entries": entries,
        "latest_year": latest,
        "missing_in_latest": bool(years) and latest is not None and latest not in years,
        "cost_forecast": forecast,
    }


# --- Public year lists ---------------------------------------------------------------


def public_reports(db: Session) -> list[dict[str, Any]]:
    counts = dict(
        db.query(InfraplanEntry.report_id, func.count(InfraplanEntry.id)).group_by(InfraplanEntry.report_id)
    )
    return [
        {
            "year": r.year,
            "title": r.title,
            "published_on": r.published_on,
            "entry_count": counts.get(r.id, 0),
        }
        for r in db.query(InfraplanReport).order_by(InfraplanReport.year.desc())
    ]


def report_entries(db: Session, report: InfraplanReport) -> list[dict[str, Any]]:
    entries = (
        db.query(InfraplanEntry)
        .filter(InfraplanEntry.report_id == report.id)
        .order_by(InfraplanEntry.section, InfraplanEntry.lfd_nr)
        .all()
    )
    by_id = _load_refs(db, entries)
    links: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for entry_id, project_id, name in (
        db.query(InfraplanEntryProject.entry_id, Project.id, Project.name)
        .join(Project, Project.id == InfraplanEntryProject.project_id)
        .filter(InfraplanEntryProject.entry_id.in_([e.id for e in entries]))
        .order_by(Project.name)
    ):
        links[entry_id].append({"id": project_id, "name": name})
    return [{**entry_dict(e, report.year, by_id), "projects": links.get(e.id, [])} for e in entries]


# --- KPIs ------------------------------------------------------------------------------


def ensure_default_kpis(db: Session) -> int:
    """Create the KPI definitions of the Infraplan 2026 that are missing
    (idempotent; existing definitions are never changed). Returns the count."""
    existing = {key for (key,) in db.query(InfraplanKpi.key)}
    created = 0
    for order, kpi in enumerate(DEFAULT_KPIS):
        if kpi["key"] in existing:
            continue
        db.add(InfraplanKpi(sort_order=order * 10, **kpi))
        created += 1
    if created:
        db.flush()
    return created


def list_kpis(db: Session) -> list[InfraplanKpi]:
    if ensure_default_kpis(db):
        db.commit()
    return db.query(InfraplanKpi).order_by(InfraplanKpi.sort_order, InfraplanKpi.id).all()


def kpi_values(db: Session, report: InfraplanReport) -> list[dict[str, Any]]:
    rows = (
        db.query(InfraplanKpiValue, InfraplanKpi.key)
        .join(InfraplanKpi, InfraplanKpi.id == InfraplanKpiValue.kpi_id)
        .filter(InfraplanKpiValue.report_id == report.id)
        .order_by(InfraplanKpi.sort_order, InfraplanKpiValue.year, InfraplanKpiValue.value_kind)
        .all()
    )
    return [
        {
            "id": v.id,
            "kpi_key": key,
            "report_year": report.year,
            "year": v.year,
            "value_kind": v.value_kind,
            "series": v.series,
            "value": float(v.value),
            "source_page": v.source_page,
            "status": v.status,
            "entered_by_snapshot": v.entered_by_snapshot,
        }
        for v, key in rows
    ]


def set_kpi_values(
    db: Session,
    report: InfraplanReport,
    values: list[dict[str, Any]],
    definitions: list[dict[str, Any]],
    *,
    status: str,
    username: str | None,
) -> dict[str, int]:
    """Create/correct definitions, then upsert values by (KPI, year, kind,
    series); a value of None removes the slot. All or nothing.

    ``status``: GEPRUEFT for the manual form, UNGEPRUEFT for the MCP path —
    an AI-read value is public only after the year is approved."""
    ensure_default_kpis(db)
    kpis = {k.key: k for k in db.query(InfraplanKpi)}
    unknown = sorted({v["kpi_key"] for v in values} - set(kpis) - {d["key"] for d in definitions})
    if unknown:
        raise InfraplanKpiError(
            f"Unbekannte Kennzahl(en): {', '.join(unknown)}. Neue Kennzahlen bitte mit "
            "stabilem key unter definitions anlegen."
        )
    stats = {"written": 0, "removed": 0, "definitions_created": 0}
    for data in definitions:
        kpi = kpis.get(data["key"])
        if kpi is None:
            kpi = InfraplanKpi(sort_order=1000 + len(kpis), **data)
            db.add(kpi)
            kpis[kpi.key] = kpi
            stats["definitions_created"] += 1
        else:
            for field in ("name", "unit", "kind", "category", "description"):
                if data.get(field) is not None:
                    setattr(kpi, field, data[field])
    db.flush()

    existing = {
        (v.kpi_id, v.year, v.value_kind, v.series): v
        for v in db.query(InfraplanKpiValue).filter(InfraplanKpiValue.report_id == report.id)
    }
    for data in values:
        series = (data.get("series") or "").strip() or None
        slot = (kpis[data["kpi_key"]].id, data["year"], data["value_kind"], series)
        current = existing.get(slot)
        if data.get("value") is None:
            if current is not None:
                db.delete(current)
                existing.pop(slot)
                stats["removed"] += 1
            continue
        if current is None:
            current = InfraplanKpiValue(
                report_id=report.id,
                kpi_id=slot[0],
                year=slot[1],
                value_kind=slot[2],
                series=series,
            )
            db.add(current)
            existing[slot] = current
        current.value = Decimal(str(data["value"]))
        current.source_page = data.get("source_page")
        current.status = status
        current.entered_by_snapshot = username
        stats["written"] += 1
    db.commit()
    return stats


def approve_kpi_values(db: Session, report: InfraplanReport) -> int:
    count = (
        db.query(InfraplanKpiValue)
        .filter(InfraplanKpiValue.report_id == report.id, InfraplanKpiValue.status != "GEPRUEFT")
        .update({InfraplanKpiValue.status: "GEPRUEFT"}, synchronize_session=False)
    )
    db.commit()
    return count


def public_kpis(db: Session) -> list[dict[str, Any]]:
    """Every KPI with its checked values of all years (a target of each year
    stays its own series, so target shifts stay visible)."""
    values: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for v, year in (
        db.query(InfraplanKpiValue, InfraplanReport.year)
        .join(InfraplanReport, InfraplanReport.id == InfraplanKpiValue.report_id)
        .filter(InfraplanKpiValue.status == "GEPRUEFT")
        .order_by(InfraplanReport.year, InfraplanKpiValue.year)
    ):
        values[v.kpi_id].append(
            {
                "report_year": year,
                "year": v.year,
                "value_kind": v.value_kind,
                "series": v.series,
                "value": float(v.value),
            }
        )
    return [
        {
            "id": k.id,
            "key": k.key,
            "name": k.name,
            "unit": k.unit,
            "kind": k.kind,
            "category": k.category,
            "description": k.description,
            "sort_order": k.sort_order,
            "values": values.get(k.id, []),
        }
        for k in list_kpis(db)
    ]
