"""Infraplan import: parse drafts, review, confirmation and years.

See docs/features/feature-infraplan-import.md. The REST endpoints and the MCP
tools call the same functions here ("Zwei Wege, ein Ergebnis"); they only
differ in the ``assignment_source`` they pass (``MANUAL`` vs. ``AGENT``).
Review state lives in the draft's ``result_json`` rows until the confirmation
writes ``infraplan_report`` / ``infraplan_entry`` / ``infraplan_entry_project``.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from dashboard_backend.crud._importer_common import recompute_for
from dashboard_backend.crud.changelog import create_changelog_for_create
from dashboard_backend.models.infraplan import (
    InfraplanEntry,
    InfraplanEntryProject,
    InfraplanKpiValue,
    InfraplanParseResult,
    InfraplanReport,
)
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.schemas.infraplan_import import (
    EDITABLE_ROW_FIELDS,
    InfraplanKpiPage,
    InfraplanMissingEntry,
    InfraplanMissingProject,
    InfraplanParseOutput,
    InfraplanProjectRef,
    InfraplanRowPatch,
    InfraplanWarning,
)
from dashboard_backend.tasks.infraplan_matching import (
    PRESELECT_CONFIDENCE,
    preselection,
    preselection_note,
    suggestions_for_draft,
)

if TYPE_CHECKING:
    from dashboard_backend.models.users import User


def create_parse_result(
    db: Session, year: int, file_name: str, user: "User | None"
) -> InfraplanParseResult:
    record = InfraplanParseResult(
        year=year,
        file_name=file_name,
        status="PENDING",
        created_by_user_id=user.id if user else None,
        username_snapshot=user.username if user else None,
    )
    db.add(record)
    db.flush()
    return record


def get_parse_result(db: Session, parse_result_id: int) -> InfraplanParseResult | None:
    return db.get(InfraplanParseResult, parse_result_id)


def list_parse_results(db: Session) -> list[InfraplanParseResult]:
    """All drafts, newest first."""
    return (
        db.query(InfraplanParseResult)
        .order_by(InfraplanParseResult.created_at.desc(), InfraplanParseResult.id.desc())
        .all()
    )


def mark_parse_pending(record: InfraplanParseResult, task_id: str | None) -> None:
    record.status = "PENDING"
    record.task_id = task_id
    record.error_message = None


def launch_parse(db: Session, record: InfraplanParseResult) -> str:
    """Start the parse task for a committed draft; returns the task id. A
    broker failure marks the draft failed and is re-raised."""
    from dashboard_backend.tasks.infraplan import parse_infraplan_pdf

    try:
        result = parse_infraplan_pdf.delay(record.id)
    except Exception as exc:
        mark_parse_failed(db, record, f"Auslesen konnte nicht gestartet werden: {exc}")
        db.commit()
        raise
    mark_parse_pending(record, result.id)
    db.commit()
    return result.id


def check_reparse(record: InfraplanParseResult) -> None:
    from dashboard_backend.utils.file_storage import infraplan_pdf_exists

    if record.confirmed_at is not None:
        raise InfraplanConflictError("Der Entwurf ist bereits übernommen und wird nicht neu ausgelesen.")
    if not infraplan_pdf_exists(record.pdf_path):
        raise InfraplanConflictError("Zu diesem Entwurf ist kein PDF mehr gespeichert. Bitte neu hochladen.")


def mark_parse_running(db: Session, record: InfraplanParseResult) -> None:
    record.status = "RUNNING"
    record.error_message = None
    db.flush()


def save_parse_output(
    db: Session,
    record: InfraplanParseResult,
    output: InfraplanParseOutput,
    warnings: list[InfraplanWarning],
    kpi_pages: list[InfraplanKpiPage],
) -> None:
    """Store a (re-)parse. Assignments made on an earlier parse of the same
    draft are kept per row key; new rows get suggestions and, from
    ``PRESELECT_CONFIDENCE`` on, a preselected assignment."""
    previous = {r["row_key"]: r for r in _rows(record)}
    result = output.model_dump(mode="json")
    suggestions = suggestions_for_draft(db, result["rows"], record.year)
    for row in result["rows"]:
        row["suggestions"] = suggestions.get(row["row_key"], [])
        old = previous.get(row["row_key"])
        if old and old.get("project_ids"):
            for key in ("project_ids", "assignment_source", "assignment_note", "assigned_by"):
                row[key] = old.get(key)
            continue
        ids, source = preselection(row["suggestions"], PRESELECT_CONFIDENCE)
        if ids:
            row["project_ids"] = ids
            row["assignment_source"] = source
            row["assignment_note"] = preselection_note(row["suggestions"], ids)
    record.status = "SUCCESS"
    record.error_message = None
    record.result_json = result
    record.warnings_json = [w.model_dump(mode="json") for w in warnings]
    record.kpi_pages_json = [p.model_dump(mode="json") for p in kpi_pages]
    db.flush()


def mark_parse_failed(db: Session, record: InfraplanParseResult, error: str) -> None:
    record.status = "FAILURE"
    record.error_message = error
    db.flush()


def delete_parse_result(db: Session, record: InfraplanParseResult) -> str | None:
    """Delete a draft; returns the stored PDF name for the caller to remove
    once the transaction has committed."""
    pdf_path = record.pdf_path
    db.delete(record)
    db.flush()
    return pdf_path


def row_count(record: InfraplanParseResult) -> int | None:
    if not record.result_json:
        return None
    return len(record.result_json.get("rows", []))


# ---------------------------------------------------------------------------
# Review (stage 2)
# ---------------------------------------------------------------------------


class InfraplanNotFoundError(LookupError):
    """Row, project or year does not exist (endpoints map this to 404)."""


class InfraplanConflictError(ValueError):
    """Not possible in the current state (endpoints map this to 409).
    The message is user-facing (German)."""


def _rows(record: InfraplanParseResult) -> list[dict[str, Any]]:
    return list((record.result_json or {}).get("rows", []))


def _store_rows(record: InfraplanParseResult, rows: list[dict[str, Any]]) -> None:
    data = dict(record.result_json or {})
    data["rows"] = rows
    record.result_json = data
    flag_modified(record, "result_json")


def _require_open(record: InfraplanParseResult) -> None:
    if record.status != "SUCCESS" or not record.result_json:
        raise InfraplanConflictError("Der Entwurf hat kein verwertbares Ergebnis.")
    if record.confirmed_at is not None:
        raise InfraplanConflictError(
            "Der Entwurf ist bereits übernommen. Zuordnungen bitte unter „Offene Zuordnungen“ "
            "oder nach dem Löschen des Jahrgangs ändern."
        )


def _find_row(rows: list[dict[str, Any]], row_key: str) -> dict[str, Any]:
    for row in rows:
        if row["row_key"] == row_key:
            return row
    raise InfraplanNotFoundError(f"Zeile {row_key} gibt es in diesem Entwurf nicht.")


def _check_projects(db: Session, ids: list[int]) -> None:
    if not ids:
        return
    found = {pid for (pid,) in db.query(Project.id).filter(Project.id.in_(ids))}
    missing = sorted(set(ids) - found)
    if missing:
        raise InfraplanNotFoundError(f"Projekte nicht gefunden: {', '.join(map(str, missing))}")


def assigned_count(record: InfraplanParseResult) -> int:
    return sum(1 for r in _rows(record) if r.get("project_ids"))


def _set_assignment(
    row: dict[str, Any], project_ids: list[int], source: str, note: str | None, username: str | None
) -> None:
    ids = list(dict.fromkeys(project_ids))
    row["project_ids"] = ids
    row["assignment_source"] = source if ids else None
    row["assignment_note"] = note if ids else None
    row["assigned_by"] = username if ids else None


def _apply_patch(
    db: Session,
    rows: list[dict[str, Any]],
    row_key: str,
    patch: InfraplanRowPatch,
    *,
    source: str,
    username: str | None,
) -> dict[str, Any]:
    row = _find_row(rows, row_key)
    if patch.project_ids is not None:
        _check_projects(db, patch.project_ids)
    if patch.values is not None:
        for key, value in patch.values.model_dump(exclude_unset=True).items():
            if key in EDITABLE_ROW_FIELDS:
                row[key] = value
    if patch.project_ids is not None:
        _set_assignment(row, patch.project_ids, source, (patch.note or "").strip() or None, username)
    elif patch.note is not None and row.get("project_ids"):
        row["assignment_note"] = patch.note.strip() or None
    return row


def patch_row(
    db: Session,
    record: InfraplanParseResult,
    row_key: str,
    patch: InfraplanRowPatch,
    *,
    source: str,
    username: str | None,
) -> dict[str, Any]:
    """Change the assignment and/or values of one row; returns the row."""
    _require_open(record)
    rows = _rows(record)
    row = _apply_patch(db, rows, row_key, patch, source=source, username=username)
    _store_rows(record, rows)
    db.commit()
    return row


def assign_rows(
    db: Session,
    record: InfraplanParseResult,
    items: list[tuple[str, list[int], str | None]],
    *,
    source: str,
    username: str | None,
) -> list[dict[str, Any]]:
    """Set the projects of many rows at once — ``(row_key, project_ids, note)``
    each, replacing what is there. Works on an open draft and, after the
    confirmation, on the confirmed entries of its year. A failing row does not
    stop the others; the result has ``ok`` and ``project_ids`` or ``error``
    per row. One commit, and the planning state is re-materialised once."""
    if record.confirmed_at is not None:
        return _assign_confirmed_rows(db, record, items, source=source, username=username)
    _require_open(record)
    rows = _rows(record)
    results: list[dict[str, Any]] = []
    for row_key, project_ids, note in items:
        try:
            row = _apply_patch(
                db, rows, row_key, InfraplanRowPatch(project_ids=project_ids, note=note),
                source=source, username=username,
            )
        except (InfraplanNotFoundError, InfraplanConflictError) as exc:
            results.append({"row_key": row_key, "ok": False, "error": str(exc)})
            continue
        results.append({"row_key": row_key, "ok": True, "project_ids": row["project_ids"]})
    _store_rows(record, rows)
    db.commit()
    return results


def confirmed_report(db: Session, record: InfraplanParseResult) -> InfraplanReport:
    """The year a confirmed draft was taken over as."""
    report = get_report_by_year(db, record.year)
    if report is None or report.parse_result_id != record.id:
        raise InfraplanConflictError("Zu diesem Entwurf gehört kein übernommener Jahrgang.")
    return report


def entry_for_row(db: Session, report: InfraplanReport, row_key: str) -> InfraplanEntry:
    """The confirmed entry of a draft row (``row_key`` = ``<section>-<lfd_nr>``)."""
    section, _, number = row_key.rpartition("-")
    entry = (
        db.query(InfraplanEntry)
        .filter_by(report_id=report.id, section=section, lfd_nr=int(number) if number.isdigit() else -1)
        .one_or_none()
    )
    if entry is None:
        raise InfraplanNotFoundError(f"Zeile {row_key} gibt es im Infraplan {report.year} nicht.")
    return entry


def _assign_confirmed_rows(
    db: Session,
    record: InfraplanParseResult,
    items: list[tuple[str, list[int], str | None]],
    *,
    source: str,
    username: str | None,
) -> list[dict[str, Any]]:
    report = confirmed_report(db, record)
    results: list[dict[str, Any]] = []
    affected: set[int] = set()
    for row_key, project_ids, note in items:
        try:
            entry = entry_for_row(db, report, row_key)
            _check_projects(db, project_ids)
        except (InfraplanNotFoundError, InfraplanConflictError) as exc:
            results.append({"row_key": row_key, "ok": False, "error": str(exc)})
            continue
        ids, touched = _link_entry(
            db, entry, project_ids, source=source, username=username, note=note, replace=True
        )
        affected |= touched
        results.append({"row_key": row_key, "ok": True, "project_ids": ids, "entry_id": entry.id})
    db.commit()
    recompute_for(db, affected)
    return results


def apply_suggestions(
    db: Session,
    record: InfraplanParseResult,
    min_confidence: float,
    *,
    only_unassigned: bool = True,
    username: str | None = None,
) -> tuple[int, int]:
    """Take over suggestions from ``min_confidence`` on. Returns
    (rows assigned now, rows still without projects)."""
    _require_open(record)
    rows = _rows(record)
    known = {pid for (pid,) in db.query(Project.id)}
    applied = 0
    for row in rows:
        if only_unassigned and row.get("project_ids"):
            continue
        suggestions = [s for s in row.get("suggestions") or [] if s["project_id"] in known]
        ids, source = preselection(suggestions, min_confidence)
        if ids and ids != row.get("project_ids"):
            _set_assignment(row, ids, source, preselection_note(suggestions, ids), username)
            applied += 1
    _store_rows(record, rows)
    db.commit()
    return applied, sum(1 for r in rows if not r.get("project_ids"))


def _new_row_project(
    db: Session, row: dict[str, Any], parent: Project | None, name: str | None, user: Any
) -> Project:
    """A draft project without geometry for a row: under ``parent``, or on its
    own (then it also takes the row's number, so next year finds it)."""
    title = (name or row.get("massnahme") or row.get("bezeichnung") or row["row_key"]).strip()
    project = Project(
        name=title[:255],
        superior_project_id=parent.id if parent else None,
        project_number=None if parent else row.get("primary_number"),
        is_draft=True,
    )
    db.add(project)
    db.flush()
    create_changelog_for_create(
        db,
        project,
        {
            "name": project.name,
            "superior_project_id": project.superior_project_id,
            "project_number": project.project_number,
            "is_draft": True,
        },
        getattr(user, "id", None),
        getattr(user, "username", None),
    )
    return project


def _default_note(parent: Project | None) -> str:
    if parent is None:
        return "Eigenständiges Projekt aus der Infraplan-Zeile angelegt"
    return f"Teilprojekt unter „{parent.name}“ angelegt"


def create_subproject(
    db: Session,
    record: InfraplanParseResult,
    row_key: str,
    parent_id: int | None,
    name: str | None,
    *,
    source: str,
    user: Any,
    note: str | None = None,
) -> tuple[Project, dict[str, Any]]:
    """Create a draft project (no geometry) named after the row — under
    ``parent_id``, or on its own without — and add it to the row's assignment
    (a link to the parent is replaced). After the confirmation the confirmed
    entry is changed instead. Returns the project and the row/entry state."""
    results = create_subprojects(
        db, record, [(row_key, parent_id, name, note)], source=source, user=user
    )
    result = results[0]
    if not result["ok"]:
        raise result["exception"]
    return db.get(Project, result["project_id"]), result["row"]


def create_subprojects(
    db: Session,
    record: InfraplanParseResult,
    items: list[tuple[str, int | None, str | None, str | None]],
    *,
    source: str,
    user: Any,
) -> list[dict[str, Any]]:
    """Many of :func:`create_subproject` at once — ``(row_key, parent_id,
    name, note)`` each; a failing row does not stop the others. One commit."""
    username = getattr(user, "username", None)
    confirmed = record.confirmed_at is not None
    report = confirmed_report(db, record) if confirmed else None
    if not confirmed:
        _require_open(record)
    rows = _rows(record)
    results: list[dict[str, Any]] = []
    affected: set[int] = set()
    for row_key, parent_id, name, note in items:
        try:
            row = _find_row(rows, row_key)
            entry = entry_for_row(db, report, row_key) if report else None
            parent = db.get(Project, parent_id) if parent_id is not None else None
            if parent_id is not None and parent is None:
                raise InfraplanNotFoundError(f"Projekt {parent_id} gibt es nicht.")
        except (InfraplanNotFoundError, InfraplanConflictError) as exc:
            results.append({"row_key": row_key, "ok": False, "error": str(exc), "exception": exc})
            continue
        project = _new_row_project(db, row, parent, name, user)
        note = note or _default_note(parent)
        if entry is not None:
            current = [
                link.project_id
                for link in db.query(InfraplanEntryProject).filter(InfraplanEntryProject.entry_id == entry.id)
            ]
            ids = [pid for pid in current if pid != getattr(parent, "id", None)] + [project.id]
            ids, touched = _link_entry(
                db, entry, ids, source=source, username=username, note=note, replace=True
            )
            affected |= touched
            state: dict[str, Any] = {"row_key": row_key, "entry_id": entry.id, "project_ids": ids}
        else:
            ids = [pid for pid in row.get("project_ids") or [] if pid != getattr(parent, "id", None)]
            _set_assignment(row, ids + [project.id], source, note, username)
            state = row
        results.append(
            {"row_key": row_key, "ok": True, "project_id": project.id, "name": project.name, "row": state}
        )
    if not confirmed:
        _store_rows(record, rows)
    db.commit()
    recompute_for(db, affected)
    return results


def draft_projects(db: Session, record: InfraplanParseResult) -> dict[str, InfraplanProjectRef]:
    """Every project a row suggests or is assigned to, for the review display."""
    ids: set[int] = set()
    for row in _rows(record):
        ids.update(row.get("project_ids") or [])
        ids.update(s["project_id"] for s in row.get("suggestions") or [])
    if not ids:
        return {}
    rows = db.query(Project.id, Project.name, Project.superior_project_id, Project.is_draft).filter(
        Project.id.in_(ids)
    )
    return {
        str(pid): InfraplanProjectRef(
            id=pid, name=name, superior_project_id=superior, is_draft=bool(draft)
        )
        for pid, name, superior, draft in rows
    }


def previous_report(db: Session, year: int) -> InfraplanReport | None:
    return (
        db.query(InfraplanReport)
        .filter(InfraplanReport.year < year)
        .order_by(InfraplanReport.year.desc())
        .first()
    )


def missing_from_previous(
    db: Session, record: InfraplanParseResult
) -> tuple[int | None, list[InfraplanMissingProject]]:
    """Projects with an entry in the previous year that have none in this
    draft — neither assigned nor reachable through their project number."""
    previous = previous_report(db, record.year)
    if previous is None:
        return None, []
    rows = _rows(record)
    assigned = {pid for r in rows for pid in r.get("project_ids") or []}
    numbers = {r.get("primary_number") for r in rows if r.get("primary_number")}
    links = (
        db.query(InfraplanEntry, InfraplanEntryProject.project_id, Project.name)
        .join(InfraplanEntryProject, InfraplanEntryProject.entry_id == InfraplanEntry.id)
        .join(Project, Project.id == InfraplanEntryProject.project_id)
        .filter(InfraplanEntry.report_id == previous.id)
        .order_by(Project.name, InfraplanEntry.section, InfraplanEntry.lfd_nr)
        .all()
    )
    by_project: dict[int, InfraplanMissingProject] = {}
    for entry, project_id, project_name in links:
        if project_id in assigned or (entry.primary_number and entry.primary_number in numbers):
            continue
        item = by_project.setdefault(
            project_id,
            InfraplanMissingProject(
                project_id=project_id,
                project_name=project_name,
                previous_year=previous.year,
                entries=[],
            ),
        )
        item.entries.append(
            InfraplanMissingEntry(
                section=entry.section,
                lfd_nr=entry.lfd_nr,
                primary_number=entry.primary_number,
                massnahme=entry.massnahme,
            )
        )
    return previous.year, list(by_project.values())


# ---------------------------------------------------------------------------
# Confirmation and years
# ---------------------------------------------------------------------------


def get_report_by_year(db: Session, year: int) -> InfraplanReport | None:
    return db.query(InfraplanReport).filter(InfraplanReport.year == year).one_or_none()


def _decimal(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _entry_fields(row: dict[str, Any]) -> dict[str, Any]:
    """The parsed fields of a draft row as ``InfraplanEntry`` columns."""
    return {
        "page": row.get("page"),
        "project_numbers": row.get("project_numbers") or [],
        "primary_number": row.get("primary_number"),
        "bezeichnung": row.get("bezeichnung"),
        "massnahme": row.get("massnahme"),
        "laender": row.get("laender"),
        "state_raw": row.get("state_raw"),
        "lph_from": row.get("lph_from"),
        "lph_to": row.get("lph_to"),
        "under_construction": bool(row.get("under_construction")),
        "baurecht": bool(row.get("baurecht")),
        "ibn_raw": row.get("ibn_raw"),
        "ibn_year": row.get("ibn_year"),
        "ibn_qualifier": row.get("ibn_qualifier"),
        "cost_mio": _decimal(row.get("cost_mio")),
        "cost_kind": row.get("cost_kind"),
        "cost_ref_raw": row.get("cost_ref_raw"),
        "parl_raw": row.get("parl_raw"),
        "parl_state": row.get("parl_state"),
        "footnote_refs": row.get("footnote_refs") or [],
        "footnotes": row.get("footnotes") or {},
    }


def _linked_project_ids(db: Session) -> set[int]:
    return {pid for (pid,) in db.query(InfraplanEntryProject.project_id).distinct()}


def confirm_parse_result(
    db: Session,
    record: InfraplanParseResult,
    *,
    published_on: date | None,
    title: str | None,
    force: bool,
    user: Any,
) -> dict[str, int]:
    """Write a reviewed draft as year ``record.year``.

    Refused when the year exists or — without ``force`` (frontend only) —
    when the parser left warnings. Afterwards the planning state of every
    project linked to any year is re-materialised (only the newest year of a
    project counts, so older links can change their effect too).
    """
    _require_open(record)
    if get_report_by_year(db, record.year) is not None:
        raise InfraplanConflictError(
            f"Der Infraplan {record.year} ist bereits übernommen. Bitte zuerst den Jahrgang löschen."
        )
    if record.warnings_json and not force:
        raise InfraplanConflictError(
            f"Der Entwurf hat {len(record.warnings_json)} Warnung(en) des Parsers. "
            "Bitte prüfen; übernehmen lässt er sich dann nur im Frontend mit „Trotzdem übernehmen“."
        )
    rows = _rows(record)
    wanted = sorted({pid for r in rows for pid in r.get("project_ids") or []})
    _check_projects(db, wanted)
    before = _linked_project_ids(db)

    report = InfraplanReport(
        year=record.year,
        title=title or f"Infraplan {record.year}",
        published_on=published_on,
        parse_result_id=record.id,
    )
    db.add(report)
    db.flush()

    by_key: dict[tuple[str, int], InfraplanEntry] = {}
    stats = {"entries": 0, "links": 0, "unassigned": 0}
    for row in rows:
        entry = InfraplanEntry(
            report_id=report.id,
            section=row["section"],
            lfd_nr=row["lfd_nr"],
            **_entry_fields(row),
        )
        db.add(entry)
        by_key[(entry.section, entry.lfd_nr)] = entry
        stats["entries"] += 1
    db.flush()

    for row in rows:
        entry = by_key[(row["section"], row["lfd_nr"])]
        ref = row.get("cost_ref")
        if ref and ref.get("resolved"):
            target = by_key.get((ref["section"], ref["lfd_nr"]))
            if target is not None:
                entry.cost_ref_entry_id = target.id
        ids = list(dict.fromkeys(row.get("project_ids") or []))
        if not ids:
            stats["unassigned"] += 1
        for project_id in ids:
            db.add(
                InfraplanEntryProject(
                    entry_id=entry.id,
                    project_id=project_id,
                    assigned_by_snapshot=row.get("assigned_by") or getattr(user, "username", None),
                    assignment_source=row.get("assignment_source") or "MANUAL",
                    note=row.get("assignment_note"),
                )
            )
            stats["links"] += 1

    record.confirmed_at = datetime.utcnow()
    record.confirmed_by_snapshot = getattr(user, "username", None)
    db.commit()

    affected = before | _linked_project_ids(db)
    recompute_for(db, affected)
    return {
        "report_id": report.id,
        "year": report.year,
        **stats,
        "projects_updated": len(affected),
    }


def _entry_ids(db: Session, report_id: int) -> list[int]:
    return [eid for (eid,) in db.query(InfraplanEntry.id).filter(InfraplanEntry.report_id == report_id)]


def delete_report(db: Session, report: InfraplanReport) -> int:
    """Delete one year with its entries, links and KPI values. The draft it
    came from becomes open again, so the year can be confirmed anew. Returns
    the number of projects whose planning state was re-materialised."""
    entry_ids = _entry_ids(db, report.id)
    affected = _linked_project_ids(db)
    if entry_ids:
        # Explicit deletes instead of relying on ON DELETE: derived rows go with
        # their source, and the cascade also holds where FKs are not enforced.
        db.query(ProgressObservation).filter(
            ProgressObservation.infraplan_entry_id.in_(entry_ids)
        ).delete(synchronize_session=False)
        db.query(InfraplanEntryProject).filter(
            InfraplanEntryProject.entry_id.in_(entry_ids)
        ).delete(synchronize_session=False)
        db.query(InfraplanEntry).filter(InfraplanEntry.id.in_(entry_ids)).update(
            {InfraplanEntry.cost_ref_entry_id: None}, synchronize_session=False
        )
        db.query(InfraplanEntry).filter(InfraplanEntry.id.in_(entry_ids)).delete(
            synchronize_session=False
        )
    db.query(InfraplanKpiValue).filter(InfraplanKpiValue.report_id == report.id).delete(
        synchronize_session=False
    )
    if report.parse_result_id is not None:
        draft = db.get(InfraplanParseResult, report.parse_result_id)
        if draft is not None:
            draft.confirmed_at = None
            draft.confirmed_by_snapshot = None
    db.delete(report)
    db.commit()
    recompute_for(db, affected)
    return len(affected)


def list_reports(db: Session) -> list[dict[str, Any]]:
    """Confirmed years, newest first, with entry/assignment/KPI counters."""
    reports = db.query(InfraplanReport).order_by(InfraplanReport.year.desc()).all()
    entry_counts = dict(
        db.query(InfraplanEntry.report_id, func.count(InfraplanEntry.id)).group_by(InfraplanEntry.report_id)
    )
    assigned = dict(
        db.query(InfraplanEntry.report_id, func.count(func.distinct(InfraplanEntry.id)))
        .join(InfraplanEntryProject, InfraplanEntryProject.entry_id == InfraplanEntry.id)
        .group_by(InfraplanEntry.report_id)
    )
    kpi_counts: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for report_id, status, count in db.query(
        InfraplanKpiValue.report_id, InfraplanKpiValue.status, func.count(InfraplanKpiValue.id)
    ).group_by(InfraplanKpiValue.report_id, InfraplanKpiValue.status):
        kpi_counts[report_id][0] += count
        if status != "GEPRUEFT":
            kpi_counts[report_id][1] += count
    return [
        {
            "id": r.id,
            "year": r.year,
            "title": r.title,
            "published_on": r.published_on,
            "parse_result_id": r.parse_result_id,
            "created_at": r.created_at,
            "entry_count": entry_counts.get(r.id, 0),
            "assigned_count": assigned.get(r.id, 0),
            "kpi_value_count": kpi_counts[r.id][0],
            "kpi_unchecked_count": kpi_counts[r.id][1],
        }
        for r in reports
    ]


# ---------------------------------------------------------------------------
# Open assignments after the confirmation (/admin/unassigned)
# ---------------------------------------------------------------------------


def newest_report(db: Session) -> InfraplanReport | None:
    return db.query(InfraplanReport).order_by(InfraplanReport.year.desc()).first()


def unassigned_entries(db: Session) -> list[tuple[InfraplanEntry, int]]:
    """Entries of the newest year without any project, with that year."""
    report = newest_report(db)
    if report is None:
        return []
    linked = db.query(InfraplanEntryProject.entry_id)
    rows = (
        db.query(InfraplanEntry)
        .filter(InfraplanEntry.report_id == report.id, InfraplanEntry.id.not_in(linked))
        .order_by(InfraplanEntry.section, InfraplanEntry.lfd_nr)
        .all()
    )
    return [(entry, report.year) for entry in rows]


def _link_entry(
    db: Session,
    entry: InfraplanEntry,
    project_ids: list[int],
    *,
    source: str,
    username: str | None,
    note: str | None,
    replace: bool,
) -> tuple[list[int], set[int]]:
    """Link a confirmed entry without committing. Returns (linked ids,
    projects whose planning state changes)."""
    existing = {
        link.project_id: link
        for link in db.query(InfraplanEntryProject).filter(InfraplanEntryProject.entry_id == entry.id)
    }
    affected = set(project_ids)
    if replace:
        for project_id, link in existing.items():
            if project_id not in project_ids:
                db.delete(link)
                affected.add(project_id)
    for project_id in dict.fromkeys(project_ids):
        if project_id in existing:
            if replace and note is not None:
                existing[project_id].note = note
            continue
        db.add(
            InfraplanEntryProject(
                entry_id=entry.id,
                project_id=project_id,
                assigned_by_snapshot=username,
                assignment_source=source,
                note=note,
            )
        )
    db.flush()
    return sorted(set(project_ids) | (set() if replace else set(existing))), affected


def assign_entry(
    db: Session,
    entry: InfraplanEntry,
    project_ids: list[int],
    *,
    source: str,
    username: str | None,
    note: str | None = None,
    replace: bool = False,
) -> list[int]:
    """Link a confirmed entry to projects (existing links are kept unless
    ``replace``); re-materialises the affected projects. Returns the ids."""
    _check_projects(db, project_ids)
    ids, affected = _link_entry(
        db, entry, project_ids, source=source, username=username, note=note, replace=replace
    )
    db.commit()
    recompute_for(db, affected)
    return ids


# ---------------------------------------------------------------------------
# Page images (KPI approval, MCP)
# ---------------------------------------------------------------------------


def render_page(record: InfraplanParseResult, page: int, dpi: int = 110) -> bytes:
    """One page of the draft's stored PDF as PNG (1-indexed)."""
    import fitz  # pymupdf

    from dashboard_backend.utils.file_storage import read_infraplan_pdf

    try:
        pdf_bytes = read_infraplan_pdf(record.pdf_path)
    except FileNotFoundError as exc:
        raise InfraplanNotFoundError("Zu diesem Entwurf ist kein PDF gespeichert.") from exc
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        if not 1 <= page <= doc.page_count:
            raise InfraplanNotFoundError(f"Seite {page} gibt es nicht (1–{doc.page_count}).")
        return doc[page - 1].get_pixmap(dpi=dpi).tobytes("png")


def page_words(record: InfraplanParseResult, page: int) -> list[dict]:
    """Words of one page of the draft's stored PDF with their position."""
    import fitz  # pymupdf

    from dashboard_backend.tasks.infraplan import extract_pages
    from dashboard_backend.utils.file_storage import read_infraplan_pdf

    try:
        pdf_bytes = read_infraplan_pdf(record.pdf_path)
    except FileNotFoundError as exc:
        raise InfraplanNotFoundError("Zu diesem Entwurf ist kein PDF gespeichert.") from exc
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        count = doc.page_count
    if not 1 <= page <= count:
        raise InfraplanNotFoundError(f"Seite {page} gibt es nicht (1–{count}).")
    return extract_pages(pdf_bytes, [page])[0].words


# ---------------------------------------------------------------------------
# Repair of drafts parsed before ``restore_full_stops``
# ---------------------------------------------------------------------------

# Warnings that depend on the cell texts; the rest (running numbers, layout)
# do not change when the full stops come back.
_TEXT_WARNING_KINDS = {"UNRESOLVED_REF", "UNREADABLE_TEXT", "UNPARSED_COST"}


def repair_full_stops(db: Session, *, apply: bool) -> list[dict[str, Any]]:
    """Restore the full stops read as U+FFFD in every stored draft and in the
    year confirmed from it — in place, so assignments and KPI values stay.

    Entries are updated by (section, lfd_nr) and cost references re-pointed.
    With ``apply`` the changes are committed and the planning state of the
    linked projects is re-materialised; otherwise nothing is written (dry
    run). Returns one summary per draft that needs the repair.
    """
    from dashboard_backend.tasks.infraplan import repair_rows, restore_full_stops

    summaries: list[dict[str, Any]] = []
    affected: set[int] = set()
    for record in db.query(InfraplanParseResult).order_by(InfraplanParseResult.id):
        if "\ufffd" not in json.dumps(record.result_json or {}, ensure_ascii=False):
            continue
        rows, changed, warnings = repair_rows(_rows(record))
        report = db.query(InfraplanReport).filter(InfraplanReport.parse_result_id == record.id).one_or_none()
        entries = {
            (e.section, e.lfd_nr): e
            for e in db.query(InfraplanEntry).filter(InfraplanEntry.report_id == report.id)
        } if report is not None else {}
        touched = [
            (row, entries[(row["section"], row["lfd_nr"])])
            for row in rows
            if row["row_key"] in changed and (row["section"], row["lfd_nr"]) in entries
        ]
        linked = {
            pid
            for (pid,) in db.query(InfraplanEntryProject.project_id).filter(
                InfraplanEntryProject.entry_id.in_([entry.id for _, entry in touched])
            )
        } if touched else set()
        affected |= linked
        summaries.append({
            "parse_result_id": record.id,
            "year": record.year,
            "rows_changed": len(changed),
            "entries_changed": len(touched),
            "projects_updated": len(linked),
            "warnings": [w.message for w in warnings],
        })
        if not apply:
            continue

        footnotes = (record.result_json or {}).get("footnotes") or {}
        _store_rows(record, rows)
        record.result_json["footnotes"] = {k: restore_full_stops(v) for k, v in footnotes.items()}
        kept = [w for w in record.warnings_json or [] if w.get("kind") not in _TEXT_WARNING_KINDS]
        record.warnings_json = kept + [w.model_dump(mode="json") for w in warnings]
        for row, entry in touched:
            for key, value in _entry_fields(row).items():
                setattr(entry, key, value)
            ref = row.get("cost_ref")
            target = entries.get((ref["section"], ref["lfd_nr"])) if ref and ref.get("resolved") else None
            entry.cost_ref_entry_id = target.id if target is not None else None

    if apply and summaries:
        db.commit()
        # recompute_progress commits per project, so it runs after the repair.
        recompute_for(db, affected)
    return summaries
