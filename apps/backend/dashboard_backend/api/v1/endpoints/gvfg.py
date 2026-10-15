"""GVFG-Bundesprogramm: import (editors) and public reads.

See docs/features/feature-gvfg-import.md.
"""

from __future__ import annotations

from fastapi import Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from dashboard_backend.api.deps import launch_with_staged_pdf, read_upload_within_limit
from dashboard_backend.core.security import require_permission
from dashboard_backend.crud import gvfg as gvfg_crud
from dashboard_backend.database import get_db
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.gvfg import (
    GvfgConfirmRequest,
    GvfgConfirmResponse,
    GvfgEntrySchema,
    GvfgParseResultDetail,
    GvfgParseResultSummary,
    GvfgProgramSchema,
    GvfgProjectEntrySchema,
)
from dashboard_backend.schemas.tasks import TaskLaunchResponse
from dashboard_backend.tasks.gvfg import parse_gvfg_pdf_task

import_router = AuthRouter()
router = AuthRouter()

_require_import = Depends(require_permission("gvfg.import"))


# --- Import (gvfg.import) ----------------------------------------------------


@import_router.post("/parse", response_model=TaskLaunchResponse)
async def start_parse(
    pdf: UploadFile = File(...),
    current_user: User = Depends(require_permission("gvfg.import")),
):
    """Upload a GVFG programme PDF (main part or annex) and start the parse task.
    Poll GET /api/v1/tasks/{task_id}; the result carries the parse_result_id."""
    if pdf.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Nur PDF-Dateien werden angenommen.")
    pdf_bytes = await read_upload_within_limit(pdf)
    user_info = {"id": current_user.id, "username": current_user.username}
    result = launch_with_staged_pdf(
        parse_gvfg_pdf_task, pdf_bytes, pdf.filename or "upload.pdf", user_info
    )
    return TaskLaunchResponse(task_id=result.id)


@import_router.get(
    "/parse-result", response_model=list[GvfgParseResultSummary], dependencies=[_require_import]
)
def list_parse_results(db: Session = Depends(get_db)):
    return gvfg_crud.list_parse_results(db)


@import_router.get(
    "/parse-result/{parse_result_id}",
    response_model=GvfgParseResultDetail,
    dependencies=[_require_import],
)
def get_parse_result(parse_result_id: int, db: Session = Depends(get_db)):
    record = gvfg_crud.get_parse_result(db, parse_result_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Parse result not found")
    return record


@import_router.delete(
    "/parse-result/{parse_result_id}", status_code=204, dependencies=[_require_import]
)
def delete_parse_result(parse_result_id: int, db: Session = Depends(get_db)):
    """Delete a parse run. Data already confirmed into an edition stays."""
    record = gvfg_crud.get_parse_result(db, parse_result_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Parse result not found")
    db.delete(record)
    db.commit()


@import_router.post(
    "/parse-result/{parse_result_id}/confirm", response_model=GvfgConfirmResponse
)
def confirm_parse_result(
    parse_result_id: int,
    body: GvfgConfirmRequest,
    current_user: User = Depends(require_permission("gvfg.import")),
    db: Session = Depends(get_db),
):
    """Write the reviewed result into its edition (replaces the parts it contains)."""
    record = gvfg_crud.get_parse_result(db, parse_result_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Parse result not found")
    try:
        return gvfg_crud.confirm_parse_result(
            db,
            record,
            assignments=body.assignments,
            create_projects=body.create_projects,
            user=current_user,
        )
    except gvfg_crud.GvfgConfirmError as exc:
        # Raised by the checks before anything is written.
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- Public reads -------------------------------------------------------------


@router.get("/programs", response_model=list[GvfgProgramSchema])
def list_programs(db: Session = Depends(get_db)):
    """All imported editions, newest first."""
    return gvfg_crud.list_programs(db)


@router.get("/programs/{program_id}/entries", response_model=list[GvfgEntrySchema])
def list_program_entries(program_id: int, db: Session = Depends(get_db)):
    """All Vorhaben of an edition with their amount lines and linked projects."""
    if gvfg_crud.get_program(db, program_id) is None:
        raise HTTPException(status_code=404, detail="Program not found")
    return gvfg_crud.program_entries(db, program_id)


@router.get("/projects/{project_id}/entries", response_model=list[GvfgProjectEntrySchema])
def list_project_entries(
    project_id: int, with_subprojects: bool = False, db: Session = Depends(get_db)
):
    """GVFG entries of a project across all editions, newest first.
    ``with_subprojects`` adds the entries of its direct subprojects."""
    return gvfg_crud.project_entries(db, project_id, with_subprojects)
