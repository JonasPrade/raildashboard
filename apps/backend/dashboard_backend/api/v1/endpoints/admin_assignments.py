from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from dashboard_backend.core.security import require_roles
from dashboard_backend.crud.admin_assignments import (
    assign_finve_to_projects,
    assign_vib_entry_to_projects,
    get_finve,
    get_vib_entry,
    list_unassigned_finves,
    list_unassigned_vib_entries,
)
from dashboard_backend.database import get_db
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.admin_assignments import (
    AssignProjectsInput,
    UnassignedFinveSchema,
    UnassignedVibEntrySchema,
)
from dashboard_backend.schemas.users import UserRole

router = AuthRouter()

_require_editor = Depends(require_roles(UserRole.editor, UserRole.admin))


@router.get("/unassigned-finves", response_model=list[UnassignedFinveSchema])
def get_unassigned_finves(
    db: Session = Depends(get_db),
    _current_user: User = _require_editor,
) -> list[UnassignedFinveSchema]:
    return list_unassigned_finves(db)


@router.get("/unassigned-vib-entries", response_model=list[UnassignedVibEntrySchema])
def get_unassigned_vib_entries(
    db: Session = Depends(get_db),
    _current_user: User = _require_editor,
) -> list[UnassignedVibEntrySchema]:
    return list_unassigned_vib_entries(db)


@router.patch("/unassigned-finves/{finve_id}/assign", response_model=None, status_code=204)
def assign_finve(
    finve_id: int,
    body: AssignProjectsInput,
    db: Session = Depends(get_db),
    _current_user: User = _require_editor,
) -> None:
    finve = get_finve(db, finve_id)
    if not finve:
        raise HTTPException(status_code=404, detail="FinVe not found")
    if not body.project_ids:
        raise HTTPException(status_code=422, detail="project_ids must not be empty")
    assign_finve_to_projects(db, finve_id, body.project_ids)
    db.commit()


@router.patch("/unassigned-vib-entries/{entry_id}/assign", response_model=None, status_code=204)
def assign_vib_entry(
    entry_id: int,
    body: AssignProjectsInput,
    db: Session = Depends(get_db),
    _current_user: User = _require_editor,
) -> None:
    entry = get_vib_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="VIB entry not found")
    if not body.project_ids:
        raise HTTPException(status_code=422, detail="project_ids must not be empty")
    assign_vib_entry_to_projects(db, entry_id, body.project_ids)
    db.commit()
