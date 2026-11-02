"""„Dauerhaft ignorieren“ for open assignments
(feature-unassigned-assignments.md).

The four ``unassigned_*`` lists filter with :func:`dismissed_ids`; the
endpoints in ``admin_assignments`` set, list and lift a dismissal here.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from dashboard_backend.models.assignment_dismissal import (
    KIND_FINVE,
    KIND_GVFG,
    KIND_INFRAPLAN,
    KIND_VIB,
    AssignmentDismissal,
)
from dashboard_backend.models.gvfg import GvfgEntry, GvfgProgram
from dashboard_backend.models.infraplan import InfraplanEntry, InfraplanReport
from dashboard_backend.models.projects.finve import Finve
from dashboard_backend.models.users import User
from dashboard_backend.models.vib.vib_entry import VibEntry
from dashboard_backend.models.vib.vib_report import VibReport


class DismissalNotFound(Exception):
    """The record to ignore does not exist."""


_MODELS = {
    KIND_FINVE: Finve,
    KIND_VIB: VibEntry,
    KIND_GVFG: GvfgEntry,
    KIND_INFRAPLAN: InfraplanEntry,
}

_SECTION_SHORT = {
    "BP_A": "BP Teil A",
    "BP_B": "BP Teil B",
    "BP_C": "BP Teil C",
    "BP_D": "BP Teil D",
    "GVFG_A": "GVFG Kat. A",
    "GVFG_C": "GVFG Kat. C",
    "INVKG": "InvKG",
}


def dismissed_ids(kind: str):
    """Subquery of the ignored record ids of one kind, for ``.not_in(...)``."""
    return select(AssignmentDismissal.entry_id).where(AssignmentDismissal.kind == kind)


def dismiss(
    db: Session, kind: str, entry_id: int, *, note: str | None, user: User | None
) -> AssignmentDismissal:
    """Hide a record from „Offene Zuordnungen“. Idempotent: a second call only
    updates the note. Commits."""
    if db.get(_MODELS[kind], entry_id) is None:
        raise DismissalNotFound(f"{kind} {entry_id} not found")
    row = (
        db.query(AssignmentDismissal)
        .filter(AssignmentDismissal.kind == kind, AssignmentDismissal.entry_id == entry_id)
        .one_or_none()
    )
    if row is None:
        row = AssignmentDismissal(
            kind=kind,
            entry_id=entry_id,
            note=note,
            dismissed_by_user_id=user.id if user is not None else None,
        )
        db.add(row)
    elif note is not None:
        row.note = note
    db.commit()
    db.refresh(row)
    return row


def restore(db: Session, kind: str, entry_id: int) -> bool:
    """Lift a dismissal; the record is open again. Returns whether one existed.
    Commits."""
    deleted = (
        db.query(AssignmentDismissal)
        .filter(AssignmentDismissal.kind == kind, AssignmentDismissal.entry_id == entry_id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return bool(deleted)


def _labels(db: Session, kind: str, ids: list[int]) -> dict[int, tuple[str, str | None]]:
    """``id → (label, detail)`` for the ignored list."""
    if not ids:
        return {}
    if kind == KIND_FINVE:
        return {
            f.id: (f.name or f"FinVe {f.id}", f"FinVe {f.id}" + (" · SV" if f.is_sammel_finve else ""))
            for f in db.query(Finve).filter(Finve.id.in_(ids))
        }
    if kind == KIND_VIB:
        rows = (
            db.query(VibEntry, VibReport.year)
            .join(VibReport, VibReport.id == VibEntry.vib_report_id)
            .filter(VibEntry.id.in_(ids))
        )
        return {
            e.id: (e.vib_name_raw, f"VIB {year}" + (f" · {e.vib_section}" if e.vib_section else ""))
            for e, year in rows
        }
    if kind == KIND_GVFG:
        rows = (
            db.query(GvfgEntry, GvfgProgram.year_from)
            .join(GvfgProgram, GvfgProgram.id == GvfgEntry.program_id)
            .filter(GvfgEntry.id.in_(ids))
        )
        return {
            e.id: (e.name or e.key, f"GVFG {year} · {e.key} · {e.land}") for e, year in rows
        }
    rows = (
        db.query(InfraplanEntry, InfraplanReport.year)
        .join(InfraplanReport, InfraplanReport.id == InfraplanEntry.report_id)
        .filter(InfraplanEntry.id.in_(ids))
    )
    return {
        e.id: (
            e.massnahme or e.bezeichnung or f"Nr. {e.lfd_nr}",
            f"Infraplan {year} · {_SECTION_SHORT.get(e.section, e.section)} Nr. {e.lfd_nr}",
        )
        for e, year in rows
    }


def list_dismissed(db: Session) -> list[dict]:
    """All ignored records, newest first, with a readable label. Rows whose
    record is gone are left out."""
    rows = db.query(AssignmentDismissal).order_by(AssignmentDismissal.dismissed_at.desc()).all()
    labels: dict[str, dict[int, tuple[str, str | None]]] = {}
    for kind in _MODELS:
        labels[kind] = _labels(db, kind, [r.entry_id for r in rows if r.kind == kind])
    result = []
    for r in rows:
        label = labels.get(r.kind, {}).get(r.entry_id)
        if label is None:
            continue
        result.append(
            {
                "kind": r.kind,
                "entry_id": r.entry_id,
                "label": label[0],
                "detail": label[1],
                "note": r.note,
                "dismissed_at": r.dismissed_at,
                "dismissed_by": r.dismissed_by_username,
            }
        )
    return result
