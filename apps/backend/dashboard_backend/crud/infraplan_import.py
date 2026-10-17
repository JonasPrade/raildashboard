"""Persistence of Infraplan parse drafts (stage 1 of the Infraplan import)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from dashboard_backend.models.infraplan import InfraplanParseResult
from dashboard_backend.schemas.infraplan_import import (
    InfraplanKpiPage,
    InfraplanParseOutput,
    InfraplanWarning,
)

if TYPE_CHECKING:
    from dashboard_backend.models.users import User


def create_parse_result(
    db: Session, year: int, file_name: str, user: "User | None"
) -> InfraplanParseResult:
    record = InfraplanParseResult(
        year=year,
        file_name=file_name,
        status="PENDING",
        created_by_user_id=user.id if user else None,
        username_snapshot=user.username if user else None,
    )
    db.add(record)
    db.flush()
    return record


def get_parse_result(db: Session, parse_result_id: int) -> InfraplanParseResult | None:
    return db.get(InfraplanParseResult, parse_result_id)


def list_parse_results(db: Session) -> list[InfraplanParseResult]:
    """All drafts, newest first."""
    return (
        db.query(InfraplanParseResult)
        .order_by(InfraplanParseResult.created_at.desc(), InfraplanParseResult.id.desc())
        .all()
    )


def mark_parse_pending(record: InfraplanParseResult, task_id: str | None) -> None:
    record.status = "PENDING"
    record.task_id = task_id
    record.error_message = None


def mark_parse_running(db: Session, record: InfraplanParseResult) -> None:
    record.status = "RUNNING"
    record.error_message = None
    db.flush()


def save_parse_output(
    db: Session,
    record: InfraplanParseResult,
    output: InfraplanParseOutput,
    warnings: list[InfraplanWarning],
    kpi_pages: list[InfraplanKpiPage],
) -> None:
    record.status = "SUCCESS"
    record.error_message = None
    record.result_json = output.model_dump(mode="json")
    record.warnings_json = [w.model_dump(mode="json") for w in warnings]
    record.kpi_pages_json = [p.model_dump(mode="json") for p in kpi_pages]
    db.flush()


def mark_parse_failed(db: Session, record: InfraplanParseResult, error: str) -> None:
    record.status = "FAILURE"
    record.error_message = error
    db.flush()


def delete_parse_result(db: Session, record: InfraplanParseResult) -> str | None:
    """Delete a draft; returns the stored PDF name for the caller to remove
    once the transaction has committed."""
    pdf_path = record.pdf_path
    db.delete(record)
    db.flush()
    return pdf_path


def row_count(record: InfraplanParseResult) -> int | None:
    if not record.result_json:
        return None
    return len(record.result_json.get("rows", []))
