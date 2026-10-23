"""FinVe (Finanzierungsvereinbarung) tools: free search across all FinVes and
editing their project links.

``list_project_finves`` only reaches FinVes already linked to a project; these
tools find FinVes by number, name or Bedarfsplan number — including those not
(yet) assigned to any project.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy import exists, or_
from sqlalchemy.orm import selectinload

from dashboard_backend.crud.finve_links import (
    FinveLinkError,
    permanent_projects,
    update_finve_projects as update_finve_projects_crud,
)
from dashboard_backend.crud.finves import finve_with_budgets, get_finve_with_budgets
from dashboard_backend.mcp.context import get_principal, load_user, require, tool_session
from dashboard_backend.mcp.tools.projects import MAX_LIMIT, READ_ONLY, WRITE
from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.projects.budget import Budget
from dashboard_backend.models.projects.finve import Finve


def _project_refs(finve: Finve) -> list[dict[str, Any]]:
    # SV-FinVes carry one association row per Haushalt year — deduplicate.
    refs = {p.id: p.name for p in finve.projects}
    return [{"id": pid, "name": name} for pid, name in sorted(refs.items())]


def _finve_summary(finve: Finve) -> dict[str, Any]:
    budgets = sorted(finve.budgets, key=lambda b: b.budget_year)
    latest = budgets[-1] if budgets else None
    return {
        "id": finve.id,
        "name": finve.name,
        "temporary_finve_number": bool(finve.temporary_finve_number),
        "finve_key": finve.finve_key,
        "is_sammel_finve": finve.is_sammel_finve,
        "starting_year": finve.starting_year,
        "cost_estimate_original": finve.cost_estimate_original,
        "bedarfsplan_numbers": sorted({b.bedarfsplan_number for b in budgets if b.bedarfsplan_number}),
        "budget_years": [b.budget_year for b in budgets],
        "latest_cost_estimate_actual": latest.cost_estimate_actual if latest else None,
        "projects": _project_refs(finve),
    }


def list_finves(
    search: str | None = None,
    bedarfsplan_number: str | None = None,
    budget_year: int | None = None,
    is_sammel_finve: bool | None = None,
    has_project: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Search all financing agreements (FinVe) — also those not linked to any project.

    - search: FinVe number (exact, if numeric) or a case-insensitive substring of
      the name, the Bedarfsplan number, the lfd. Nr. or the FinVe key
      (e.g. "ABS 38", "München", "2345")
    - bedarfsplan_number: case-insensitive substring of the Bedarfsplan number
      in any budget year (e.g. "B0080")
    - budget_year: only FinVes listed in the budget report of this year
    - is_sammel_finve: only (or no) Sammel-FinVes
    - has_project: true = linked to at least one project, false = unassigned
    Returns ``total`` plus one page sorted by FinVe number; each entry lists its
    Bedarfsplan numbers, budget years, latest cost estimate (T€) and linked
    projects. Use get_finve for the full budget history.
    """
    get_principal(ctx)
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    with tool_session(ctx) as db:
        query = db.query(Finve)
        term = (search or "").strip()
        if term:
            pattern = f"%{term}%"
            conditions = [
                Finve.name.ilike(pattern),
                Finve.finve_key.ilike(pattern),
                exists().where(
                    Budget.fin_ve == Finve.id,
                    or_(Budget.bedarfsplan_number.ilike(pattern), Budget.lfd_nr.ilike(pattern)),
                ),
            ]
            if term.isdigit():
                conditions.append(Finve.id == int(term))
            query = query.filter(or_(*conditions))
        if bedarfsplan_number and bedarfsplan_number.strip():
            query = query.filter(
                exists().where(
                    Budget.fin_ve == Finve.id,
                    Budget.bedarfsplan_number.ilike(f"%{bedarfsplan_number.strip()}%"),
                )
            )
        if budget_year is not None:
            query = query.filter(
                exists().where(Budget.fin_ve == Finve.id, Budget.budget_year == budget_year)
            )
        if is_sammel_finve is not None:
            query = query.filter(Finve.is_sammel_finve.is_(is_sammel_finve))
        if has_project is not None:
            linked = exists().where(FinveToProject.finve_id == Finve.id)
            query = query.filter(linked if has_project else ~linked)
        total = query.count()
        finves = (
            query.options(selectinload(Finve.budgets), selectinload(Finve.projects))
            .order_by(Finve.id)
            .offset(offset)
            .limit(limit)
            .all()
        )
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "finves": [_finve_summary(f) for f in finves],
        }


def get_finve(finve_id: int, *, ctx: Context) -> dict[str, Any]:
    """One FinVe by number with its linked projects and full budget history per
    budget year, including the per-Haushaltstitel breakdown. Amounts in T€."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        finve = get_finve_with_budgets(db, finve_id)
        if finve is None:
            raise ToolError(f"FinVe {finve_id} nicht gefunden.")
        data = finve_with_budgets(finve).model_dump(mode="json")
        data["temporary_finve_number"] = bool(finve.temporary_finve_number)
        data["finve_key"] = finve.finve_key
        data["projects"] = _project_refs(finve)
        return data


def update_finve_projects(
    finve_id: int,
    add_project_ids: list[int] | None = None,
    remove_project_ids: list[int] | None = None,
    note: str | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Add projects to and/or remove projects from a FinVe (requires
    ``finve.edit``), also for FinVes that are already assigned; other links stay.
    Only permanent links change — the year links of a Sammel-FinVe come from the
    Haushalt import and stay. Each changed project gets a changelog entry
    (revertable in the UI) and a recomputed planning state: a FinVe sets a lower
    bound there, so removing a wrong link also removes its observation.
    note: why the link was wrong or added (returned with the result).
    Returns the FinVe's permanent projects afterwards and the changed project ids."""
    principal = get_principal(ctx)
    require(principal, "finve.edit")
    add = list(dict.fromkeys(add_project_ids or []))
    remove = list(dict.fromkeys(remove_project_ids or []))
    if not add and not remove:
        raise ToolError("Keine Projekte übergeben (add_project_ids oder remove_project_ids).")
    with tool_session(ctx) as db:
        try:
            changed = update_finve_projects_crud(
                db,
                finve_id,
                add_project_ids=add,
                remove_project_ids=remove,
                user=load_user(db, principal),
            )
        except FinveLinkError as exc:
            raise ToolError(str(exc)) from exc
        return {
            "finve_id": finve_id,
            "projects": [{"id": p.id, "name": p.name} for p in permanent_projects(db, finve_id)],
            "changed_project_ids": changed,
            "note": note,
        }


def register(server: MCPServer) -> None:
    server.add_tool(list_finves, annotations=READ_ONLY)
    server.add_tool(get_finve, annotations=READ_ONLY)
    server.add_tool(update_finve_projects, annotations=WRITE)
