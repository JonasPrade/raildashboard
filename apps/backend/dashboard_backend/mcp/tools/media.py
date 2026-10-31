"""Medien/Presse reports (feature-project-progress.md → „Medien/Presse“) over MCP.

The agent reads the article itself and writes what it found — no server-side
fetch or LLM extraction (the Fulda pattern). A report says which main phase a
project is in according to the press; only a *confirmed* report with a phase
feeds the planning state, as a low-trust (0.4) derived MEDIEN observation.
Same right as the REST endpoints: ``progress.edit``, also for reading.
The skill ``medien-import`` describes the workflow.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from dashboard_backend.crud import media as media_crud
from dashboard_backend.crud._importer_common import ProjectNotFoundError
from dashboard_backend.crud.projects.archive import archived_warnings
from dashboard_backend.mcp.context import get_principal, load_user, require, tool_session
from dashboard_backend.mcp.tools.projects import DESTRUCTIVE, MAX_LIMIT, READ_ONLY, WRITE
from dashboard_backend.models.projects.media_report import MediaReport
from dashboard_backend.schemas.projects.progress_schema import MainPhaseLiteral

PERMISSION = "progress.edit"
_RAW_TEXT_PREVIEW = 300


def _json(entry: dict, *, full_text: bool = False) -> dict[str, Any]:
    out = dict(entry)
    for key in ("published_date", "observed_date", "created_at"):
        if out.get(key) is not None:
            out[key] = out[key].isoformat()
    raw = out.get("raw_text")
    if raw and not full_text and len(raw) > _RAW_TEXT_PREVIEW:
        out["raw_text"] = raw[: _RAW_TEXT_PREVIEW - 1] + "…"
    out["feeds_planning_state"] = bool(
        out.get("confirmed") and out.get("project_id") and out.get("asserted_phase")
    )
    return out


def _warnings(db, entry: dict, wanted_confirmed: bool | None) -> list[str]:
    warnings: list[str] = []
    if wanted_confirmed and not entry["project_id"]:
        warnings.append("Nicht bestätigt: dem Bericht ist kein Projekt zugeordnet.")
    if entry["confirmed"] and not entry["asserted_phase"]:
        warnings.append(
            "Bestätigt, aber ohne asserted_phase — der Bericht zählt erst mit einer Phase."
        )
    if entry["project_id"]:
        warnings.extend(archived_warnings(db, [entry["project_id"]]))
    return warnings


def list_media_reports(
    project_id: int | None = None,
    only_unconfirmed: bool = False,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Press/media reports, newest first (requires ``progress.edit``): url,
    publication, dates, quote, asserted phase, assigned or suggested project,
    confirmed, ``feeds_planning_state``. raw_text is shortened.
    - project_id: reports assigned to this project
    - only_unconfirmed: not yet confirmed (the review list)
    - search: part of url, publication or quote (case-insensitive)
    Paged with limit/offset; ``total`` counts all matches. Check here before
    add_media_report whether the article is already in."""
    require(get_principal(ctx), PERMISSION)
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    with tool_session(ctx) as db:
        rows = media_crud.list_entries(db, only_unconfirmed=only_unconfirmed)
    if project_id is not None:
        rows = [r for r in rows if r["project_id"] == project_id]
    if search and search.strip():
        needle = search.strip().lower()
        rows = [
            r
            for r in rows
            if any(needle in (r.get(key) or "").lower() for key in ("url", "publication", "quote"))
        ]
    return {
        "total": len(rows),
        "offset": offset,
        "reports": [_json(r) for r in rows[offset : offset + limit]],
    }


def add_media_report(
    url: str,
    publication: str,
    published_date: date,
    quote: str,
    project_id: int | None = None,
    asserted_phase: MainPhaseLiteral | None = None,
    observed_date: date | None = None,
    raw_text: str | None = None,
    confirmed: bool = False,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Add a press/media report you have read (requires ``progress.edit``).
    One report = one article and one project; an article about several projects
    gets one report per project.
    - url, publication (e.g. "Stuttgarter Zeitung"), published_date (JJJJ-MM-TT)
    - quote: the sentence(s) that support the phase, verbatim
    - asserted_phase: the main phase the article says the project is in
      (NICHT_GESTARTET, VORPLANUNG, GENEHMIGUNGSPLANUNG, BAU, IN_BETRIEB);
      leave empty if the article states none — then it never counts
    - observed_date: when the stated situation held (default: published_date)
    - raw_text: optional, the relevant passage or article text
    - confirmed=true: the report counts at once (needs project_id and a phase)
      as a derived MEDIEN observation with trust 0.4; otherwise it waits for
      review (update_media_report).
    The same url for the same project is refused (see list_media_reports)."""
    principal = get_principal(ctx)
    require(principal, PERMISSION)
    url, publication, quote = url.strip(), publication.strip(), quote.strip()
    if not url or not publication or not quote:
        raise ToolError("url, publication und quote dürfen nicht leer sein.")
    with tool_session(ctx) as db:
        existing = media_crud.find_by_url(db, url, project_id)
        if existing is not None:
            raise ToolError(
                f"Diesen Artikel gibt es für dieses Projekt schon (Bericht {existing.id}); "
                "ändern mit update_media_report."
            )
        user = load_user(db, principal)
        try:
            entry = media_crud.create_entry(
                db,
                {
                    "url": url,
                    "publication": publication,
                    "published_date": published_date,
                    "quote": quote,
                    "project_id": project_id,
                    "asserted_phase": asserted_phase,
                    "observed_date": observed_date,
                    "raw_text": raw_text,
                    "confirmed": confirmed,
                },
                user,
            )
        except ProjectNotFoundError as exc:
            raise ToolError(f"Projekt {project_id} nicht gefunden.") from exc
        out = _json(entry)
        warnings = _warnings(db, entry, confirmed)
        if warnings:
            out["warnings"] = warnings
        return out


def update_media_report(
    report_id: int,
    project_id: int | None = None,
    clear_project: bool = False,
    asserted_phase: MainPhaseLiteral | None = None,
    clear_phase: bool = False,
    confirmed: bool | None = None,
    url: str | None = None,
    publication: str | None = None,
    published_date: date | None = None,
    observed_date: date | None = None,
    quote: str | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Change a media report (requires ``progress.edit``): fields, the project
    (project_id; clear_project=true removes it), the phase (clear_phase=true
    removes it) or confirmed (true = counts for the planning state, false =
    withdraw). The planning state of the previous and the new project is
    recomputed at once. Only passed fields change."""
    require(get_principal(ctx), PERMISSION)
    if project_id is not None and clear_project:
        raise ToolError("project_id und clear_project schließen sich aus.")
    if asserted_phase is not None and clear_phase:
        raise ToolError("asserted_phase und clear_phase schließen sich aus.")
    payload: dict[str, Any] = {
        key: value
        for key, value in {
            "url": url,
            "publication": publication,
            "published_date": published_date,
            "observed_date": observed_date,
            "quote": quote,
            "asserted_phase": asserted_phase,
            "confirmed": confirmed,
            "project_id": project_id,
        }.items()
        if value is not None
    }
    if clear_project:
        payload["project_id"] = None
        payload["confirmed"] = False
    if clear_phase:
        payload["asserted_phase"] = None
    if not payload:
        raise ToolError("Keine Änderungen übergeben.")
    with tool_session(ctx) as db:
        if payload.get("confirmed"):
            # Confirming needs a project; without one the report stays open.
            current = db.get(MediaReport, report_id)
            if current is not None and payload.get("project_id", current.project_id) is None:
                payload["confirmed"] = False
        try:
            entry = media_crud.update_entry(db, report_id, payload)
        except ProjectNotFoundError as exc:
            raise ToolError(f"Projekt {project_id} nicht gefunden.") from exc
        if entry is None:
            raise ToolError(f"Medienbericht {report_id} nicht gefunden.")
        out = _json(entry)
        warnings = _warnings(db, entry, confirmed)
        if warnings:
            out["warnings"] = warnings
        return out


def delete_media_report(report_id: int, *, ctx: Context) -> dict[str, Any]:
    """Delete a media report (requires ``progress.edit``), e.g. a duplicate or
    a misread article; its derived observation goes with it and the project's
    planning state is recomputed."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        if not media_crud.delete_entry(db, report_id):
            raise ToolError(f"Medienbericht {report_id} nicht gefunden.")
        return {"deleted": report_id}


def register(server: MCPServer) -> None:
    server.add_tool(list_media_reports, annotations=READ_ONLY)
    server.add_tool(add_media_report, annotations=WRITE)
    server.add_tool(update_media_report, annotations=WRITE)
    server.add_tool(delete_media_report, annotations=DESTRUCTIVE)
