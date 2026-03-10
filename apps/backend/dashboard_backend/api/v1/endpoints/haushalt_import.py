from __future__ import annotations

from fastapi import Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from dashboard_backend.core.security import require_roles
from dashboard_backend.crud.haushalt_import import (
    delete_parse_result,
    get_parse_result,
    list_parse_results,
    list_unmatched_rows,
    get_unmatched_row,
    resolve_unmatched_row,
    save_unmatched_rows,
    upsert_budget,
    upsert_budget_titel_entries,
    upsert_finve,
)
from dashboard_backend.database import get_db
from dashboard_backend.models.associations.finve_to_project import FinveToProject
from dashboard_backend.models.haushalt.haushalts_parse_result import HaushaltsParseResult
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.haushalt_import import (
    HaushaltsConfirmRequest,
    HaushaltsConfirmResponse,
    ParseResultPublicSchema,
    UnmatchedBudgetRowResolveRequest,
    UnmatchedBudgetRowSchema,
)
from dashboard_backend.schemas.tasks import TaskLaunchResponse
from dashboard_backend.schemas.users import UserRole
from dashboard_backend.tasks.haushalt import parse_haushalt_pdf

router = AuthRouter()

_require_editor = Depends(require_roles(UserRole.editor, UserRole.admin))


# ---------------------------------------------------------------------------
# POST /parse — start PDF parse task
# ---------------------------------------------------------------------------

@router.post("/parse", response_model=TaskLaunchResponse, dependencies=[_require_editor])
async def start_parse(
    pdf: UploadFile = File(...),
    year: int = Form(...),
    current_user: User = Depends(require_roles(UserRole.editor, UserRole.admin)),
):
    """Upload a Haushalt PDF and start a background parse task.

    Returns the Celery task_id for polling via GET /api/v1/tasks/{task_id}.
    """
    pdf_bytes = await pdf.read()
    user_info = {"id": current_user.id, "username": current_user.username}
    result = parse_haushalt_pdf.delay(pdf_bytes, year, pdf.filename or "upload.pdf", user_info)
    return TaskLaunchResponse(task_id=result.id)


# ---------------------------------------------------------------------------
# GET /parse-result — list all parse runs
# ---------------------------------------------------------------------------

@router.get(
    "/parse-result",
    response_model=list[ParseResultPublicSchema],
    dependencies=[_require_editor],
)
def list_parse_run_results(db: Session = Depends(get_db)):
    """Return metadata for all past parse runs, newest first."""
    return list_parse_results(db)


# ---------------------------------------------------------------------------
# GET /parse-result/{id} — single parse result with full result_json
# ---------------------------------------------------------------------------

@router.get(
    "/parse-result/{parse_result_id}",
    response_model=ParseResultPublicSchema,
    dependencies=[_require_editor],
)
def get_parse_run_result(parse_result_id: int, db: Session = Depends(get_db)):
    record = get_parse_result(db, parse_result_id)
    if not record:
        raise HTTPException(status_code=404, detail="Parse result not found")
    return record


# ---------------------------------------------------------------------------
# DELETE /parse-result/{id} — delete a parse result (and confirmed data)
# ---------------------------------------------------------------------------

@router.delete("/parse-result/{parse_result_id}", status_code=204, dependencies=[_require_editor])
def delete_parse_run_result(
    parse_result_id: int,
    db: Session = Depends(get_db),
):
    """Delete a parse result.

    If the result was already confirmed, all Budget and BudgetTitelEntry rows
    for that haushalt_year are also removed so the year can be re-imported.
    """
    deleted = delete_parse_result(db, parse_result_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Parse result not found")
    db.commit()


# ---------------------------------------------------------------------------
# POST /confirm — import parsed data into the database
# ---------------------------------------------------------------------------

@router.post("/confirm", response_model=HaushaltsConfirmResponse)
def confirm_import(
    body: HaushaltsConfirmRequest,
    current_user: User = Depends(require_roles(UserRole.editor, UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Confirm a parse result and import Finve/Budget data.

    Guard: if the parse result is already confirmed, returns 409 Conflict.
    """
    record: HaushaltsParseResult | None = get_parse_result(db, body.parse_result_id)
    if not record:
        raise HTTPException(status_code=404, detail="Parse result not found")
    if record.confirmed_at is not None:
        raise HTTPException(
            status_code=409,
            detail="This parse result has already been imported. Double-import prevented.",
        )

    from datetime import datetime

    finves_created = finves_updated = budgets_created = budgets_updated = unmatched_saved = 0

    for row in body.rows:
        if row.status == "unmatched":
            continue

        # 1. HaushaltTitel get_or_create handled inside upsert_budget_titel_entries
        # 2. Finve INSERT/UPDATE
        if row.proposed_finve:
            _, created, _ = upsert_finve(db, row.proposed_finve, current_user, record.haushalt_year)
            if created:
                finves_created += 1
            else:
                finves_updated += 1

        # 3. Budget INSERT/UPDATE
        if row.proposed_budget:
            budget, created, _ = upsert_budget(
                db, row.proposed_budget, current_user, record.haushalt_year
            )
            if created:
                budgets_created += 1
            else:
                budgets_updated += 1

            # 4. BudgetTitelEntry INSERT/UPDATE
            if row.proposed_titel_entries:
                upsert_budget_titel_entries(db, budget.id, row.proposed_titel_entries)

        # 5. Sync FinveToProject for new and updated FinVes
        if row.status in ("new", "update") and row.proposed_finve:
            finve_id = row.proposed_finve.id
            is_sammel = row.proposed_finve.is_sammel_finve
            # SV-FinVes track membership per haushalt_year; regular FinVes use NULL (permanent)
            link_year = record.haushalt_year if is_sammel else None

            desired = set(row.project_ids)
            q = db.query(FinveToProject).filter(FinveToProject.finve_id == finve_id)
            if is_sammel:
                q = q.filter(FinveToProject.haushalt_year == link_year)
            else:
                q = q.filter(FinveToProject.haushalt_year.is_(None))
            current = {r.project_id for r in q.all()}

            for project_id in desired - current:
                db.add(FinveToProject(finve_id=finve_id, project_id=project_id, haushalt_year=link_year))
            for project_id in current - desired:
                del_q = db.query(FinveToProject).filter(
                    FinveToProject.finve_id == finve_id,
                    FinveToProject.project_id == project_id,
                )
                if is_sammel:
                    del_q = del_q.filter(FinveToProject.haushalt_year == link_year)
                else:
                    del_q = del_q.filter(FinveToProject.haushalt_year.is_(None))
                del_q.delete(synchronize_session=False)

    # 6. Save unmatched rows if requested
    if body.unmatched_action == "save":
        unmatched_rows_data = [
            {"raw_finve_number": str(row.finve_number), "raw_name": row.name}
            for row in body.rows
            if row.status == "unmatched"
        ]
        if unmatched_rows_data:
            unmatched_saved = save_unmatched_rows(db, unmatched_rows_data, record.haushalt_year)

    # 7. Mark parse result as confirmed
    record.confirmed_at = datetime.utcnow()
    record.confirmed_by_snapshot = current_user.username

    db.commit()

    return HaushaltsConfirmResponse(
        finves_created=finves_created,
        finves_updated=finves_updated,
        budgets_created=budgets_created,
        budgets_updated=budgets_updated,
        unmatched_saved=unmatched_saved,
    )


# ---------------------------------------------------------------------------
# GET /unmatched — list unmatched rows
# ---------------------------------------------------------------------------

@router.get(
    "/unmatched",
    response_model=list[UnmatchedBudgetRowSchema],
    dependencies=[_require_editor],
)
def list_unmatched(resolved: bool | None = None, db: Session = Depends(get_db)):
    """Return unmatched budget rows. Pass ?resolved=false to see only open items."""
    return list_unmatched_rows(db, resolved=resolved)


# ---------------------------------------------------------------------------
# PATCH /unmatched/{id} — resolve an unmatched row
# ---------------------------------------------------------------------------

@router.patch("/unmatched/{row_id}", response_model=UnmatchedBudgetRowSchema)
def patch_unmatched(
    row_id: int,
    body: UnmatchedBudgetRowResolveRequest,
    current_user: User = Depends(require_roles(UserRole.editor, UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Assign a Finve to an unmatched row. Triggers Budget + BudgetTitelEntry creation."""
    row = get_unmatched_row(db, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Unmatched row not found")
    if row.resolved:
        raise HTTPException(status_code=409, detail="Row is already resolved")

    resolved = resolve_unmatched_row(db, row_id, body.finve_id, current_user)
    if not resolved:
        raise HTTPException(status_code=404, detail="Unmatched row not found")

    db.commit()
    db.refresh(resolved)
    return resolved
