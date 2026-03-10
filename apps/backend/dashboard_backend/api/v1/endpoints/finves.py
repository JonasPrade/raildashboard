from fastapi import Depends
from sqlalchemy.orm import Session

from dashboard_backend.crud.finves import list_finves
from dashboard_backend.database import get_db
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.projects.project_schema import FinveListItemSchema

router = AuthRouter()


@router.get("/", response_model=list[FinveListItemSchema])
def get_finves(db: Session = Depends(get_db)):
    """Return all Finanzierungsvereinbarungen with linked project info."""
    return list_finves(db)
