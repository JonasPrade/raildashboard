"""GVFG-Bundesprogramm importer: PDF → staged parse result with project suggestions.

See docs/features/feature-gvfg-import.md and services/gvfg_parser.py.
"""

from __future__ import annotations

import io
import logging

from celery import Task

from dashboard_backend.celery_app import celery_app
from dashboard_backend.crud.gvfg import build_suggestions, save_parse_result
from dashboard_backend.database import Session
from dashboard_backend.services.gvfg_parser import parse_gvfg_pdf
from dashboard_backend.tasks.haushalt import report_step
from dashboard_backend.utils.file_storage import consume_staged_import

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def parse_gvfg_pdf_task(self: Task, staged_pdf: str, pdf_filename: str, user_info: dict) -> dict:
    """Parse a staged GVFG PDF; returns {"parse_result_id": int}."""
    with consume_staged_import(staged_pdf) as pdf_bytes:
        return run_gvfg_parse(self, pdf_bytes, pdf_filename, user_info)


def run_gvfg_parse(task: Task | None, pdf_bytes: bytes, pdf_filename: str, user_info: dict) -> dict:
    db = Session()
    try:
        report_step(task, "parse", "Tabellen werden gelesen…")
        result = parse_gvfg_pdf(io.BytesIO(pdf_bytes))
        report_step(task, "match", f"{len(result.entries)} Vorhaben — Projekte werden zugeordnet…")
        result_json = result.to_json()
        result_json["suggestions"] = build_suggestions(db, result_json["entries"])
        record = save_parse_result(
            db,
            filename=pdf_filename,
            result_json=result_json,
            status="SUCCESS",
            error=None,
            user_info=user_info,
        )
        db.commit()
        logger.info("parse_gvfg_pdf finished: parse_result_id=%d", record.id)
        return {"parse_result_id": record.id}
    except Exception as exc:
        logger.exception("parse_gvfg_pdf failed: %s", exc)
        db.rollback()
        try:
            save_parse_result(
                db, filename=pdf_filename, result_json=None, status="FAILURE",
                error=str(exc), user_info=user_info,
            )
            db.commit()
        except Exception:
            db.rollback()
        raise
    finally:
        db.close()
