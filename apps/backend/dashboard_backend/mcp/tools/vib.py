"""VIB import tools (feature-vib-import.md → Phase 7).

The agent reads a Verkehrsinvestitionsbericht (PDF) itself and records it
here: report, Vorhaben with PFA table, project assignment with a reason,
confirmation. The skill ``.claude/skills/vib-import`` holds the reading rules
and the check mode for existing years. Every write leaves the entry
unconfirmed; only ``confirm_vib_report`` lets it feed the planning state.
Every tool requires ``vib.import``.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from dashboard_backend.crud import vib_agent
from dashboard_backend.crud._importer_common import ProjectNotFoundError
from dashboard_backend.mcp.context import get_principal, load_user, require, tool_session
from dashboard_backend.mcp.tools.projects import DESTRUCTIVE, READ_ONLY, WRITE

PERMISSION = "vib.import"

CategoryLiteral = Literal["laufend", "neu", "potentiell", "abgeschlossen"]

_REPORT_CHANGE_FIELDS = {"drucksache_nr", "report_date"}
_ENTRY_CHANGE_FIELDS = {
    "vib_section",
    "vib_lfd_nr",
    "vib_name_raw",
    "category",
    "page",
    "verkehrliche_zielsetzung",
    "durchgefuehrte_massnahmen",
    "noch_umzusetzende_massnahmen",
    "bauaktivitaeten",
    "teilinbetriebnahmen",
    "planungsstand",
    "sonstiges",
    "raw_text",
    "strecklaenge_km",
    "gesamtkosten_mio_eur",
    "entwurfsgeschwindigkeit",
    "status_planung",
    "status_bau",
    "status_abgeschlossen",
}


class VibPfaInput(BaseModel):
    """One row of the PFA table (Planfeststellungsabschnitte), as printed."""

    abschnitt_label: str | None = Field(
        None, description="Gruppenzeile über den PFA, z. B. 'Lübeck–Bad Kleinen' oder '1. Baustufe'"
    )
    nr_pfa: str | None = Field(None, description="Spalte 'Nr. PFA', z. B. '1.1'")
    oertlichkeit: str | None = Field(None, description="Spalte 'Örtlichkeit'")
    entwurfsplanung: str | None = Field(
        None, description="Spalte 'Entwurfsplanung' wörtlich, z. B. 'abgeschlossen', 'offen'"
    )
    abschluss_finve: str | None = Field(None, description="Spalte 'Abschluss FinVe' wörtlich")
    datum_pfb: str | None = Field(None, description="Spalte 'Datum PFB' wörtlich")
    baubeginn: str | None = Field(None, description="Spalte 'Baubeginn' wörtlich")
    inbetriebnahme: str | None = Field(None, description="Spalte 'Inbetriebnahme' wörtlich")
    project_id: int | None = Field(
        None, description="Teilprojekt, wenn schon klar; sonst später mit assign_vib_pfa"
    )


class VibEntryInput(BaseModel):
    """One Vorhaben (B.4.x.x block) of the report."""

    vib_section: str = Field(description="Sektionsnummer, z. B. 'B.4.1.3'")
    vib_name_raw: str = Field(description="Überschrift des Vorhabens wörtlich, ohne Sektionsnummer")
    category: CategoryLiteral = Field(
        description="Aus der Gliederung: laufend (B.4.1), neu (B.4.2), potentiell (B.4.3), abgeschlossen"
    )
    page: int | None = Field(None, description="Seite im PDF, auf der das Vorhaben beginnt")
    verkehrliche_zielsetzung: str | None = None
    durchgefuehrte_massnahmen: str | None = Field(
        None, description="Abschnitt 'Durchgeführte (und geplante) Maßnahmen'"
    )
    noch_umzusetzende_massnahmen: str | None = None
    bauaktivitaeten: str | None = Field(None, description="Abschnitt 'Bauaktivitäten [Jahr]'")
    teilinbetriebnahmen: str | None = Field(
        None, description="Abschnitt 'Teilinbetriebnahmen [Jahr]'; 'Keine' wörtlich übernehmen"
    )
    planungsstand: str | None = Field(None, description="Abschnitt 'Projektstand'/'Planungsstand'")
    sonstiges: str | None = Field(None, description="Fußnoten, Hinweise, die zu keinem Abschnitt gehören")
    strecklaenge_km: float | None = None
    gesamtkosten_mio_eur: float | None = None
    entwurfsgeschwindigkeit: str | None = Field(None, description="z. B. '200' oder '160/230'")
    status_planung: bool = Field(False, description="Teile des Vorhabens sind in Planung")
    status_bau: bool = Field(False, description="Teile des Vorhabens sind im Bau")
    status_abgeschlossen: bool = Field(
        False, description="Vorhaben (oder Teile) in Betrieb genommen"
    )
    pfa_entries: list[VibPfaInput] = Field(default_factory=list, description="PFA-Tabelle zeilenweise")


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except vib_agent.VibValidationError as exc:
        raise ToolError(str(exc)) from exc
    except ProjectNotFoundError as exc:
        raise ToolError(str(exc)) from exc


def _json(data: Any) -> Any:
    """Dates → ISO strings (tool results are JSON)."""
    if isinstance(data, dict):
        return {k: _json(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_json(v) for v in data]
    if isinstance(data, date):
        return data.isoformat()
    return data


def list_vib_reports(*, ctx: Context) -> dict[str, Any]:
    """VIB reports with year, Drucksache, report date and counters
    total/assigned/confirmed (requires ``vib.import``). Check here before
    creating a report — one report per year."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        return {"reports": _json(vib_agent.list_reports(db))}


def create_vib_report(
    year: int, report_date: date, drucksache_nr: str | None = None, *, ctx: Context
) -> dict[str, Any]:
    """Record a VIB report (requires ``vib.import``).

    - year: Berichtsjahr from the title ('Verkehrsinvestitionsbericht für das
      Berichtsjahr 2023' → 2023)
    - report_date: date of the Drucksache (cover page), JJJJ-MM-TT
    - drucksache_nr: e.g. '20/12345'
    An existing year is an error naming its report id — continue with that."""
    principal = get_principal(ctx)
    require(principal, PERMISSION)
    with tool_session(ctx) as db:
        report = _guard(
            vib_agent.create_report, db, year, drucksache_nr, report_date, load_user(db, principal)
        )
        return _json(report)


def update_vib_report(report_id: int, changes: dict[str, Any], *, ctx: Context) -> dict[str, Any]:
    """Correct a report's Drucksache or date (requires ``vib.import``).
    Allowed keys: drucksache_nr, report_date (JJJJ-MM-TT). The year cannot change."""
    require(get_principal(ctx), PERMISSION)
    unknown = set(changes) - _REPORT_CHANGE_FIELDS
    if unknown:
        raise ToolError(f"Nicht änderbar: {', '.join(sorted(unknown))}")
    if isinstance(changes.get("report_date"), str):
        try:
            changes["report_date"] = date.fromisoformat(changes["report_date"])
        except ValueError as exc:
            raise ToolError("report_date muss JJJJ-MM-TT sein.") from exc
    with tool_session(ctx) as db:
        report = vib_agent.update_report(db, report_id, changes)
        if report is None:
            raise ToolError(f"Bericht {report_id} gibt es nicht.")
        return _json(report)


def list_vib_entries(
    report_id: int, only_open: bool = False, search: str | None = None, *, ctx: Context
) -> dict[str, Any]:
    """Vorhaben of a report in section order, compact: section, name,
    category, projects, assignment note, confirmed, PFA counts (requires
    ``vib.import``). only_open: not yet confirmed. search: part of name or
    section."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        if vib_agent.get_report(db, report_id) is None:
            raise ToolError(f"Bericht {report_id} gibt es nicht.")
        return {"entries": vib_agent.list_entries(db, report_id, only_open=only_open, search=search)}


def get_vib_entry(entry_id: int, *, ctx: Context) -> dict[str, Any]:
    """One Vorhaben with all fields and its PFA rows (requires ``vib.import``).
    Each unassigned PFA row carries a subproject suggestion from the
    subprojects of the assigned projects; unconfirmed entries also list the
    project suggestions with their reason."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        entry = vib_agent.get_entry(db, entry_id)
        if entry is None:
            raise ToolError(f"Eintrag {entry_id} gibt es nicht.")
        return _json(entry)


def add_vib_entries(
    report_id: int, entries: list[VibEntryInput], *, ctx: Context
) -> dict[str, Any]:
    """Add Vorhaben with their PFA tables (requires ``vib.import``), all or
    nothing, unconfirmed. A section already in the report is rejected — fix it
    with update_vib_entry. Each entry comes back with `suggestions`
    (previous year → VDE number → name, with reason); at most the best one is
    pre-assigned (all projects of the previous year's entry if that matched),
    and assignment_note says it is unchecked. Check every one with
    assign_vib_entry. Send a few entries per call (long texts)."""
    require(get_principal(ctx), PERMISSION)
    if not entries:
        raise ToolError("Keine Einträge übergeben.")
    items = [e.model_dump() for e in entries]
    with tool_session(ctx) as db:
        return {"entries": _guard(vib_agent.add_entries, db, report_id, items)}


def update_vib_entry(entry_id: int, changes: dict[str, Any], *, ctx: Context) -> dict[str, Any]:
    """Correct fields of a Vorhaben (requires ``vib.import``); it becomes
    unconfirmed until confirmed again. Allowed keys: vib_section, vib_lfd_nr,
    vib_name_raw, category, page, the text sections (verkehrliche_zielsetzung,
    durchgefuehrte_massnahmen, noch_umzusetzende_massnahmen, bauaktivitaeten,
    teilinbetriebnahmen, planungsstand, sonstiges, raw_text), strecklaenge_km,
    gesamtkosten_mio_eur, entwurfsgeschwindigkeit, status_planung, status_bau,
    status_abgeschlossen. Projects: assign_vib_entry; PFA table:
    set_vib_pfa_entries."""
    require(get_principal(ctx), PERMISSION)
    unknown = set(changes) - _ENTRY_CHANGE_FIELDS
    if unknown:
        raise ToolError(f"Nicht änderbar: {', '.join(sorted(unknown))}")
    with tool_session(ctx) as db:
        entry = _guard(vib_agent.update_entry, db, entry_id, dict(changes))
        if entry is None:
            raise ToolError(f"Eintrag {entry_id} gibt es nicht.")
        return _json(entry)


def set_vib_pfa_entries(
    entry_id: int, pfa_entries: list[VibPfaInput], *, ctx: Context
) -> dict[str, Any]:
    """Replace the whole PFA table of a Vorhaben (requires ``vib.import``);
    unconfirms the entry. Keep project_id on rows already assigned to a
    subproject, otherwise the assignment is lost."""
    require(get_principal(ctx), PERMISSION)
    items = [p.model_dump() for p in pfa_entries]
    with tool_session(ctx) as db:
        entry = _guard(vib_agent.set_pfa_entries, db, entry_id, items)
        if entry is None:
            raise ToolError(f"Eintrag {entry_id} gibt es nicht.")
        return _json(entry)


def assign_vib_entry(
    entry_id: int, project_ids: list[int], note: str, *, ctx: Context
) -> dict[str, Any]:
    """Set the projects of a Vorhaben — one or several — replacing the
    previous assignment (requires ``vib.import``); unconfirms the entry.
    note says why, for all projects together (e.g. 'Oberprojekt ABS Lübeck–
    Rostock, VDE Nr. 1 und Name stimmen; Vorjahr gleich'). An empty list
    removes the assignment."""
    require(get_principal(ctx), PERMISSION)
    if not note.strip():
        raise ToolError("Eine Begründung (note) ist Pflicht.")
    with tool_session(ctx) as db:
        entry = _guard(vib_agent.assign_entry, db, entry_id, project_ids, note.strip())
        if entry is None:
            raise ToolError(f"Eintrag {entry_id} gibt es nicht.")
        return _json(entry)


def assign_vib_pfa(pfa_id: int, project_id: int | None, *, ctx: Context) -> dict[str, Any]:
    """Assign one PFA section to the (sub)project it describes, or clear it
    with null (requires ``vib.import``); unconfirms the Vorhaben. The section's
    dates then feed that subproject instead of the parent. Returns the whole
    Vorhaben."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        entry = _guard(vib_agent.assign_pfa, db, pfa_id, project_id)
        if entry is None:
            raise ToolError(f"PFA-Zeile {pfa_id} gibt es nicht.")
        return _json(entry)


def delete_vib_entry(entry_id: int, *, ctx: Context) -> dict[str, Any]:
    """Delete a wrong Vorhaben with its PFA rows (requires ``vib.import``);
    its observations go too."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        if not vib_agent.delete_entry(db, entry_id):
            raise ToolError(f"Eintrag {entry_id} gibt es nicht.")
        return {"deleted": entry_id}


def confirm_vib_report(
    report_id: int, entry_ids: list[int] | None = None, *, ctx: Context
) -> dict[str, Any]:
    """Confirm the open Vorhaben of a report that have projects (requires
    ``vib.import``); entry_ids limits it to these. Confirmed entries feed the
    planning state (phase flags, PFA dates). Entries without projects stay
    open. Returns the count and the report counters."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        if vib_agent.get_report(db, report_id) is None:
            raise ToolError(f"Bericht {report_id} gibt es nicht.")
        confirmed = vib_agent.confirm_report(db, report_id, entry_ids)
        return {"confirmed_now": confirmed, "report": _json(vib_agent.report_summary(db, report_id))}


def register(server: MCPServer) -> None:
    for fn in (list_vib_reports, list_vib_entries, get_vib_entry):
        server.add_tool(fn, annotations=READ_ONLY)
    for fn in (
        create_vib_report,
        update_vib_report,
        add_vib_entries,
        update_vib_entry,
        set_vib_pfa_entries,
        assign_vib_entry,
        assign_vib_pfa,
        confirm_vib_report,
    ):
        server.add_tool(fn, annotations=WRITE)
    server.add_tool(delete_vib_entry, annotations=DESTRUCTIVE)
