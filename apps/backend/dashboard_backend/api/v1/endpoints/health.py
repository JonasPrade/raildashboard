import logging
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from dashboard_backend.core.config import settings
from dashboard_backend.database import engine, get_db
from dashboard_backend.models.projects.project import Project

logger = logging.getLogger(__name__)

router = APIRouter()

# Mounted at the app root (/healthz), not under /api/v1: it is the deploy gate,
# not part of the API. See main.py.
readiness_router = APIRouter()

# Placeholder values shipped in .env.prod.example. A server still carrying one
# of them is not configured, whatever the process thinks.
_PLACEHOLDER_SECRETS = {"", "change-me-generate-a-random-32-byte-hex-string"}


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness + DB reachability. Kept for manual checks; the deploy gate is /healthz."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"database unavailable: {exc.__class__.__name__}",
        )
    return {"status": "ok"}


def _writable(directory: str) -> bool:
    try:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path, prefix=".healthz-"):
            pass
        return True
    except OSError:
        return False


@readiness_router.get("/healthz", include_in_schema=False)
def healthz(db: Session = Depends(get_db)):
    """Readiness, not just liveness: 200 only when the app can actually serve.

    The container healthcheck points here, ``deploy/prod.sh`` waits on it and
    rolls back otherwise, and ``deploy.yml`` calls it from outside through the
    host proxy (DEPLOY.md).
    """
    problems: list[str] = []
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("healthz: database unreachable")
        problems.append("database")
    else:
        # Load one full Project row: every mapped column must exist. SELECT 1
        # stays green when the schema and the code disagree, e.g. after a
        # rollback past a migration that dropped a column.
        try:
            db.execute(select(Project).limit(1)).first()
        except SQLAlchemyError:
            logger.exception("healthz: schema does not match the code")
            db.rollback()
            problems.append("schema")
    if settings.session_secret_key in _PLACEHOLDER_SECRETS:
        problems.append("session_secret_key")
    for name, directory in (
        ("upload_dir", settings.upload_dir),
        ("import_staging_dir", settings.import_staging_dir),
    ):
        if not _writable(directory):
            logger.error("healthz: %s %s is not writable (uid %s)", name, directory, os.getuid())
            problems.append(name)
    if problems:
        return JSONResponse({"status": "error", "problems": problems}, status_code=503)
    return {"status": "ok"}
