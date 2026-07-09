"""Celery task for the Fulda-Runde importer (#75).

OCR + LLM extraction can take minutes for a large Kleine-Anfrage PDF. The
parse endpoint used to run this inline in an async handler, which blocked the
event loop for the whole duration; it now dispatches this task and the
frontend polls ``GET /api/v1/tasks/{task_id}``.
"""
from __future__ import annotations

import logging

from dashboard_backend.celery_app import celery_app
from dashboard_backend.crud import fulda as fulda_crud
from dashboard_backend.database import Session

logger = logging.getLogger(__name__)


class _UserProxy:
    """Minimal user-like object rebuilt from the serialized user_info dict."""

    def __init__(self, info: dict):
        self.id = info.get("id")
        self.username = info.get("username")


@celery_app.task(bind=True)
def parse_fulda_pdf(
    self,
    pdf_bytes: bytes,
    year: int,
    pdf_filename: str,
    user_info: dict,
) -> dict:
    """OCR + LLM extract a Fulda PDF into draft announcement rows.

    Returns the summary dict ``{ocr_status, created, source_label}``.
    """
    logger.info(
        "parse_fulda_pdf started: file=%s year=%d user=%s",
        pdf_filename,
        year,
        user_info.get("username") if user_info else "unknown",
    )
    db = Session()
    try:
        summary = fulda_crud.parse_and_store(
            db,
            pdf_bytes=pdf_bytes,
            year=year,
            user=_UserProxy(user_info) if user_info else None,
        )
        logger.info("parse_fulda_pdf finished: created=%d", summary["created"])
        return summary
    except Exception as exc:
        logger.exception("parse_fulda_pdf failed: %s", exc)
        db.rollback()
        raise
    finally:
        db.close()
