"""Fulda-Runde import tools (feature-fulda-import.md).

The agent reads a Fulda answer (PDF) itself and records it here: document,
entries, project assignment, confirmation. The skill ``.claude/skills/fulda-runde``
holds the reading rules. Every tool requires ``fulda.import``.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from dashboard_backend.crud.projects.projects import replacement_warnings
from dashboard_backend.crud import fulda as fulda_crud
from dashboard_backend.crud._importer_common import ProjectNotFoundError
from dashboard_backend.mcp.context import get_principal, load_user, require, tool_session
from dashboard_backend.mcp.tools.projects import DESTRUCTIVE, READ_ONLY, WRITE
from dashboard_backend.schemas.fulda import (
    AnswerStatusLiteral,
    AttributedToLiteral,
    FuldaDocumentSchema,
    FuldaEntrySchema,
)
from dashboard_backend.services.fulda_categories import FULDA_CATEGORY_LIST

PERMISSION = "fulda.import"

_DOCUMENT_CHANGE_FIELDS = {"year", "drucksache", "title", "document_date", "dip_url", "answer_status", "note"}
_ENTRY_CHANGE_FIELDS = {
    "raw_name",
    "abschnitt",
    "category",
    "expected_date",
    "question_ref",
    "page",
    "raw_text",
    "attributed_to",
    "assignment_note",
}


class FuldaEntryInput(BaseModel):
    """One statement of the answer — one project (section) in one list."""

    raw_name: str = Field(description="Spalte 'Projekt' bzw. Teil vor dem Doppelpunkt, wörtlich")
    abschnitt: str | None = Field(
        None, description="Spalte 'Abschnitt' bzw. Teil nach dem Doppelpunkt; 'Gesamtstrecke' wenn keiner"
    )
    category: str = Field(description="Schlüssel aus list_fulda_categories")
    raw_text: str = Field(description="Die Zeile/Zelle wörtlich, wie sie im Dokument steht")
    question_ref: str | None = Field(None, description="z. B. 'Frage 3'")
    page: int | None = Field(None, description="Seite im PDF")
    expected_date: date | None = Field(
        None, description="Nur bei PROGNOSE/NEUAUFNAHME: angekündigter Termin, z. B. 2026-12-31 für 'bis Ende 2026'"
    )
    attributed_to: AttributedToLiteral | None = Field(
        None, description="'DB' bei 'nach Angaben/Auskunft der DB AG', sonst 'BMV'"
    )


def _entry_out(entry: dict) -> dict[str, Any]:
    return FuldaEntrySchema.model_validate(entry).model_dump(mode="json")


def _document_out(doc: dict) -> dict[str, Any]:
    return FuldaDocumentSchema.model_validate(doc).model_dump(mode="json")


def list_fulda_categories(*, ctx: Context) -> dict[str, Any]:
    """Fulda categories with meaning, statement kind and effect (requires
    ``fulda.import``). IST/OHNE_FOLGEPHASE set the project's phase as of the
    document date; PROGNOSE/NEUAUFNAHME only give an expected date in the
    forecast; phase null = hint only."""
    require(get_principal(ctx), PERMISSION)
    return {
        "categories": [
            {
                "key": c.key,
                "label": c.label,
                "statement_kind": c.kind,
                "phase": c.phase.value if c.phase else None,
            }
            for c in FULDA_CATEGORY_LIST
        ]
    }


def list_fulda_documents(year: int | None = None, *, ctx: Context) -> dict[str, Any]:
    """Recorded Fulda answers with counters total/assigned/confirmed (requires
    ``fulda.import``). Check here before creating a document."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        return {"documents": [_document_out(d) for d in fulda_crud.list_documents(db, year=year)]}


def create_fulda_document(
    year: int,
    drucksache: str,
    document_date: date,
    title: str | None = None,
    dip_url: str | None = None,
    answer_status: AnswerStatusLiteral = "VOLLSTAENDIG",
    note: str | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Record a Fulda answer (requires ``fulda.import``).

    - year: the Fulda-Runde year the question asks about
    - drucksache: e.g. '21/5855' (unique)
    - document_date: date of the answer (cover letter)
    - answer_status: VOLLSTAENDIG, TEILWEISE (some questions unanswered) or
      OHNE_ERGEBNIS (no project lists at all)
    - note: unanswered questions and the reason given"""
    principal = get_principal(ctx)
    require(principal, PERMISSION)
    payload = {
        "year": year,
        "drucksache": drucksache,
        "document_date": document_date,
        "title": title,
        "dip_url": dip_url,
        "answer_status": answer_status,
        "note": note,
    }
    with tool_session(ctx) as db:
        try:
            doc = fulda_crud.create_document(db, payload, load_user(db, principal))
        except fulda_crud.FuldaValidationError as exc:
            raise ToolError(str(exc)) from exc
        return _document_out(doc)


def update_fulda_document(
    document_id: int, changes: dict[str, Any], *, ctx: Context
) -> dict[str, Any]:
    """Change a document's metadata (requires ``fulda.import``). Allowed keys:
    year, drucksache, title, document_date, dip_url, answer_status, note."""
    require(get_principal(ctx), PERMISSION)
    unknown = set(changes) - _DOCUMENT_CHANGE_FIELDS
    if unknown:
        raise ToolError(f"Nicht änderbar: {', '.join(sorted(unknown))}")
    if "document_date" in changes and isinstance(changes["document_date"], str):
        try:
            changes["document_date"] = date.fromisoformat(changes["document_date"])
        except ValueError as exc:
            raise ToolError("document_date muss JJJJ-MM-TT sein.") from exc
    with tool_session(ctx) as db:
        try:
            doc = fulda_crud.update_document(db, document_id, changes)
        except fulda_crud.FuldaValidationError as exc:
            raise ToolError(str(exc)) from exc
        if doc is None:
            raise ToolError(f"Dokument {document_id} gibt es nicht.")
        return _document_out(doc)


def add_fulda_entries(
    document_id: int, entries: list[FuldaEntryInput], *, ctx: Context
) -> dict[str, Any]:
    """Add statements of a document (requires ``fulda.import``), all or nothing.

    One entry per project (section) and list. Split a cell naming several
    measures into several entries with the same raw_text. Each new entry comes
    back with project_ids pre-filled from a name match; its assignment_note
    says it is unchecked — confirm or correct it with assign_fulda_entry."""
    principal = get_principal(ctx)
    require(principal, PERMISSION)
    if not entries:
        raise ToolError("Keine Einträge übergeben.")
    items = [e.model_dump(exclude_none=True) for e in entries]
    with tool_session(ctx) as db:
        try:
            rows = fulda_crud.add_entries(db, document_id, items, load_user(db, principal))
        except fulda_crud.FuldaValidationError as exc:
            raise ToolError(str(exc)) from exc
        return {"entries": [_entry_out(r) for r in rows]}


def list_fulda_entries(
    document_id: int, only_open: bool = False, *, ctx: Context
) -> dict[str, Any]:
    """Entries of a document with assignment and note (requires
    ``fulda.import``). only_open: not yet confirmed."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        if fulda_crud.get_document(db, document_id) is None:
            raise ToolError(f"Dokument {document_id} gibt es nicht.")
        rows = fulda_crud.list_entries(db, document_id=document_id, only_unconfirmed=only_open)
        return {"entries": [_entry_out(r) for r in rows]}


def assign_fulda_entry(
    entry_id: int, project_ids: list[int], note: str, *, ctx: Context
) -> dict[str, Any]:
    """Set the projects of an entry, replacing the suggestion (requires
    ``fulda.import``). Prefer the subproject matching the Abschnitt; note says
    why (e.g. 'Teilprojekt Lehrte, Name und Abschnitt stimmen überein').
    An empty list removes the assignment."""
    require(get_principal(ctx), PERMISSION)
    if not note.strip():
        raise ToolError("Eine Begründung (note) ist Pflicht.")
    with tool_session(ctx) as db:
        try:
            entry = fulda_crud.update_entry(
                db, entry_id, {"project_ids": project_ids, "assignment_note": note.strip()}
            )
        except ProjectNotFoundError as exc:
            raise ToolError(str(exc)) from exc
        if entry is None:
            raise ToolError(f"Eintrag {entry_id} gibt es nicht.")
        return _with_warnings(_entry_out(entry), replacement_warnings(db, project_ids))


def _with_warnings(out: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    if warnings:
        out["warnings"] = warnings
    return out


def update_fulda_entry(
    entry_id: int, changes: dict[str, Any], *, ctx: Context
) -> dict[str, Any]:
    """Correct an entry (requires ``fulda.import``). Allowed keys: raw_name,
    abschnitt, category, expected_date, question_ref, page, raw_text,
    attributed_to, assignment_note."""
    require(get_principal(ctx), PERMISSION)
    unknown = set(changes) - _ENTRY_CHANGE_FIELDS
    if unknown:
        raise ToolError(f"Nicht änderbar: {', '.join(sorted(unknown))}")
    if isinstance(changes.get("expected_date"), str):
        try:
            changes["expected_date"] = date.fromisoformat(changes["expected_date"])
        except ValueError as exc:
            raise ToolError("expected_date muss JJJJ-MM-TT sein.") from exc
    with tool_session(ctx) as db:
        try:
            entry = fulda_crud.update_entry(db, entry_id, changes)
        except fulda_crud.FuldaValidationError as exc:
            raise ToolError(str(exc)) from exc
        if entry is None:
            raise ToolError(f"Eintrag {entry_id} gibt es nicht.")
        return _entry_out(entry)


def delete_fulda_entry(entry_id: int, *, ctx: Context) -> dict[str, Any]:
    """Delete a wrong entry (requires ``fulda.import``); its observations go too."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        if not fulda_crud.delete_entry(db, entry_id):
            raise ToolError(f"Eintrag {entry_id} gibt es nicht.")
        return {"deleted": entry_id}


def confirm_fulda_document(document_id: int, *, ctx: Context) -> dict[str, Any]:
    """Confirm all open entries of a document that have projects (requires
    ``fulda.import``). Confirmed entries feed the planning state: phases for
    IST lines, expected dates for prognoses. Entries without projects stay
    open. Returns the updated document counters."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        doc = fulda_crud.get_document(db, document_id)
        if doc is None:
            raise ToolError(f"Dokument {document_id} gibt es nicht.")
        confirmed = fulda_crud.confirm_document(db, document_id)
        docs = fulda_crud.list_documents(db, year=doc.year)
        current = next(d for d in docs if d["id"] == document_id)
        return {"confirmed_now": confirmed, "document": _document_out(current)}


def register(server: MCPServer) -> None:
    for fn in (list_fulda_categories, list_fulda_documents, list_fulda_entries):
        server.add_tool(fn, annotations=READ_ONLY)
    for fn in (
        create_fulda_document,
        update_fulda_document,
        add_fulda_entries,
        assign_fulda_entry,
        update_fulda_entry,
        confirm_fulda_document,
    ):
        server.add_tool(fn, annotations=WRITE)
    server.add_tool(delete_fulda_entry, annotations=DESTRUCTIVE)
