"""Infraplan import tools (feature-infraplan-import.md → "MCP & Skill" and
"Ausbau für den Import 2027").

The PDF is uploaded in the frontend; from there an agent carries the import
as far as it can: re-parse, take over safe suggestions, assign the rest with a
reason (many rows per call), create missing subprojects, confirm (never with
parser warnings) and read the KPI charts from the page text, the image only
where the text is not enough (values stay unchecked until a person approves
the year). The skill ``.claude/skills/infraplan-import`` holds the
procedure. Every tool requires ``infraplan.import``; the REST endpoints call
the same CRUD functions with source MANUAL, these with AGENT.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.mcpserver.utilities.types import Image
from pydantic import BaseModel, Field

from dashboard_backend.crud.projects.archive import archived_warnings
from dashboard_backend.crud import infraplan as infraplan_crud
from dashboard_backend.crud import infraplan_import as crud
from dashboard_backend.mcp.context import get_principal, load_user, require, tool_session
from dashboard_backend.mcp.tools.projects import READ_ONLY, WRITE
from dashboard_backend.models.infraplan import InfraplanParseResult
from dashboard_backend.models.projects.project import Project
from dashboard_backend.schemas.infraplan import (
    InfraplanKpiDefinitionInput,
    InfraplanKpiValueInput,
)
from dashboard_backend.schemas.infraplan_import import InfraplanRowPatch
from dashboard_backend.services.infraplan_page_text import layout_text, suggest_chart_values
from dashboard_backend.tasks.infraplan import SECTION_TITLES

PERMISSION = "infraplan.import"
AGENT = "AGENT"
_MAX_ROWS = 300
_MAX_BATCH = 300

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


def _compact_row(row: dict[str, Any], names: dict[int, str]) -> dict[str, Any]:
    """Row key, texts, Länder, assignment and the best suggestion only."""
    out: dict[str, Any] = {
        "row_key": row["row_key"],
        "bezeichnung": row.get("bezeichnung"),
        "massnahme": row.get("massnahme"),
        "laender": row.get("laender"),
    }
    if row.get("primary_number"):
        out["number"] = row["primary_number"]
    if row.get("project_ids"):
        out["project_ids"] = row["project_ids"]
    suggestions = row.get("suggestions") or []
    if suggestions:
        best = suggestions[0]
        out["best"] = {
            "project_id": best["project_id"],
            "name": names.get(best["project_id"]),
            "confidence": best["confidence"],
            "reason": best["reason"],
            **({"detail": best["detail"]} if best.get("detail") else {}),
        }
    return {k: v for k, v in out.items() if v not in (None, [], "")}


def get_infraplan_draft(
    draft_id: int,
    section: SectionLiteral | None = None,
    only_open: bool = False,
    offset: int = 0,
    limit: int | None = None,
    compact: bool = False,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Rows of a draft with suggestions ({project_id, confidence, reason
    NUMBER|GVFG_KEY|PREVIOUS_YEAR|ALIAS|CONTEXT|FUZZY, detail}) and assignment
    (requires ``infraplan.import``).

    - section: BP_A–BP_D (Bedarfsplan Teil A–D), GVFG_A, GVFG_C, INVKG
    - only_open: rows without projects only
    - compact: true = all sections in one answer (limit up to 300), per row
      only row_key, Bezeichnung, Maßnahme, Länder, assigned project_ids and the
      best suggestion with its project name — the overview to plan the work;
      false = full rows (default limit 100)
    Also returns the referenced projects, the warnings, the projects of the
    previous year without a row in this draft (renamings to check) and the
    section titles."""
    require(get_principal(ctx), PERMISSION)
    limit = max(1, min(limit or (_MAX_ROWS if compact else 100), _MAX_ROWS))
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
        result: dict[str, Any] = {
            "draft": _draft_summary(db, record),
            "sections": SECTION_TITLES,
            "total_matching": len(rows),
            "offset": offset,
            "previous_year": previous_year,
            "missing_from_previous": [m.model_dump() for m in missing],
        }
        if compact:
            names = {int(k): v.name for k, v in projects.items()}
            result["rows"] = [_compact_row(r, names) for r in page]
            assigned = {pid for r in page for pid in (r.get("project_ids") or [])}
            result["assigned_projects"] = {str(pid): names.get(pid) for pid in sorted(assigned)}
            return result
        used = {pid for r in page for pid in (r.get("project_ids") or [])} | {
            s["project_id"] for r in page for s in (r.get("suggestions") or [])
        }
        result["rows"] = [_row_out(r) for r in page]
        result["projects"] = {k: v.model_dump() for k, v in projects.items() if int(k) in used}
        return result


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
    changes the confirmed entry of that year (planning state follows). For
    more than a few rows use assign_infraplan_rows."""
    principal = get_principal(ctx)
    require(principal, PERMISSION)
    if not note.strip():
        raise ToolError("Eine Begründung (note) ist Pflicht.")
    with tool_session(ctx) as db:
        record = _draft_or_error(db, draft_id)
        try:
            if record.confirmed_at is not None:
                result = crud.assign_rows(
                    db, record, [(row_key, project_ids, note.strip())],
                    source=AGENT, username=principal.username,
                )[0]
                if not result["ok"]:
                    raise ToolError(result["error"])
                out = {
                    "row_key": row_key,
                    "entry_id": result["entry_id"],
                    "project_ids": result["project_ids"],
                    "confirmed_year": record.year,
                }
            else:
                row = crud.patch_row(
                    db,
                    record,
                    row_key,
                    InfraplanRowPatch(project_ids=project_ids, note=note),
                    source=AGENT,
                    username=principal.username,
                )
                out = _row_out(row)
        except (crud.InfraplanNotFoundError, crud.InfraplanConflictError) as exc:
            raise _errors(exc) from exc
        warnings = archived_warnings(db, project_ids)
        if warnings:
            out["warnings"] = warnings
        return out


class RowAssignment(BaseModel):
    """One row: its key, the projects (replacing what is there; empty list
    removes the assignment) and the reason in one sentence."""

    row_key: str
    project_ids: list[int]
    note: str


def assign_infraplan_rows(
    draft_id: int, rows: list[RowAssignment], *, ctx: Context
) -> dict[str, Any]:
    """Assign many rows in one call (requires ``infraplan.import``) — same
    rules as assign_infraplan_row, ``note`` required per row. Works on a draft
    and, after the confirmation, on the confirmed year (planning state is
    recomputed once at the end). A failing row does not stop the others: the
    result lists ``ok`` with the project_ids or ``error`` per row; resend only
    the failed ones."""
    principal = get_principal(ctx)
    require(principal, PERMISSION)
    if not rows:
        raise ToolError("Keine Zeilen übergeben.")
    if len(rows) > _MAX_BATCH:
        raise ToolError(f"Höchstens {_MAX_BATCH} Zeilen je Aufruf.")
    with tool_session(ctx) as db:
        record = _draft_or_error(db, draft_id)
        items = [r for r in rows if r.note.strip()]
        try:
            results = crud.assign_rows(
                db, record, [(r.row_key, r.project_ids, r.note.strip()) for r in items],
                source=AGENT, username=principal.username,
            )
        except (crud.InfraplanNotFoundError, crud.InfraplanConflictError) as exc:
            raise _errors(exc) from exc
        done = iter(results)
        out = [
            next(done)
            if r.note.strip()
            else {"row_key": r.row_key, "ok": False, "error": "Eine Begründung (note) ist Pflicht."}
            for r in rows
        ]
        result = {
            "ok": sum(1 for r in out if r["ok"]),
            "failed": sum(1 for r in out if not r["ok"]),
            "confirmed_year": record.year if record.confirmed_at else None,
            "rows": out,
        }
        warnings = archived_warnings(db, [pid for r in items for pid in r.project_ids])
        if warnings:
            result["warnings"] = warnings
        return result


def create_infraplan_subproject(
    draft_id: int,
    row_key: str,
    parent_id: int | None = None,
    name: str | None = None,
    note: str | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Create a project (draft, no geometry) for a row that no project fits
    and assign the row to it (requires ``infraplan.import``). With
    ``parent_id`` it is a subproject and replaces the parent in the row's
    assignment; without, a project of its own that also takes the row's
    number (GVFG key, InvKG number). Works before and after the confirmation.
    Name defaults to the Maßnahme. For several rows use
    create_infraplan_subprojects."""
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


class SubprojectItem(BaseModel):
    """A row and the project to create for it: under ``parent_id``, or on its
    own without; ``name`` defaults to the Maßnahme, ``note`` is the reason."""

    row_key: str
    parent_id: int | None = None
    name: str | None = Field(None, max_length=255)
    note: str | None = None


def create_infraplan_subprojects(
    draft_id: int, items: list[SubprojectItem], *, ctx: Context
) -> dict[str, Any]:
    """Create many projects with their row assignment in one call (requires
    ``infraplan.import``) — same rules as create_infraplan_subproject. Only
    for a parent that is beyond doubt; a failing row does not stop the
    others (``ok`` with project_id or ``error`` per row)."""
    principal = get_principal(ctx)
    require(principal, PERMISSION)
    if not items:
        raise ToolError("Keine Zeilen übergeben.")
    if len(items) > _MAX_BATCH:
        raise ToolError(f"Höchstens {_MAX_BATCH} Zeilen je Aufruf.")
    with tool_session(ctx) as db:
        record = _draft_or_error(db, draft_id)
        try:
            results = crud.create_subprojects(
                db,
                record,
                [(i.row_key, i.parent_id, i.name, i.note) for i in items],
                source=AGENT,
                user=load_user(db, principal),
            )
        except (crud.InfraplanNotFoundError, crud.InfraplanConflictError) as exc:
            raise _errors(exc) from exc
        out = []
        for result in results:
            if result["ok"]:
                out.append(
                    {
                        "row_key": result["row_key"],
                        "ok": True,
                        "project_id": result["project_id"],
                        "name": result["name"],
                        "project_ids": result["row"].get("project_ids"),
                    }
                )
            else:
                out.append({"row_key": result["row_key"], "ok": False, "error": result["error"]})
        return {
            "ok": sum(1 for r in out if r["ok"]),
            "failed": sum(1 for r in out if not r["ok"]),
            "rows": out,
        }


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
    for KPI charts the text does not settle (stacked bars, colours); try
    get_infraplan_page_text / suggest_infraplan_kpi_values first.
    dpi 50–200; raise it when labels are hard to read."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        record = _draft_or_error(db, draft_id)
        try:
            png = crud.render_page(record, page, max(50, min(dpi, 200)))
        except crud.InfraplanNotFoundError as exc:
            raise _errors(exc) from exc
    return Image(data=png, format="png")


def get_infraplan_page_text(draft_id: int, page: int, *, ctx: Context) -> dict[str, Any]:
    """Text of one PDF page with its layout (requires ``infraplan.import``):
    one line per text line, ``"<top>: word@x word@x …"`` (points from the top
    and the word's horizontal centre). A chart's value label stands at the
    x of its year on the axis below — so most KPI values can be read without
    the page image. Pages with KPI charts: kpi_pages in list_infraplan_drafts."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        record = _draft_or_error(db, draft_id)
        try:
            words = crud.page_words(record, page)
        except crud.InfraplanNotFoundError as exc:
            raise _errors(exc) from exc
    return {"draft_id": draft_id, "page": page, "lines": layout_text(words)}


def suggest_infraplan_kpi_values(draft_id: int, page: int, *, ctx: Context) -> dict[str, Any]:
    """Unchecked value suggestions for the charts of one page (requires
    ``infraplan.import``): per year axis the number labels above it, assigned
    to the year below by x position. ``kind_guess`` is IST before the plan
    year and ZIEL from it on (the colour is not in the text — check the
    legend). ``stacked`` lists years with several labels (stacked bars: read
    from the image), ``missing`` years without a label (a zero, or no bar).
    Nothing is written; check against the totals in the text, then use
    set_infraplan_kpi_values."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        record = _draft_or_error(db, draft_id)
        try:
            words = crud.page_words(record, page)
        except crud.InfraplanNotFoundError as exc:
            raise _errors(exc) from exc
        kpi_page = next((p for p in record.kpi_pages_json or [] if p.get("page") == page), None)
    charts = suggest_chart_values(words, plan_year=record.year)
    return {
        "draft_id": draft_id,
        "page": page,
        "kpi_page": kpi_page,
        "charts": charts,
        "note": None if charts else "Keine Jahresachse im Text — Diagramm mit get_infraplan_page_image lesen.",
    }


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
        get_infraplan_page_text,
        suggest_infraplan_kpi_values,
        list_infraplan_kpis,
        get_infraplan_kpi_values,
        get_project_infraplan,
    ):
        server.add_tool(fn, annotations=READ_ONLY)
    for fn in (
        start_infraplan_parse,
        apply_infraplan_suggestions,
        assign_infraplan_row,
        assign_infraplan_rows,
        create_infraplan_subproject,
        create_infraplan_subprojects,
        confirm_infraplan_import,
        set_infraplan_kpi_values,
    ):
        server.add_tool(fn, annotations=WRITE)
