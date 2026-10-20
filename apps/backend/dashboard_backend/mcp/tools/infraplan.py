"""Infraplan import tools (feature-infraplan-import.md → "MCP & Skill").

The PDF is uploaded in the frontend; from there an agent carries the import
as far as it can: re-parse, take over safe suggestions, assign the rest with a
reason, create missing subprojects, confirm (never with parser warnings) and
read the KPI charts from page images (values stay unchecked until a person
approves the year). The skill ``.claude/skills/infraplan-import`` holds the
procedure. Every tool requires ``infraplan.import``; the REST endpoints call
the same CRUD functions with source MANUAL, these with AGENT.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.mcpserver.utilities.types import Image

from dashboard_backend.crud import infraplan as infraplan_crud
from dashboard_backend.crud import infraplan_import as crud
from dashboard_backend.mcp.context import get_principal, load_user, require, tool_session
from dashboard_backend.mcp.tools.projects import READ_ONLY, WRITE
from dashboard_backend.models.infraplan import InfraplanEntry, InfraplanParseResult
from dashboard_backend.models.projects.project import Project
from dashboard_backend.schemas.infraplan import (
    InfraplanKpiDefinitionInput,
    InfraplanKpiValueInput,
)
from dashboard_backend.schemas.infraplan_import import InfraplanRowPatch
from dashboard_backend.tasks.infraplan import SECTION_TITLES

PERMISSION = "infraplan.import"
AGENT = "AGENT"
_MAX_ROWS = 300

SectionLiteral = Literal["BP_A", "BP_B", "BP_C", "BP_D", "GVFG_A", "GVFG_C", "INVKG"]


def _draft_or_error(db, draft_id: int) -> InfraplanParseResult:
    record = crud.get_parse_result(db, draft_id)
    if record is None:
        raise ToolError(f"Entwurf {draft_id} gibt es nicht (list_infraplan_drafts).")
    return record


def _draft_summary(db, record: InfraplanParseResult) -> dict[str, Any]:
    return {
        "id": record.id,
        "year": record.year,
        "status": record.status,
        "file_name": record.file_name,
        "error": record.error_message,
        "created_at": record.created_at.isoformat(),
        "uploaded_by": record.username_snapshot,
        "confirmed_at": record.confirmed_at.isoformat() if record.confirmed_at else None,
        "rows": crud.row_count(record),
        "assigned_rows": crud.assigned_count(record),
        "warnings": record.warnings_json or [],
        "kpi_pages": record.kpi_pages_json or [],
    }


def _row_out(row: dict[str, Any]) -> dict[str, Any]:
    """A row without the empty noise of the parser fields."""
    keys = (
        "row_key", "section", "lfd_nr", "page", "primary_number", "project_numbers",
        "bezeichnung", "massnahme", "laender", "state_raw", "ibn_raw", "cost_mio",
        "cost_kind", "cost_ref_raw", "parl_raw", "footnotes", "suggestions",
        "project_ids", "assignment_source", "assignment_note",
    )
    return {k: row.get(k) for k in keys if row.get(k) not in (None, [], {}, "")}


def _errors(exc: Exception) -> ToolError:
    return ToolError(str(exc))


# --- Drafts --------------------------------------------------------------------


def list_infraplan_drafts(*, ctx: Context) -> dict[str, Any]:
    """Uploaded Infraplan drafts (newest first) with status, parser warnings,
    rows/assigned rows and the KPI chart pages, plus the confirmed years
    (requires ``infraplan.import``). Any warning means: stop and report."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        return {
            "drafts": [_draft_summary(db, r) for r in crud.list_parse_results(db)],
            "years": [
                {**y, "published_on": y["published_on"].isoformat() if y["published_on"] else None,
                 "created_at": y["created_at"].isoformat()}
                for y in crud.list_reports(db)
            ],
        }


def get_infraplan_draft(
    draft_id: int,
    section: SectionLiteral | None = None,
    only_open: bool = False,
    offset: int = 0,
    limit: int = 100,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Rows of a draft with suggestions ({project_id, confidence, reason
    NUMBER|GVFG_KEY|FUZZY}) and assignment (requires ``infraplan.import``).

    - section: BP_A–BP_D (Bedarfsplan Teil A–D), GVFG_A, GVFG_C, INVKG
    - only_open: rows without projects only
    Also returns the referenced projects, the warnings, the projects of the
    previous year without a row in this draft (renamings to check) and the
    section titles."""
    require(get_principal(ctx), PERMISSION)
    limit = max(1, min(limit, _MAX_ROWS))
    with tool_session(ctx) as db:
        record = _draft_or_error(db, draft_id)
        rows = [r for r in (record.result_json or {}).get("rows", [])]
        if section:
            rows = [r for r in rows if r["section"] == section]
        if only_open:
            rows = [r for r in rows if not r.get("project_ids")]
        page = rows[offset : offset + limit]
        previous_year, missing = crud.missing_from_previous(db, record)
        projects = crud.draft_projects(db, record)
        used = {pid for r in page for pid in (r.get("project_ids") or [])} | {
            s["project_id"] for r in page for s in (r.get("suggestions") or [])
        }
        return {
            "draft": _draft_summary(db, record),
            "sections": SECTION_TITLES,
            "total_matching": len(rows),
            "offset": offset,
            "rows": [_row_out(r) for r in page],
            "projects": {k: v.model_dump() for k, v in projects.items() if int(k) in used},
            "previous_year": previous_year,
            "missing_from_previous": [m.model_dump() for m in missing],
        }


def start_infraplan_parse(draft_id: int, *, ctx: Context) -> dict[str, Any]:
    """Parse the stored PDF of a draft again (requires ``infraplan.import``).
    Assignments are kept per row; check the status with list_infraplan_drafts."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        record = _draft_or_error(db, draft_id)
        try:
            crud.check_reparse(record)
        except crud.InfraplanConflictError as exc:
            raise _errors(exc) from exc
        try:
            task_id = crud.launch_parse(db, record)
        except Exception as exc:
            raise ToolError(f"Auslesen konnte nicht gestartet werden: {exc}") from exc
        return {"draft_id": record.id, "task_id": task_id, "status": "PENDING"}


def apply_infraplan_suggestions(
    draft_id: int, min_confidence: float = 0.85, *, ctx: Context
) -> dict[str, Any]:
    """Assign the suggested projects of open rows from ``min_confidence`` on
    (requires ``infraplan.import``): every project-number/GVFG-key hit, else
    the best name hit. Keep 0.85 unless the user says otherwise."""
    principal = get_principal(ctx)
    require(principal, PERMISSION)
    if not 0 <= min_confidence <= 1:
        raise ToolError("min_confidence liegt zwischen 0 und 1.")
    with tool_session(ctx) as db:
        record = _draft_or_error(db, draft_id)
        try:
            applied, unassigned = crud.apply_suggestions(
                db, record, min_confidence, username=principal.username
            )
        except crud.InfraplanConflictError as exc:
            raise _errors(exc) from exc
        return {"applied": applied, "still_open": unassigned}


def assign_infraplan_row(
    draft_id: int, row_key: str, project_ids: list[int], note: str, *, ctx: Context
) -> dict[str, Any]:
    """Set the projects of a row, replacing what is there (requires
    ``infraplan.import``). Prefer the subproject the row describes; ``note``
    says why (e.g. 'Teilprojekt Abschnitt 9.2, Name und Strecke stimmen').
    An empty list removes the assignment. After the confirmation the same call
    changes the confirmed entry of that year (planning state follows)."""
    principal = get_principal(ctx)
    require(principal, PERMISSION)
    if not note.strip():
        raise ToolError("Eine Begründung (note) ist Pflicht.")
    with tool_session(ctx) as db:
        record = _draft_or_error(db, draft_id)
        try:
            if record.confirmed_at is not None:
                return _assign_confirmed(db, record, row_key, project_ids, note.strip(), principal.username)
            row = crud.patch_row(
                db,
                record,
                row_key,
                InfraplanRowPatch(project_ids=project_ids, note=note),
                source=AGENT,
                username=principal.username,
            )
        except (crud.InfraplanNotFoundError, crud.InfraplanConflictError) as exc:
            raise _errors(exc) from exc
        return _row_out(row)


def _assign_confirmed(db, record, row_key: str, project_ids: list[int], note: str, username: str):
    report = crud.get_report_by_year(db, record.year)
    if report is None or report.parse_result_id != record.id:
        raise ToolError("Zu diesem Entwurf gehört kein übernommener Jahrgang.")
    section, _, number = row_key.rpartition("-")
    entry = (
        db.query(InfraplanEntry)
        .filter_by(report_id=report.id, section=section, lfd_nr=int(number) if number.isdigit() else -1)
        .one_or_none()
    )
    if entry is None:
        raise ToolError(f"Zeile {row_key} gibt es im Infraplan {record.year} nicht.")
    ids = crud.assign_entry(db, entry, project_ids, source=AGENT, username=username, note=note, replace=True)
    return {"row_key": row_key, "entry_id": entry.id, "project_ids": ids, "confirmed_year": record.year}


def create_infraplan_subproject(
    draft_id: int,
    row_key: str,
    parent_id: int,
    name: str | None = None,
    note: str | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Create a subproject (draft, no geometry) under ``parent_id`` for a row
    whose section has no project yet, and assign the row to it instead of the
    parent (requires ``infraplan.import``). Name defaults to the Maßnahme."""
    principal = get_principal(ctx)
    require(principal, PERMISSION)
    with tool_session(ctx) as db:
        record = _draft_or_error(db, draft_id)
        try:
            project, row = crud.create_subproject(
                db,
                record,
                row_key,
                parent_id,
                name,
                source=AGENT,
                user=load_user(db, principal),
                note=note,
            )
        except (crud.InfraplanNotFoundError, crud.InfraplanConflictError) as exc:
            raise _errors(exc) from exc
        return {"project_id": project.id, "name": project.name, "row": _row_out(row)}


def confirm_infraplan_import(
    draft_id: int, published_on: date | None = None, *, ctx: Context
) -> dict[str, Any]:
    """Take over the draft as its year (requires ``infraplan.import``). Refused
    while the parser reports warnings — those need a person in the frontend.
    published_on: publication date of the Infraplan (cover page), it dates the
    planning-state statements. Rows still open land in 'Offene Zuordnungen'."""
    principal = get_principal(ctx)
    require(principal, PERMISSION)
    with tool_session(ctx) as db:
        record = _draft_or_error(db, draft_id)
        try:
            return crud.confirm_parse_result(
                db,
                record,
                published_on=published_on,
                title=None,
                force=False,
                user=load_user(db, principal),
            )
        except (crud.InfraplanNotFoundError, crud.InfraplanConflictError) as exc:
            raise _errors(exc) from exc


def get_infraplan_page_image(draft_id: int, page: int, dpi: int = 110, *, ctx: Context) -> Image:
    """One page of the draft's PDF as image (requires ``infraplan.import``) —
    for reading KPI charts (pages from kpi_pages in list_infraplan_drafts).
    dpi 50–200; raise it when labels are hard to read."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        record = _draft_or_error(db, draft_id)
        try:
            png = crud.render_page(record, page, max(50, min(dpi, 200)))
        except crud.InfraplanNotFoundError as exc:
            raise _errors(exc) from exc
    return Image(data=png, format="png")


# --- KPIs ------------------------------------------------------------------------


def list_infraplan_kpis(*, ctx: Context) -> dict[str, Any]:
    """KPI definitions (stable key, name, unit, kind STEUERUNG|INFORMATION,
    category) — use these keys in set_infraplan_kpi_values (requires
    ``infraplan.import``)."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        return {
            "kpis": [
                {
                    "key": k.key,
                    "name": k.name,
                    "unit": k.unit,
                    "kind": k.kind,
                    "category": k.category,
                    "description": k.description,
                }
                for k in infraplan_crud.list_kpis(db)
            ]
        }


def get_infraplan_kpi_values(year: int, *, ctx: Context) -> dict[str, Any]:
    """Every KPI value of a confirmed year with its status UNGEPRUEFT /
    GEPRUEFT (requires ``infraplan.import``)."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        report = crud.get_report_by_year(db, year)
        if report is None:
            raise ToolError(f"Den Infraplan {year} gibt es nicht.")
        return {"year": year, "values": infraplan_crud.kpi_values(db, report)}


class KpiValueInput(InfraplanKpiValueInput):
    """year = the year the value refers to; value_kind IST (Rückschau) or
    ZIEL; series for sub-series (KMM-Teilprogramm, TEN-Netzebene), else
    omit; source_page = PDF page you read it from; value null removes it."""


class KpiDefinitionInput(InfraplanKpiDefinitionInput):
    """Only for a KPI that list_infraplan_kpis does not have (stable snake_case key)."""


def set_infraplan_kpi_values(
    year: int,
    values: list[KpiValueInput],
    definitions: list[KpiDefinitionInput] | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Write KPI values of a confirmed year, all or nothing (requires
    ``infraplan.import``). Values written here are UNGEPRUEFT and stay off the
    public page until a person approves the year. Cross-check against the
    totals in the text ("in Summe 266 Gleis-km") before writing."""
    principal = get_principal(ctx)
    require(principal, PERMISSION)
    if not values and not definitions:
        raise ToolError("Keine Werte übergeben.")
    with tool_session(ctx) as db:
        report = crud.get_report_by_year(db, year)
        if report is None:
            raise ToolError(f"Den Infraplan {year} gibt es nicht — erst bestätigen.")
        try:
            return infraplan_crud.set_kpi_values(
                db,
                report,
                [v.model_dump() for v in values],
                [d.model_dump() for d in definitions or []],
                status="UNGEPRUEFT",
                username=principal.username,
            )
        except infraplan_crud.InfraplanKpiError as exc:
            raise _errors(exc) from exc


# --- Per project --------------------------------------------------------------------


def get_project_infraplan(project_id: int, *, ctx: Context) -> dict[str, Any]:
    """Infraplan entries of a project across all years (section, state, IBN,
    cost, Befassung, who assigned it and why), the cost forecast and whether
    the project dropped out of the newest year. Read-only, public data."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        if db.get(Project, project_id) is None:
            raise ToolError(f"Projekt {project_id} gibt es nicht.")
        return infraplan_crud.project_infraplan(db, project_id)


def register(server: MCPServer) -> None:
    for fn in (
        list_infraplan_drafts,
        get_infraplan_draft,
        get_infraplan_page_image,
        list_infraplan_kpis,
        get_infraplan_kpi_values,
        get_project_infraplan,
    ):
        server.add_tool(fn, annotations=READ_ONLY)
    for fn in (
        start_infraplan_parse,
        apply_infraplan_suggestions,
        assign_infraplan_row,
        create_infraplan_subproject,
        confirm_infraplan_import,
        set_infraplan_kpi_values,
    ):
        server.add_tool(fn, annotations=WRITE)
