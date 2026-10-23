from __future__ import annotations

from fastapi import Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from dashboard_backend.api.deps import launch_with_staged_pdf, read_upload_within_limit
from dashboard_backend.core.security import require_permission
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
from dashboard_backend.tasks.haushalt import parse_haushalt_pdf

router = AuthRouter()

_require_editor = Depends(require_permission("haushalt.import"))


# ---------------------------------------------------------------------------
# POST /parse — start PDF parse task
# ---------------------------------------------------------------------------

@router.post("/parse", response_model=TaskLaunchResponse)
async def start_parse(
    pdf: UploadFile = File(...),
    year: int = Form(...),
    current_user: User = Depends(require_permission("haushalt.import")),
):
    """Upload a Haushalt PDF and start a background parse task.

    Returns the Celery task_id for polling via GET /api/v1/tasks/{task_id}.
    """
    if pdf.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    pdf_bytes = await read_upload_within_limit(pdf)
    user_info = {"id": current_user.id, "username": current_user.username}
    result = launch_with_staged_pdf(
        parse_haushalt_pdf, pdf_bytes, year, pdf.filename or "upload.pdf", user_info,
    )
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

def permanent_link_delta(
    parsed_row: dict | None, submitted: list[int]
) -> tuple[set[int], set[int]]:
    """Projects to add/remove on a regular FinVe's permanent links at confirm.

    The baseline is the list the review started from: the links at parse time.
    The parser only suggests projects for a FinVe it did not know yet, so a row
    with suggestions had no links (baseline empty). Without a stored row only
    additions are applied. Links edited between parse and confirm stay as they
    are unless the reviewer changed the same project.
    """
    wanted = set(submitted)
    if parsed_row is None:
        return wanted, set()
    if parsed_row.get("suggested_project_ids"):
        baseline: set[int] = set()
    else:
        baseline = set(parsed_row.get("project_ids") or [])
    return wanted - baseline, baseline - wanted


def _apply_permanent_delta(db: Session, finve_id: int, add: set[int], remove: set[int]) -> None:
    current = {
        pid
        for (pid,) in db.query(FinveToProject.project_id).filter(
            FinveToProject.finve_id == finve_id, FinveToProject.haushalt_year.is_(None)
        )
    }
    for project_id in add - current:
        db.add(FinveToProject(finve_id=finve_id, project_id=project_id, haushalt_year=None))
    if remove & current:
        db.query(FinveToProject).filter(
            FinveToProject.finve_id == finve_id,
            FinveToProject.project_id.in_(remove & current),
            FinveToProject.haushalt_year.is_(None),
        ).delete(synchronize_session=False)


def _sync_sammel_links(db: Session, finve_id: int, year: int, desired: set[int]) -> None:
    rows = db.query(FinveToProject).filter(
        FinveToProject.finve_id == finve_id, FinveToProject.haushalt_year == year
    )
    current = {r.project_id for r in rows}
    for project_id in desired - current:
        db.add(FinveToProject(finve_id=finve_id, project_id=project_id, haushalt_year=year))
    if current - desired:
        db.query(FinveToProject).filter(
            FinveToProject.finve_id == finve_id,
            FinveToProject.project_id.in_(current - desired),
            FinveToProject.haushalt_year == year,
        ).delete(synchronize_session=False)


@router.post("/confirm", response_model=HaushaltsConfirmResponse)
def confirm_import(
    body: HaushaltsConfirmRequest,
    current_user: User = Depends(require_permission("haushalt.import")),
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
    parsed_rows = {
        r.get("row_key"): r for r in ((record.result_json or {}).get("rows") or []) if isinstance(r, dict)
    }

    for row in body.rows:
        if row.status == "unmatched":
            continue

        # 1. HaushaltTitel get_or_create handled inside upsert_budget_titel_entries
        # 2. Finve INSERT/UPDATE
        finve = None
        if row.proposed_finve:
            finve, created, _ = upsert_finve(db, row.proposed_finve, current_user, record.haushalt_year)
            if created:
                finves_created += 1
            else:
                finves_updated += 1

        # 3. Budget INSERT/UPDATE
        if row.proposed_budget:
            # A measure without a printed FinVe number only learns its id here,
            # from the Finve row just created or matched on its key.
            if row.proposed_budget.fin_ve is None:
                if finve is None:
                    continue
                row.proposed_budget.fin_ve = finve.id
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
        if row.status in ("new", "update") and row.proposed_finve and finve is not None:
            finve_id = finve.id
            if row.proposed_finve.is_sammel_finve:
                # SV-FinVes track membership per haushalt_year: set-sync this year's links.
                _sync_sammel_links(db, finve_id, record.haushalt_year, set(row.project_ids))
            else:
                # Permanent links may have been edited since the parse: apply only
                # the reviewer's changes against the parse-time list.
                add, remove = permanent_link_delta(
                    parsed_rows.get(row.row_key), row.project_ids
                )
                _apply_permanent_delta(db, finve_id, add, remove)

    # 6. Save unmatched rows if requested
    if body.unmatched_action == "save":
        unmatched_rows_data = [
            {
                "raw_finve_number": str(row.finve_number or row.finve_key or row.row_key),
                "raw_name": row.name,
            }
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
    current_user: User = Depends(require_permission("haushalt.import")),
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
