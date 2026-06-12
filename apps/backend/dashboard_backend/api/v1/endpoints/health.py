from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from dashboard_backend.database import engine

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness + DB-readiness probe — used by the docker-compose healthcheck."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"database unavailable: {exc.__class__.__name__}",
        )
    return {"status": "ok"}
