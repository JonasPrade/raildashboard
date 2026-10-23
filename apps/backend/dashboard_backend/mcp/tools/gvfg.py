"""GVFG-Bundesprogramm tools (feature-gvfg-import.md, Etappe 4).

Reads of the imported editions, their Vorhaben and the GVFG funding of a
project, plus correcting the project links. The import itself (PDF → review →
confirm) stays in the web UI. Amounts are in Mio. €.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy import case, exists, func, or_
from sqlalchemy.orm import selectinload

from dashboard_backend.crud.projects.projects import replacement_warnings
from dashboard_backend.crud import gvfg as gvfg_crud
from dashboard_backend.crud.projects import progress as progress_crud
from dashboard_backend.mcp.context import get_principal, load_user, require, tool_session
from dashboard_backend.mcp.tools.projects import MAX_LIMIT, READ_ONLY, WRITE, _project_or_error
from dashboard_backend.models.gvfg import GvfgEntry, GvfgProgram, gvfg_entry_project
from dashboard_backend.schemas.gvfg import GvfgEntrySchema, GvfgProgramSchema
from dashboard_backend.services.gvfg_parser import key_without_suffix, normalize_key

ASSIGN_PERMISSION = "assignment.manage"


def _num(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _edition(program: GvfgProgram) -> str:
    return f"{program.year_from}–{program.year_to}"


def _sum_line(entry: GvfgEntry):
    return next((a for a in entry.amounts if a.category == "SUM"), None)


def _categories(entry: GvfgEntry) -> list[str]:
    # Same rule as the overview page: a category counts when it carries aid.
    cats = [a.category for a in entry.amounts if a.category != "SUM" and (a.aid_total or 0) != 0]
    return list(dict.fromkeys(cats))


def _planned_aid(entry: GvfgEntry, program: GvfgProgram) -> float | None:
    """Aid within the edition's own years (the "geplant" columns)."""
    line = _sum_line(entry)
    labels = [p["label"] for p in program.periods or [] if p.get("kind") == "geplant"]
    if line is None or not labels or entry.part != "finanzrelevant":
        return None
    return float(sum(Decimal(str(line.periods.get(label) or 0)) for label in labels))


def _entry_summary(entry: GvfgEntry, program: GvfgProgram) -> dict[str, Any]:
    line = _sum_line(entry)
    return {
        "id": entry.id,
        "edition": _edition(program),
        "key": entry.key,
        "name": entry.name,
        "city": entry.city,
        "land": entry.land,
        "kind": entry.kind,
        "part": entry.part,
        "categories": _categories(entry),
        "lph": entry.lph,
        "funding_type": entry.funding_type,
        "funding_rate": entry.funding_rate,
        "commissioning_planned": entry.commissioning_planned,
        "commissioning_actual": entry.commissioning_actual,
        "cost_total": _num(line.cost_total) if line else None,
        "aid_total": _num(line.aid_total) if line else None,
        "aid_planned": _planned_aid(entry, program),
        "projects": [{"id": p.id, "name": p.name, "is_draft": bool(p.is_draft)} for p in sorted(entry.projects, key=lambda p: p.id)],
    }


def _program_or_newest(db, program_id: int | None) -> GvfgProgram:
    if program_id is not None:
        program = gvfg_crud.get_program(db, program_id)
        if program is None:
            raise ToolError(f"GVFG-Ausgabe {program_id} gibt es nicht.")
        return program
    program = db.query(GvfgProgram).order_by(GvfgProgram.year_from.desc()).first()
    if program is None:
        raise ToolError("Es ist noch keine GVFG-Ausgabe importiert.")
    return program


def _entry_or_error(db, entry_id: int) -> GvfgEntry:
    entry = db.get(GvfgEntry, entry_id)
    if entry is None:
        raise ToolError(f"GVFG-Vorhaben {entry_id} gibt es nicht.")
    return entry


def list_gvfg_programs(*, ctx: Context) -> dict[str, Any]:
    """Imported editions of the GVFG-Bundesprogramm, newest first, with their
    year columns (``periods``: label and kind ausgezahlt/voraussichtlich/geplant/
    rest), the number of Vorhaben and how many have no project."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        linked = exists().where(gvfg_entry_project.c.entry_id == GvfgEntry.id)
        counts = {
            pid: (total, unassigned or 0)
            for pid, total, unassigned in db.query(
                GvfgEntry.program_id,
                func.count(GvfgEntry.id),
                func.sum(case((linked, 0), else_=1)),
            ).group_by(GvfgEntry.program_id)
        }
        out = []
        for program in gvfg_crud.list_programs(db):
            data = GvfgProgramSchema.model_validate(program).model_dump(mode="json")
            total, unassigned = counts.get(program.id, (0, 0))
            data.update(edition=_edition(program), entries=total, entries_without_project=unassigned)
            out.append(data)
        return {"programs": out}


def list_gvfg_entries(
    program_id: int | None = None,
    search: str | None = None,
    land: str | None = None,
    kind: Literal["kommunal", "db"] | None = None,
    part: Literal["finanzrelevant", "nachrichtlich"] | None = None,
    funding_type: str | None = None,
    has_project: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Vorhaben of one edition (default: the newest), sorted by Land and key.

    - search: a key in any spelling ("02 G 509 _ A", also without suffix) or a
      case-insensitive substring of name, city or key
    - land: substring of the Land name (e.g. "Bayern")
    - funding_type: substring of the Fördertatbestand
    - has_project: false = Vorhaben without a project (to assign)
    Each entry carries the ∑ line (cost_total, aid_total, aid_planned within
    the edition's years; Mio. €), the categories with aid and the linked
    projects (``is_draft`` marks a draft project, e.g. one created by the import
    and not yet maintained). Details and the history across editions: get_gvfg_entry.
    """
    get_principal(ctx)
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    with tool_session(ctx) as db:
        program = _program_or_newest(db, program_id)
        query = db.query(GvfgEntry).filter(GvfgEntry.program_id == program.id)
        term = (search or "").strip()
        if term:
            key = normalize_key(term)
            if key:
                query = query.filter(
                    or_(GvfgEntry.key == key, GvfgEntry.key.like(f"{key_without_suffix(key)}\\_%", escape="\\"))
                )
            else:
                pattern = f"%{term}%"
                query = query.filter(
                    or_(
                        GvfgEntry.name.ilike(pattern),
                        GvfgEntry.city.ilike(pattern),
                        GvfgEntry.key.ilike(pattern),
                        GvfgEntry.key_raw.ilike(pattern),
                    )
                )
        if land and land.strip():
            query = query.filter(GvfgEntry.land.ilike(f"%{land.strip()}%"))
        if kind:
            query = query.filter(GvfgEntry.kind == kind)
        if part:
            query = query.filter(GvfgEntry.part == part)
        if funding_type and funding_type.strip():
            query = query.filter(GvfgEntry.funding_type.ilike(f"%{funding_type.strip()}%"))
        if has_project is not None:
            linked = exists().where(gvfg_entry_project.c.entry_id == GvfgEntry.id)
            query = query.filter(linked if has_project else ~linked)
        total = query.count()
        entries = (
            query.options(selectinload(GvfgEntry.amounts), selectinload(GvfgEntry.projects))
            .order_by(GvfgEntry.land, GvfgEntry.key)
            .offset(offset)
            .limit(limit)
            .all()
        )
        return {
            "program_id": program.id,
            "edition": _edition(program),
            "stand": program.stand.isoformat() if program.stand else None,
            "total": total,
            "offset": offset,
            "limit": limit,
            "entries": [_entry_summary(e, program) for e in entries],
        }


def get_gvfg_entry(entry_id: int, *, ctx: Context) -> dict[str, Any]:
    """One Vorhaben with all printed lines (∑/A/B/C; yearly aid per period label
    of the edition, Mio. €), its page in the PDF and ``history``: the same key in
    every edition (cost, aid, commissioning, categories, projects) to see cost
    increases, delays or a change from C to A."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        entry = _entry_or_error(db, entry_id)
        data = GvfgEntrySchema.model_validate(entry).model_dump(mode="json")
        data["edition"] = _edition(entry.program)
        data["page"] = entry.page
        data["periods"] = entry.program.periods
        data["history"] = [
            _entry_summary(e, e.program) for e in gvfg_crud.entries_with_key(db, entry.key)
        ]
        return data


def list_project_gvfg(
    project_id: int, with_subprojects: bool = False, *, ctx: Context
) -> dict[str, Any]:
    """GVFG funding of a project across all editions, newest edition first
    (compact; details per entry with get_gvfg_entry). with_subprojects adds the
    Vorhaben of its direct subprojects — a parent project funds through them.

    ``ibn_doubt`` (same as in get_project_progress → forecast) is set when the
    newest edition still plans a relevant part of the aid after the known
    Inbetriebnahme year: then question that year in your answer and cite the
    GVFG-Finanzreihe (edition, Mio. € per year after it)."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        entries = gvfg_crud.project_entries(db, project_id, with_subprojects)
        forecast = progress_crud.get_progress_view(db, project_id)["forecast"] if entries else None
        return {
            "entries": [_entry_summary(e, e.program) for e in entries],
            "ibn_doubt": forecast["ibn_doubt"] if forecast else None,
        }


def assign_gvfg_entry(
    entry_id: int, project_ids: list[int], all_editions: bool = False, *, ctx: Context
) -> dict[str, Any]:
    """Set the projects of a Vorhaben, replacing its current links (requires
    ``assignment.manage``). Use the project whose project_number is the key;
    after merging duplicates point the Vorhaben at the remaining project.
    all_editions: apply to the same key in every edition (a wrong link is
    usually wrong everywhere; the next import suggests the newest link).
    New projects join the group "GVFG" (Land 08 also "GVFG BW"); groups are
    never removed. An empty list removes the links."""
    principal = get_principal(ctx)
    require(principal, ASSIGN_PERMISSION)
    with tool_session(ctx) as db:
        entry = _entry_or_error(db, entry_id)
        targets = gvfg_crud.entries_with_key(db, entry.key) if all_editions else [entry]
        try:
            gvfg_crud.set_entry_projects(db, targets, project_ids, load_user(db, principal))
        except gvfg_crud.GvfgConfirmError as exc:
            raise ToolError(str(exc)) from exc
        out: dict[str, Any] = {"updated": [_entry_summary(e, e.program) for e in targets]}
        warnings = replacement_warnings(db, project_ids)
        if warnings:
            out["warnings"] = warnings
        return out


def register(server: MCPServer) -> None:
    for fn in (list_gvfg_programs, list_gvfg_entries, get_gvfg_entry, list_project_gvfg):
        server.add_tool(fn, annotations=READ_ONLY)
    server.add_tool(assign_gvfg_entry, annotations=WRITE)
