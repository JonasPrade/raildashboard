from sqlalchemy.orm import Session, joinedload

from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.haushalt.budget_titel_entry import BudgetTitelEntry
from dashboard_backend.models.projects.budget import Budget
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.projects.project import Project
from dashboard_backend.schemas.projects.project_schema import (
    BudgetSummarySchema,
    FinveListItemSchema,
    ProjectRefSchema,
    TitelEntrySchema,
)


def list_finves(db: Session) -> list[FinveListItemSchema]:
    """Return all FinVes with linked project refs and full budget history."""
    finves = (
        db.query(Finve)
        .options(
            joinedload(Finve.budgets)
            .joinedload(Budget.titel_entries)
            .joinedload(BudgetTitelEntry.titel)
        )
        .order_by(Finve.id)
        .all()
    )
    if not finves:
        return []

    finve_ids = [f.id for f in finves]

    # Load all (finve_id, project_id, project_name) rows; deduplicate because
    # SV-FinVes may have multiple rows per (finve_id, project_id) across years.
    raw = (
        db.query(FinveToProject.finve_id, Project.id, Project.name)
        .join(Project, Project.id == FinveToProject.project_id)
        .filter(FinveToProject.finve_id.in_(finve_ids))
        .all()
    )

    seen: set[tuple[int, int]] = set()
    projects_by_finve: dict[int, list[ProjectRefSchema]] = {}
    for finve_id, project_id, project_name in raw:
        key = (finve_id, project_id)
        if key not in seen:
            seen.add(key)
            projects_by_finve.setdefault(finve_id, []).append(
                ProjectRefSchema(id=project_id, name=project_name or "")
            )

    result = []
    for f in finves:
        linked = projects_by_finve.get(f.id, [])
        budgets_sorted = sorted(f.budgets, key=lambda b: b.budget_year)
        budget_schemas = []
        for b in budgets_sorted:
            titel_schemas = [TitelEntrySchema.from_entry(e) for e in b.titel_entries]
            budget_schemas.append(
                BudgetSummarySchema(
                    budget_year=b.budget_year,
                    lfd_nr=b.lfd_nr,
                    bedarfsplan_number=b.bedarfsplan_number,
                    cost_estimate_original=b.cost_estimate_original,
                    cost_estimate_last_year=b.cost_estimate_last_year,
                    cost_estimate_actual=b.cost_estimate_actual,
                    delta_previous_year=b.delta_previous_year,
                    delta_previous_year_relativ=b.delta_previous_year_relativ,
                    spent_two_years_previous=b.spent_two_years_previous,
                    allowed_previous_year=b.allowed_previous_year,
                    spending_residues=b.spending_residues,
                    year_planned=b.year_planned,
                    next_years=b.next_years,
                    titel_entries=titel_schemas,
                )
            )
        result.append(
            FinveListItemSchema(
                id=f.id,
                name=f.name,
                starting_year=f.starting_year,
                cost_estimate_original=f.cost_estimate_original,
                is_sammel_finve=f.is_sammel_finve,
                temporary_finve_number=f.temporary_finve_number,
                project_count=len(linked),
                project_names=[p.name for p in linked],
                projects=linked,
                budgets=budget_schemas,
            )
        )
    return result
