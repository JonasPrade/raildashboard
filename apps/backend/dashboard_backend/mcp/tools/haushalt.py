"""Haushalt follow-up tools (feature-haushalt-import.md → „Nacharbeit per MCP“).

The import itself (PDF → review → confirm) stays in the web UI. These tools work
off what a confirmed report year left open: FinVes without a project, Sammel-FinVes
without projects in that year, and unmatched rows. Permanent links of regular
FinVes are set with ``update_finve_projects`` (finves.py); the year links of a
Sammel-FinVe here. Amounts in T€.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy import and_, exists, func, or_

from dashboard_backend.crud import haushalt_import as haushalt_crud
from dashboard_backend.crud import sammel_finve_links as sammel_crud
from dashboard_backend.crud.finve_links import FinveLinkError
from dashboard_backend.crud.projects.archive import successor_map
from dashboard_backend.mcp.context import get_principal, load_user, require, tool_session
from dashboard_backend.mcp.tools.projects import MAX_LIMIT, READ_ONLY, WRITE
from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.haushalt.haushalts_parse_result import HaushaltsParseResult
from dashboard_backend.models.haushalt.unmatched_budget_row import UnmatchedBudgetRow
from dashboard_backend.models.projects.budget import Budget
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.project import Project
from dashboard_backend.tasks.finve_matching import (
    suggest_per_erlaeuterung_project,
    suggest_projects_for_finve,
)

LINK_PERMISSION = "finve.edit"
IMPORT_PERMISSION = "haushalt.import"
MAX_SUGGESTIONS = 15


def _listed_in(year: int):
    return exists().where(Budget.fin_ve == Finve.id, Budget.budget_year == year)


def _has_project(year: int):
    """A FinVe counts as assigned in ``year``: a permanent link, or for a
    Sammel-FinVe a year link of that year to a project that is not archived."""
    permanent = exists().where(
        FinveToProject.finve_id == Finve.id, FinveToProject.haushalt_year.is_(None)
    )
    yearly = exists().where(
        FinveToProject.finve_id == Finve.id,
        FinveToProject.haushalt_year == year,
        FinveToProject.project_id == Project.id,
        Project.is_archived.is_(False),
    )
    return or_(permanent, and_(Finve.is_sammel_finve.is_(True), yearly))


def _years(db) -> list[int]:
    budget = {y for (y,) in db.query(Budget.budget_year).distinct()}
    parsed = {y for (y,) in db.query(HaushaltsParseResult.haushalt_year).distinct()}
    return sorted(budget | parsed, reverse=True)


def _year_or_newest(db, year: int | None) -> int:
    if year is not None:
        return year
    newest = db.query(func.max(Budget.budget_year)).scalar()
    if newest is None:
        raise ToolError("Es ist noch kein Haushaltsjahr importiert.")
    return int(newest)


def _parse_rows(db, year: int) -> dict[tuple[str, Any], dict[str, Any]]:
    """Rows of the newest confirmed import of ``year``, by FinVe number and by key."""
    record = (
        db.query(HaushaltsParseResult)
        .filter(
            HaushaltsParseResult.haushalt_year == year,
            HaushaltsParseResult.confirmed_at.isnot(None),
        )
        .order_by(HaushaltsParseResult.confirmed_at.desc())
        .first()
    )
    rows: dict[tuple[str, Any], dict[str, Any]] = {}
    for row in ((record.result_json or {}).get("rows") or []) if record else []:
        if not isinstance(row, dict):
            continue
        if row.get("finve_key"):
            rows[("key", row["finve_key"])] = row
        elif row.get("finve_number") is not None:
            rows[("id", row["finve_number"])] = row
    return rows


def _row_for(rows: dict, finve: Finve) -> dict[str, Any] | None:
    if finve.finve_key:
        return rows.get(("key", finve.finve_key))
    return rows.get(("id", finve.id))


def _project_ref(p: Project) -> dict[str, Any]:
    ref: dict[str, Any] = {"id": p.id, "name": p.name}
    if p.is_draft:
        ref["is_draft"] = True
    if p.is_archived:
        ref["is_archived"] = True
    return ref


def _year_links(db, finve: Finve, year: int) -> list[Project]:
    if finve.is_sammel_finve:
        projects = sammel_crud.year_projects(db, finve.id, year)
    else:
        projects = []
    permanent = (
        db.query(Project)
        .join(FinveToProject, FinveToProject.project_id == Project.id)
        .filter(FinveToProject.finve_id == finve.id, FinveToProject.haushalt_year.is_(None))
        .order_by(Project.id)
        .all()
    )
    seen = {p.id for p in projects}
    return projects + [p for p in permanent if p.id not in seen]


def _finve_row(db, finve: Finve, year: int, budget: Budget | None, parse_row: dict | None) -> dict:
    projects = _year_links(db, finve, year)
    out: dict[str, Any] = {
        "id": finve.id,
        "name": finve.name,
        "finve_key": finve.finve_key,
        "temporary_finve_number": bool(finve.temporary_finve_number),
        "is_sammel_finve": bool(finve.is_sammel_finve),
        "table_number": parse_row.get("table_number") if parse_row else None,
        "lfd_nr": budget.lfd_nr if budget else None,
        "bedarfsplan_number": budget.bedarfsplan_number if budget else None,
        "cost_estimate_actual": budget.cost_estimate_actual if budget else None,
        "year_planned": budget.year_planned if budget else None,
        "projects": [_project_ref(p) for p in projects],
        "open": not any(not p.is_archived for p in projects),
    }
    if parse_row and parse_row.get("erlaeuterung_projects"):
        out["erlaeuterung_projects"] = parse_row["erlaeuterung_projects"]
    if parse_row and parse_row.get("review_notes"):
        out["review_notes"] = parse_row["review_notes"]
    return out


def list_haushalt_years(*, ctx: Context) -> dict[str, Any]:
    """Imported Haushalt report years, newest first, with what is left to do:
    ``finves`` listed in the year, ``finves_without_project`` (Sammel-FinVes count
    as open without a non-archived project in that year; ``sammel_without_project``
    of them), ``unmatched_open`` (rows the import could not attach to a FinVe) and
    the import runs (``confirmed_at`` null = still waiting for the review in the UI)."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        out = []
        for year in _years(db):
            listed = db.query(Finve.id).filter(_listed_in(year))
            open_q = listed.filter(~_has_project(year))
            runs = (
                db.query(HaushaltsParseResult)
                .filter(HaushaltsParseResult.haushalt_year == year)
                .order_by(HaushaltsParseResult.parsed_at.desc())
                .all()
            )
            out.append(
                {
                    "year": year,
                    "finves": listed.count(),
                    "finves_without_project": open_q.count(),
                    "sammel_without_project": open_q.filter(Finve.is_sammel_finve.is_(True)).count(),
                    "unmatched_open": db.query(UnmatchedBudgetRow)
                    .filter(
                        UnmatchedBudgetRow.haushalt_year == year,
                        UnmatchedBudgetRow.resolved.is_(False),
                    )
                    .count(),
                    "imports": [
                        {
                            "parse_result_id": r.id,
                            "pdf_filename": r.pdf_filename,
                            "status": r.status,
                            "parsed_at": r.parsed_at.isoformat() if r.parsed_at else None,
                            "confirmed_at": r.confirmed_at.isoformat() if r.confirmed_at else None,
                        }
                        for r in runs
                    ],
                }
            )
        return {"years": out}


def list_haushalt_finves(
    haushalt_year: int | None = None,
    open_only: bool = False,
    is_sammel_finve: bool | None = None,
    table_number: int | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """FinVes listed in one Haushalt year (default: the newest), sorted by number.

    - open_only: only FinVes without a project in that year (a Sammel-FinVe needs a
      non-archived project linked for this very year)
    - table_number: table of Teil B (1 Bedarfsplan, 2 Lärmsanierung, 3 ERTMS,
      4 Kleine und Mittlere Maßnahmen, 5 InvKG)
    - search: FinVe number or substring of name, key, lfd. Nr. or Bedarfsplan number
    Each entry carries that year's budget line (T€), ``projects`` as they count in
    that year (year links of a Sammel-FinVe plus permanent links; archived ones
    marked) and, from the confirmed import, ``erlaeuterung_projects`` (measures the
    report names under a Sammel-FinVe) and ``review_notes``. Candidates for an
    open FinVe: suggest_haushalt_finve_projects."""
    get_principal(ctx)
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    with tool_session(ctx) as db:
        year = _year_or_newest(db, haushalt_year)
        query = db.query(Finve, Budget).join(
            Budget, and_(Budget.fin_ve == Finve.id, Budget.budget_year == year)
        )
        if open_only:
            query = query.filter(~_has_project(year))
        if is_sammel_finve is not None:
            query = query.filter(Finve.is_sammel_finve.is_(is_sammel_finve))
        if table_number is not None:
            prefix = f"t{table_number}:"
            query = query.filter(
                Finve.finve_key.like(f"{prefix}%")
                if table_number != 1
                else or_(Finve.finve_key.is_(None), Finve.finve_key.like(f"{prefix}%"))
            )
        term = (search or "").strip()
        if term:
            pattern = f"%{term}%"
            conditions = [
                Finve.name.ilike(pattern),
                Finve.finve_key.ilike(pattern),
                Budget.lfd_nr.ilike(pattern),
                Budget.bedarfsplan_number.ilike(pattern),
            ]
            if term.isdigit():
                conditions.append(Finve.id == int(term))
            query = query.filter(or_(*conditions))
        total = query.count()
        page = query.order_by(Finve.id).offset(offset).limit(limit).all()
        rows = _parse_rows(db, year)
        return {
            "haushalt_year": year,
            "total": total,
            "offset": offset,
            "limit": limit,
            "finves": [_finve_row(db, f, year, b, _row_for(rows, f)) for f, b in page],
        }


def suggest_haushalt_finve_projects(
    finve_id: int, haushalt_year: int | None = None, *, ctx: Context
) -> dict[str, Any]:
    """Candidate projects for a FinVe, each with the reasons that point to it:

    - ``erlaeuterung``: a measure the report names under the Sammel-FinVe
      (``haushalt_year``, default newest year of the FinVe) matches the project name
    - ``other_year``: the project is linked to this Sammel-FinVe in another year
    - ``archived_link``: the year's link goes to an archived project (candidate
      is its successor)
    - ``bedarfsplan``: the project carries another FinVe with the same
      Bedarfsplan number
    - ``name``: the FinVe name resembles the project name
    Archived projects are replaced by their successor (``successor_of``) or left
    out. Candidates are hints — check name, section and Bedarfsplan number before
    assigning (update_finve_projects / set_sammel_finve_year_projects)."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        finve = db.get(Finve, finve_id)
        if finve is None:
            raise ToolError(f"FinVe {finve_id} nicht gefunden.")
        years = sammel_crud.budget_years(db, finve_id)
        year = haushalt_year if haushalt_year is not None else (years[-1] if years else None)
        reasons: dict[int, list[str]] = {}

        def note(pid: int | None, reason: str) -> None:
            if pid is not None and reason not in reasons.setdefault(pid, []):
                reasons[pid].append(reason)

        projects = (
            db.query(Project.id, Project.name).filter(Project.is_archived.is_(False)).all()
        )
        parse_row = _row_for(_parse_rows(db, year), finve) if year is not None else None
        names = (parse_row or {}).get("erlaeuterung_projects") or []
        for name, pid in zip(names, suggest_per_erlaeuterung_project(names, projects)):
            note(pid, f"erlaeuterung {year}: „{name}“")

        if finve.is_sammel_finve:
            links = (
                db.query(FinveToProject.project_id, FinveToProject.haushalt_year, Project.is_archived)
                .join(Project, Project.id == FinveToProject.project_id)
                .filter(FinveToProject.finve_id == finve_id, FinveToProject.haushalt_year.isnot(None))
            )
            for pid, link_year, is_archived in links.order_by(FinveToProject.haushalt_year.desc()):
                if link_year != year:
                    note(pid, f"other_year {link_year}")
                elif is_archived:
                    # The year's link to an archived project points to its successor.
                    note(pid, f"archived_link {link_year}")

        numbers = {
            n for (n,) in db.query(Budget.bedarfsplan_number).filter(
                Budget.fin_ve == finve_id, Budget.bedarfsplan_number.isnot(None)
            )
        }
        if numbers:
            for pid, other_id, number in (
                db.query(FinveToProject.project_id, Budget.fin_ve, Budget.bedarfsplan_number)
                .join(Budget, Budget.fin_ve == FinveToProject.finve_id)
                .filter(
                    Budget.bedarfsplan_number.in_(numbers),
                    Budget.fin_ve != finve_id,
                    FinveToProject.haushalt_year.is_(None),
                )
                .distinct()
            ):
                note(pid, f"bedarfsplan {number} (FinVe {other_id})")

        for pid in suggest_projects_for_finve(finve.name or "", projects):
            note(pid, "name")

        successors = successor_map(db)
        merged: dict[int, dict[str, Any]] = {}
        for pid, why in reasons.items():
            target = successors.get(pid, pid)
            entry = merged.setdefault(target, {"reasons": [], "successor_of": []})
            entry["reasons"] += [r for r in why if r not in entry["reasons"]]
            if target != pid:
                entry["successor_of"].append(pid)
        found = {
            p.id: p
            for p in db.query(Project).filter(
                Project.id.in_(merged), Project.is_archived.is_(False)
            )
        }
        linked = {p.id for p in _year_links(db, finve, year)} if year is not None else set()
        candidates = []
        for pid, entry in merged.items():
            project = found.get(pid)
            if project is None:
                continue
            item = {**_project_ref(project), "reasons": entry["reasons"]}
            if entry["successor_of"]:
                item["successor_of"] = sorted(entry["successor_of"])
            if pid in linked:
                item["already_linked"] = True
            candidates.append(item)
        candidates.sort(key=lambda c: (-len(c["reasons"]), c["id"]))
        return {
            "finve_id": finve_id,
            "name": finve.name,
            "is_sammel_finve": bool(finve.is_sammel_finve),
            "haushalt_year": year,
            "budget_years": years,
            "erlaeuterung_projects": names,
            "candidates": candidates[:MAX_SUGGESTIONS],
        }


def set_sammel_finve_year_projects(
    finve_id: int,
    haushalt_year: int,
    project_ids: list[int],
    following_years: bool = False,
    note: str | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Set the projects a Sammel-FinVe finances in one Haushalt year, replacing that
    year's links (requires ``finve.edit``). following_years: the same for every
    later year the FinVe is listed in. Links of archived projects stay as history;
    archived projects cannot be added. An empty list removes the year's links.
    Each changed project gets a changelog entry (``sammel_finve_years``, revertable)
    and a recomputed planning state. note: why (returned with the result).
    Regular FinVes: update_finve_projects."""
    principal = get_principal(ctx)
    require(principal, LINK_PERMISSION)
    wanted = list(dict.fromkeys(project_ids))
    with tool_session(ctx) as db:
        listed = sammel_crud.budget_years(db, finve_id)
        years = [y for y in listed if y > haushalt_year] if following_years else []
        years.insert(0, haushalt_year)
        try:
            changed = sammel_crud.set_year_projects(
                db, finve_id, years, wanted, user=load_user(db, principal)
            )
        except FinveLinkError as exc:
            raise ToolError(str(exc)) from exc
        return {
            "finve_id": finve_id,
            "years": {
                str(y): [_project_ref(p) for p in sammel_crud.year_projects(db, finve_id, y)]
                for y in years
            },
            "changed_project_ids": changed,
            "note": note,
        }


def list_haushalt_unmatched_rows(
    haushalt_year: int | None = None, resolved: bool | None = False, *, ctx: Context
) -> dict[str, Any]:
    """Rows the Haushalt import could not attach to a FinVe (requires
    ``haushalt.import``), newest year first. Default: only open ones. Find the
    FinVe with list_finves (number, name, lfd. Nr.), then
    resolve_haushalt_unmatched_row."""
    principal = get_principal(ctx)
    require(principal, IMPORT_PERMISSION)
    with tool_session(ctx) as db:
        rows = haushalt_crud.list_unmatched_rows(db, resolved=resolved)
        if haushalt_year is not None:
            rows = [r for r in rows if r.haushalt_year == haushalt_year]
        return {
            "rows": [
                {
                    "id": r.id,
                    "haushalt_year": r.haushalt_year,
                    "raw_finve_number": r.raw_finve_number,
                    "raw_name": r.raw_name,
                    "resolved": r.resolved,
                    "resolved_finve_id": r.resolved_finve_id,
                    "resolved_by": r.resolved_by_snapshot,
                }
                for r in rows
            ]
        }


def resolve_haushalt_unmatched_row(
    row_id: int, finve_id: int, *, ctx: Context
) -> dict[str, Any]:
    """Mark an unmatched row as belonging to a FinVe (requires ``haushalt.import``).
    Only records the decision — no budget values are written; if the year's values
    of that FinVe are missing, say so (the year has to be imported again)."""
    principal = get_principal(ctx)
    require(principal, IMPORT_PERMISSION)
    with tool_session(ctx) as db:
        row = haushalt_crud.get_unmatched_row(db, row_id)
        if row is None:
            raise ToolError(f"Offene Zeile {row_id} gibt es nicht.")
        if row.resolved:
            raise ToolError(f"Zeile {row_id} ist schon der FinVe {row.resolved_finve_id} zugeordnet.")
        if db.get(Finve, finve_id) is None:
            raise ToolError(f"FinVe {finve_id} nicht gefunden.")
        haushalt_crud.resolve_unmatched_row(db, row_id, finve_id, load_user(db, principal))
        db.commit()
        has_budget = (
            db.query(Budget.id)
            .filter(Budget.fin_ve == finve_id, Budget.budget_year == row.haushalt_year)
            .first()
            is not None
        )
        return {
            "id": row_id,
            "haushalt_year": row.haushalt_year,
            "resolved_finve_id": finve_id,
            "finve_has_budget_in_year": has_budget,
        }


def register(server: MCPServer) -> None:
    for fn in (
        list_haushalt_years,
        list_haushalt_finves,
        suggest_haushalt_finve_projects,
        list_haushalt_unmatched_rows,
    ):
        server.add_tool(fn, annotations=READ_ONLY)
    server.add_tool(set_sammel_finve_year_projects, annotations=WRITE)
    server.add_tool(resolve_haushalt_unmatched_row, annotations=WRITE)
