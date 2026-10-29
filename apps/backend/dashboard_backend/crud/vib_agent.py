"""DB access for reading a VIB in over MCP (feature-vib-import.md → Phase 7).

An agent reads the Verkehrsinvestitionsbericht itself and records it here:
one ``VibReport`` per year, one ``VibEntry`` per Vorhaben with its PFA rows,
project assignment with a reason, confirmation. Everything written here is
unconfirmed (``VibEntry.confirmed = False``) until ``confirm_report``; only
confirmed entries materialise progress observations. The upload path
(``crud/vib.py``) stays as the second way in and writes confirmed entries.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone

from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload, load_only, selectinload

from dashboard_backend.crud.projects.archive import successor_map
from dashboard_backend.crud._importer_common import ensure_projects_exist, recompute_for
from dashboard_backend.crud.changelog import create_changelog_for_create
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.users import User
from dashboard_backend.models.vib.vib_entry import VibEntry
from dashboard_backend.models.vib.vib_entry_project import vib_entry_project
from dashboard_backend.models.vib.vib_pfa_entry import VibPfaEntry
from dashboard_backend.models.vib.vib_report import VibReport
from dashboard_backend.tasks.vib_matching import (
    PfaSuggestion,
    extract_vib_lfd_nr,
    pfa_row_key,
    place_stop_tokens,
    rank_projects_for_vib_entry,
    same_vib_name,
    suggest_subproject_for_pfa,
)

CATEGORIES = ("laufend", "neu", "potentiell", "abgeschlossen")

AUTO_SUGGESTION_NOTE = "Automatischer Vorschlag ({reason}), ungeprüft"

_REPORT_FIELDS = {"drucksache_nr", "report_date"}
# Content fields an agent may write on an entry (vib_section is the key and
# only changes through update_entry with an explicit check).
_ENTRY_FIELDS = {
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
_TEXT_FIELDS = (
    "verkehrliche_zielsetzung",
    "durchgefuehrte_massnahmen",
    "noch_umzusetzende_massnahmen",
    "bauaktivitaeten",
    "teilinbetriebnahmen",
    "planungsstand",
    "sonstiges",
)
_PFA_FIELDS = (
    "abschnitt_label",
    "nr_pfa",
    "oertlichkeit",
    "entwurfsplanung",
    "abschluss_finve",
    "datum_pfb",
    "baubeginn",
    "inbetriebnahme",
    "project_id",
)

_SECTION_RE = re.compile(r"^B[\s.]?(\d+(?:\.\d+)+)$", re.IGNORECASE)


class VibValidationError(ValueError):
    """Invalid input (unknown category, duplicate section, …); message is German."""


# --- Validation --------------------------------------------------------------


def normalize_section(value: str) -> str:
    """'B 4.1.1' / 'b.4.1.1' / 'B4.1.1' → 'B.4.1.1'."""
    raw = (value or "").strip()
    m = _SECTION_RE.match(raw)
    if m is None:
        raise VibValidationError(
            f"Sektionsnummer '{value}' nicht erkannt — erwartet wie 'B.4.1.3'."
        )
    return f"B.{m.group(1)}"


def _validate_entry(payload: dict) -> None:
    if "category" in payload and payload["category"] not in CATEGORIES:
        raise VibValidationError(
            f"Unbekannte Kategorie '{payload['category']}'. Erlaubt: {', '.join(CATEGORIES)}."
        )
    if "vib_name_raw" in payload and not (payload["vib_name_raw"] or "").strip():
        raise VibValidationError("'vib_name_raw' darf nicht leer sein.")
    if payload.get("vib_section") is not None:
        payload["vib_section"] = normalize_section(payload["vib_section"])
    for key in _TEXT_FIELDS:
        # Empty strings mean "no text" — store NULL, not "".
        if key in payload and isinstance(payload[key], str) and not payload[key].strip():
            payload[key] = None


# --- Serialisation -----------------------------------------------------------


def _report_dict(report: VibReport, counts: dict | None = None) -> dict:
    counts = counts or {}
    return {
        "id": report.id,
        "year": report.year,
        "drucksache_nr": report.drucksache_nr,
        "report_date": report.report_date,
        "imported_at": report.imported_at,
        "total": counts.get("total", 0),
        "assigned": counts.get("assigned", 0),
        "confirmed": counts.get("confirmed", 0),
    }


def _entry_summary(entry: VibEntry) -> dict:
    linked = sorted(entry.projects, key=lambda p: p.name or "")
    return {
        "id": entry.id,
        "report_id": entry.vib_report_id,
        "vib_section": entry.vib_section,
        "vib_name_raw": entry.vib_name_raw,
        "category": entry.category,
        "page": entry.page,
        "project_ids": [p.id for p in linked],
        "project_names": [p.name for p in linked if p.name],
        "assignment_note": entry.assignment_note,
        "confirmed": entry.confirmed,
        "pfa_count": len(entry.pfa_entries),
        "pfa_assigned": sum(1 for pfa in entry.pfa_entries if pfa.project_id is not None),
    }


def _pfa_dict(pfa: VibPfaEntry, suggestion: PfaSuggestion | None = None) -> dict:
    return {
        "id": pfa.id,
        **{key: getattr(pfa, key) for key in _PFA_FIELDS},
        "suggested_project_id": suggestion.project_id if suggestion else None,
        "suggested_reason": suggestion.reason if suggestion else None,
        "suggestion_strong": suggestion.strong if suggestion else None,
    }


# --- PFA → subproject (feature-vib-import.md → Phase 8) -----------------------


def _subtree(db: Session, root_ids: list[int]) -> dict[int, tuple[Project, int]]:
    """All non-archived descendants of ``root_ids`` as {id: (project, depth)} (depth 1 = child)."""
    out: dict[int, tuple[Project, int]] = {}
    frontier, depth = list(root_ids), 0
    while frontier:
        depth += 1
        rows = (
            db.query(Project)
            .options(
                load_only(
                    Project.id,
                    Project.name,
                    Project.project_number,
                    Project.superior_project_id,
                    Project.is_draft,
                )
            )
            .filter(Project.superior_project_id.in_(frontier), Project.is_archived.is_(False))
            .all()
        )
        frontier = [p.id for p in rows if p.id not in out]
        for p in rows:
            out.setdefault(p.id, (p, depth))
    return out


def _pfa_candidates(db: Session, entry: VibEntry) -> dict[int, tuple[Project, int]]:
    """Subprojects a PFA row of ``entry`` may go to: the whole subtree below its
    projects, plus assigned projects that sit inside another assigned one."""
    linked_ids = [p.id for p in entry.projects]
    if not linked_ids:
        return {}
    return _subtree(db, linked_ids)


def _previous_pfa_assignments(db: Session, entry: VibEntry) -> tuple[dict, dict, int | None]:
    """PFA rows of the newest earlier confirmed report's same Vorhaben.

    Returns ({(nr, place): project_id}, {nr: project_id or None if ambiguous},
    year). Same Vorhaben = same section or the same normalised name.
    """
    report_year = entry.report.year if entry.report is not None else None
    query = (
        db.query(VibEntry)
        .join(VibReport, VibReport.id == VibEntry.vib_report_id)
        .options(selectinload(VibEntry.pfa_entries), joinedload(VibEntry.report))
        .filter(VibEntry.vib_report_id != entry.vib_report_id, VibEntry.confirmed.is_(True))
    )
    if report_year is not None:
        query = query.filter(VibReport.year < report_year)
    for old in query.order_by(VibReport.year.desc()).all():
        if old.vib_section != entry.vib_section and not same_vib_name(
            entry.vib_name_raw, old.vib_name_raw
        ):
            continue
        rows = [pfa for pfa in old.pfa_entries if pfa.project_id is not None]
        if not rows:
            continue
        by_key: dict[tuple[str, str], int] = {}
        by_nr: dict[str, int | None] = {}
        for pfa in rows:
            nr, place = pfa_row_key(pfa.nr_pfa, pfa.oertlichkeit)
            by_key[(nr, place)] = pfa.project_id
            if nr:
                by_nr[nr] = pfa.project_id if by_nr.get(nr, pfa.project_id) == pfa.project_id else None
        return by_key, by_nr, old.report.year
    return {}, {}, None


class _PfaMatcher:
    """Subproject suggestions for the PFA rows of one entry: previous year →
    section number → place name. ``root_id`` narrows the candidates to the
    subtree of one project (project page) instead of all the entry's projects."""

    def __init__(self, db: Session, entry: VibEntry, root_id: int | None = None):
        self.candidates = _subtree(db, [root_id]) if root_id is not None else _pfa_candidates(db, entry)
        self.stop = place_stop_tokens(entry.vib_name_raw, *(p.name for p in entry.projects))
        self.by_key, self.by_nr, self.year = (
            _previous_pfa_assignments(db, entry) if self.candidates else ({}, {}, None)
        )

    def suggest(self, pfa: VibPfaEntry) -> PfaSuggestion | None:
        if not self.candidates:
            return None
        nr, place = pfa_row_key(pfa.nr_pfa, pfa.oertlichkeit)
        previous = self.by_key.get((nr, place))
        if previous is None and nr and not place:
            previous = self.by_nr.get(nr)
        if previous is None and place:
            matches = {pid for (_, p), pid in self.by_key.items() if p == place}
            previous = matches.pop() if len(matches) == 1 else None
        if previous is not None and previous in self.candidates:
            return PfaSuggestion(previous, "vorjahr", f"Vorjahr: VIB {self.year} bestätigt", True)
        return suggest_subproject_for_pfa(
            pfa.nr_pfa,
            pfa.oertlichkeit,
            pfa.abschnitt_label,
            list(self.candidates.values()),
            self.stop,
        )


def pfa_suggestions_below(db: Session, entry: VibEntry, root_id: int) -> dict[int, PfaSuggestion]:
    """Suggestions for the open PFA rows of ``entry`` among the subprojects of
    ``root_id`` — {pfa_id: suggestion}."""
    matcher = _PfaMatcher(db, entry, root_id)
    out: dict[int, PfaSuggestion] = {}
    for pfa in entry.pfa_entries:
        if pfa.project_id is None:
            suggestion = matcher.suggest(pfa)
            if suggestion is not None:
                out[pfa.id] = suggestion
    return out


def _entry_detail(db: Session, entry: VibEntry) -> dict:
    """All fields, PFA rows with a subproject suggestion for open sections."""

    data = _entry_summary(entry)
    data.update({key: getattr(entry, key) for key in _ENTRY_FIELDS})
    data["report_year"] = entry.report.year if entry.report is not None else None

    matcher = _PfaMatcher(db, entry)
    names = {pid: p.name for pid, (p, _) in matcher.candidates.items()}
    pfas = []
    for pfa in sorted(entry.pfa_entries, key=lambda p: p.id):
        suggestion = matcher.suggest(pfa) if pfa.project_id is None else None
        row = _pfa_dict(pfa, suggestion)
        row["suggested_project_name"] = names.get(suggestion.project_id) if suggestion else None
        pfas.append(row)
    data["pfa_entries"] = pfas
    data["subprojects"] = [
        {
            "id": p.id,
            "name": p.name,
            "superior_project_id": p.superior_project_id,
            "depth": depth,
            "is_draft": bool(p.is_draft),
        }
        for p, depth in sorted(matcher.candidates.values(), key=lambda x: (x[1], x[0].name or ""))
    ]
    return data


# --- Reports -------------------------------------------------------------------


def _report_counts(db: Session) -> dict[int, dict]:
    assigned_ids = db.query(vib_entry_project.c.vib_entry_id).distinct().subquery()
    rows = (
        db.query(
            VibEntry.vib_report_id,
            func.count(VibEntry.id),
            func.sum(case((VibEntry.id.in_(db.query(assigned_ids)), 1), else_=0)),
            func.sum(case((VibEntry.confirmed.is_(True), 1), else_=0)),
        )
        .group_by(VibEntry.vib_report_id)
        .all()
    )
    return {
        rid: {"total": int(t or 0), "assigned": int(a or 0), "confirmed": int(c or 0)}
        for rid, t, a, c in rows
    }


def list_reports(db: Session) -> list[dict]:
    reports = db.query(VibReport).order_by(VibReport.year.desc()).all()
    counts = _report_counts(db)
    return [_report_dict(r, counts.get(r.id)) for r in reports]


def get_report(db: Session, report_id: int) -> VibReport | None:
    return db.query(VibReport).filter(VibReport.id == report_id).first()


def report_summary(db: Session, report_id: int) -> dict | None:
    report = get_report(db, report_id)
    if report is None:
        return None
    return _report_dict(report, _report_counts(db).get(report.id))


def create_report(
    db: Session,
    year: int,
    drucksache_nr: str | None,
    report_date: date,
    user: User | None,
) -> dict:
    existing = db.query(VibReport).filter(VibReport.year == year).first()
    if existing is not None:
        raise VibValidationError(
            f"Für {year} gibt es schon den Bericht {existing.id} — mit dieser report_id weiterarbeiten."
        )
    report = VibReport(
        year=year,
        drucksache_nr=(drucksache_nr or "").strip() or None,
        report_date=report_date,
        imported_at=datetime.now(timezone.utc),
        imported_by_user_id=user.id if user else None,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return _report_dict(report)


def update_report(db: Session, report_id: int, payload: dict) -> dict | None:
    report = get_report(db, report_id)
    if report is None:
        return None
    for key, value in payload.items():
        if key in _REPORT_FIELDS:
            setattr(report, key, value)
    db.commit()
    # report_date weighs VIB against Fulda in the forecast.
    affected = {p.id for e in report.entries if e.confirmed for p in e.projects}
    recompute_for(db, affected)
    return report_summary(db, report_id)


# --- Suggestions ---------------------------------------------------------------


class _Matcher:
    """Project suggestions for VIB entries: previous year → VDE → name.

    Loads id/name/description/superior once — never the geometry.
    """

    def __init__(self, db: Session, report: VibReport):
        self.projects = (
            db.query(Project)
            .options(
                load_only(
                    Project.id, Project.name, Project.description, Project.superior_project_id
                )
            )
            .filter(Project.is_archived.is_(False))
            .all()
        )
        self.by_id = {p.id: p for p in self.projects}
        # Archived project → successor: last year's assignment to a replaced
        # project hands over (feature-project-archive.md → „Ersetzt durch“).
        self.successors = successor_map(db)
        # Confirmed, assigned entries of other reports (newest first) — the
        # editor's earlier decision is the strongest hint.
        self.history = (
            db.query(VibEntry)
            .join(VibReport, VibReport.id == VibEntry.vib_report_id)
            .options(selectinload(VibEntry.projects), joinedload(VibEntry.report))
            .filter(VibEntry.vib_report_id != report.id, VibEntry.confirmed.is_(True))
            .order_by(VibReport.year.desc())
            .all()
        )

    def suggest(self, name: str) -> list[dict]:
        """Candidates as {project_id, project_name, reason}, best first."""

        out: list[dict] = []
        seen: set[int] = set()
        for old in self.history:
            if old.projects and same_vib_name(name, old.vib_name_raw):
                for p in sorted(old.projects, key=lambda p: p.name or ""):
                    reason = f"Vorjahr: VIB {old.report.year} bestätigt"
                    target = self.successors.get(p.id, p.id)
                    if target != p.id:
                        reason += f" · umgelenkt von „{p.name}“ (archiviert, ersetzt)"
                    # An archived project without successor is no candidate.
                    if target in self.by_id and target not in seen:
                        out.append(
                            {
                                "project_id": target,
                                "project_name": self.by_id[target].name,
                                "reason": reason,
                            }
                        )
                        seen.add(target)
                break  # newest matching report only
        for pid, kind, score in rank_projects_for_vib_entry(name, self.projects)[:5]:
            if pid in seen:
                continue
            reason = "gleiche VDE-Nummer" if kind == "vde" else f"Namensähnlichkeit {score:.2f}"
            out.append({"project_id": pid, "project_name": self.by_id[pid].name, "reason": reason})
            seen.add(pid)
        return out


def _prefill(suggestions: list[dict]) -> list[dict]:
    """Projects to pre-assign: all from the previous year, else only the best one."""
    if not suggestions:
        return []
    if suggestions[0]["reason"].startswith("Vorjahr"):
        return [s for s in suggestions if s["reason"].startswith("Vorjahr")]
    return suggestions[:1]


# --- Entries -------------------------------------------------------------------


def _load_entry(db: Session, entry_id: int) -> VibEntry | None:
    return (
        db.query(VibEntry)
        .options(
            selectinload(VibEntry.pfa_entries),
            selectinload(VibEntry.projects),
            joinedload(VibEntry.report),
        )
        .filter(VibEntry.id == entry_id)
        .first()
    )


def _pfa_rows(db: Session, items: list[dict], index_label: str) -> list[VibPfaEntry]:
    project_ids = [i["project_id"] for i in items if i.get("project_id") is not None]
    if project_ids:
        try:
            ensure_projects_exist(db, project_ids)
        except Exception as exc:
            raise VibValidationError(f"{index_label}: {exc}") from exc
    rows = []
    for item in items:
        values = {k: item.get(k) for k in _PFA_FIELDS}
        if not any(values[k] for k in ("nr_pfa", "oertlichkeit", "abschnitt_label")):
            raise VibValidationError(
                f"{index_label}: PFA-Zeile braucht nr_pfa, oertlichkeit oder abschnitt_label."
            )
        rows.append(VibPfaEntry(**values))
    return rows


def add_entries(db: Session, report_id: int, items: list[dict]) -> list[dict]:
    """Create Vorhaben with their PFA rows, all-or-nothing, unconfirmed.

    Each item needs ``vib_section``, ``vib_name_raw`` and ``category``. A section
    already in the report is rejected (resume instead of duplicating). The
    assignment is pre-filled from the suggestions (previous year, else the best
    single candidate); ``assignment_note`` says so.
    """

    report = get_report(db, report_id)
    if report is None:
        raise VibValidationError(f"Bericht {report_id} gibt es nicht.")
    existing = {
        s for (s,) in db.query(VibEntry.vib_section).filter(VibEntry.vib_report_id == report_id)
    }
    seen: set[str] = set()
    prepared: list[tuple[dict, list[VibPfaEntry]]] = []
    for index, raw in enumerate(items):
        label = f"Eintrag {index + 1}"
        item = dict(raw)
        pfa_items = item.pop("pfa_entries", None) or []
        for key in ("vib_section", "vib_name_raw", "category"):
            if not str(item.get(key) or "").strip():
                raise VibValidationError(f"{label}: '{key}' ist Pflicht.")
        try:
            _validate_entry(item)
        except VibValidationError as exc:
            raise VibValidationError(f"{label}: {exc}") from exc
        section = item["vib_section"]
        if section in existing:
            raise VibValidationError(
                f"{label}: {section} ist in diesem Bericht schon erfasst — "
                "mit update_vib_entry korrigieren statt neu anlegen."
            )
        if section in seen:
            raise VibValidationError(f"{label}: {section} kommt im Aufruf doppelt vor.")
        seen.add(section)
        prepared.append((item, _pfa_rows(db, pfa_items, label)))

    matcher = _Matcher(db, report)
    created: list[tuple[VibEntry, list[dict]]] = []
    for item, pfa_rows in prepared:
        suggestions = matcher.suggest(item["vib_name_raw"])
        prefill = _prefill(suggestions)
        entry = VibEntry(
            vib_report_id=report.id,
            **{k: v for k, v in item.items() if k in _ENTRY_FIELDS},
            confirmed=False,
            projects=[matcher.by_id[s["project_id"]] for s in prefill],
            pfa_entries=pfa_rows,
        )
        if item.get("vib_lfd_nr") is None:
            entry.vib_lfd_nr = extract_vib_lfd_nr(item["vib_name_raw"])
        if prefill:
            entry.assignment_note = AUTO_SUGGESTION_NOTE.format(reason=prefill[0]["reason"])
        db.add(entry)
        created.append((entry, suggestions))
    db.commit()

    out = []
    for entry, suggestions in created:
        db.refresh(entry)
        row = _entry_summary(entry)
        row["suggestions"] = suggestions
        out.append(row)
    return out


def list_entries(
    db: Session, report_id: int, *, only_open: bool = False, search: str | None = None
) -> list[dict]:
    query = (
        db.query(VibEntry)
        .options(selectinload(VibEntry.projects), selectinload(VibEntry.pfa_entries))
        .filter(VibEntry.vib_report_id == report_id)
    )
    if only_open:
        query = query.filter(VibEntry.confirmed.is_(False))
    if search:
        needle = f"%{search.strip()}%"
        query = query.filter(
            VibEntry.vib_name_raw.ilike(needle) | VibEntry.vib_section.ilike(needle)
        )
    rows = query.all()
    rows.sort(key=lambda e: _section_key(e.vib_section))
    return [_entry_summary(e) for e in rows]


def _section_key(section: str | None) -> tuple:
    if not section:
        return (1,)
    return (0, *[int(p) if p.isdigit() else 0 for p in section.split(".")[1:]])


def get_entry(db: Session, entry_id: int) -> dict | None:
    entry = _load_entry(db, entry_id)
    if entry is None:
        return None
    detail = _entry_detail(db, entry)
    if not entry.confirmed:
        detail["suggestions"] = _Matcher(db, entry.report).suggest(entry.vib_name_raw)
    return detail


def _unconfirm(db: Session, entry: VibEntry) -> set[int]:
    """Mark an entry open again; return projects whose progress must drop it."""
    affected = {p.id for p in entry.projects} | {
        pfa.project_id for pfa in entry.pfa_entries if pfa.project_id is not None
    }
    was_confirmed = entry.confirmed
    entry.confirmed = False
    return affected if was_confirmed else set()


def update_entry(db: Session, entry_id: int, payload: dict) -> dict | None:
    """Correct an entry's fields; it becomes unconfirmed until confirmed again."""

    entry = _load_entry(db, entry_id)
    if entry is None:
        return None
    _validate_entry(payload)
    section = payload.get("vib_section")
    if section is not None and section != entry.vib_section:
        clash = (
            db.query(VibEntry.id)
            .filter(VibEntry.vib_report_id == entry.vib_report_id, VibEntry.vib_section == section)
            .first()
        )
        if clash is not None:
            raise VibValidationError(f"{section} ist in diesem Bericht schon Eintrag {clash[0]}.")
    affected = _unconfirm(db, entry)
    for key, value in payload.items():
        if key in _ENTRY_FIELDS or key == "assignment_note":
            setattr(entry, key, value)
    db.commit()
    recompute_for(db, affected)
    return get_entry(db, entry_id)


def set_pfa_entries(db: Session, entry_id: int, items: list[dict]) -> dict | None:
    """Replace the PFA table of an entry (unconfirms it)."""

    entry = _load_entry(db, entry_id)
    if entry is None:
        return None
    rows = _pfa_rows(db, items, "PFA-Tabelle")
    affected = _unconfirm(db, entry)
    entry.pfa_entries.clear()
    db.flush()
    entry.pfa_entries.extend(rows)
    db.commit()
    recompute_for(db, affected)
    return get_entry(db, entry_id)


def assign_entry(db: Session, entry_id: int, project_ids: list[int], note: str) -> dict | None:
    """Replace the projects of an entry (one or several) with a reason; unconfirms."""

    entry = _load_entry(db, entry_id)
    if entry is None:
        return None
    projects = ensure_projects_exist(db, project_ids)
    affected = _unconfirm(db, entry)
    entry.projects = projects
    entry.assignment_note = note
    db.commit()
    recompute_for(db, affected)
    return get_entry(db, entry_id)


def assign_pfa(db: Session, pfa_id: int, project_id: int | None) -> dict | None:
    """Assign one PFA section to a (sub)project or clear it; unconfirms its entry."""

    pfa = db.query(VibPfaEntry).filter(VibPfaEntry.id == pfa_id).first()
    if pfa is None:
        return None
    if project_id is not None:
        ensure_projects_exist(db, [project_id])
    entry = _load_entry(db, pfa.vib_entry_id)
    affected = _unconfirm(db, entry)
    pfa.project_id = project_id
    db.commit()
    recompute_for(db, affected)
    return get_entry(db, entry.id)


def assign_pfas(db: Session, entry_id: int, items: list[tuple[int, int | None]]) -> dict | None:
    """Assign many PFA rows of one entry at once (``(pfa_id, project_id)``);
    the project must lie below the entry's projects. All or nothing; unconfirms."""

    entry = _load_entry(db, entry_id)
    if entry is None:
        return None
    rows = {pfa.id: pfa for pfa in entry.pfa_entries}
    candidates = _pfa_candidates(db, entry)
    for pfa_id, project_id in items:
        if pfa_id not in rows:
            raise VibValidationError(f"PFA-Zeile {pfa_id} gehört nicht zu Eintrag {entry_id}.")
        if project_id is not None and project_id not in candidates:
            raise VibValidationError(
                f"Projekt {project_id} liegt nicht unter den Projekten des Eintrags — "
                "erst den Eintrag zuordnen (assign_vib_entry) oder assign_vib_pfa nehmen."
            )
    affected = _unconfirm(db, entry)
    for pfa_id, project_id in items:
        rows[pfa_id].project_id = project_id
    db.commit()
    recompute_for(db, affected)
    return get_entry(db, entry_id)


def apply_pfa_suggestions(db: Session, report_id: int, entry_ids: list[int] | None = None) -> list[dict]:
    """Take over the strong PFA suggestions (previous year, unique section
    number) for open rows; weak ones (name) stay a suggestion. Unconfirms each
    changed entry. Returns per changed entry the applied rows."""

    query = (
        db.query(VibEntry)
        .options(
            selectinload(VibEntry.pfa_entries),
            selectinload(VibEntry.projects),
            joinedload(VibEntry.report),
        )
        .filter(VibEntry.vib_report_id == report_id)
    )
    if entry_ids is not None:
        query = query.filter(VibEntry.id.in_(entry_ids))
    out: list[dict] = []
    affected: set[int] = set()
    for entry in sorted(query.all(), key=lambda e: _section_key(e.vib_section)):
        open_rows = [pfa for pfa in entry.pfa_entries if pfa.project_id is None]
        if not open_rows:
            continue
        matcher = _PfaMatcher(db, entry)
        applied = []
        for pfa in sorted(open_rows, key=lambda p: p.id):
            suggestion = matcher.suggest(pfa)
            if suggestion is None or not suggestion.strong:
                continue
            applied.append((pfa, suggestion))
        if not applied:
            continue
        affected |= _unconfirm(db, entry)
        names = {pid: p.name for pid, (p, _) in matcher.candidates.items()}
        for pfa, suggestion in applied:
            pfa.project_id = suggestion.project_id
        out.append(
            {
                "entry_id": entry.id,
                "vib_section": entry.vib_section,
                "applied": [
                    {
                        "pfa_id": pfa.id,
                        "nr_pfa": pfa.nr_pfa,
                        "oertlichkeit": pfa.oertlichkeit,
                        "project_id": s.project_id,
                        "project_name": names.get(s.project_id),
                        "reason": s.reason,
                    }
                    for pfa, s in applied
                ],
                "still_open": sum(1 for pfa in entry.pfa_entries if pfa.project_id is None),
            }
        )
    db.commit()
    recompute_for(db, affected)
    return out


def _default_subproject_name(rows: list[VibPfaEntry]) -> str:
    """'PFA 7.1 Appenweier-Hohberg' from the rows; the label when it is shared."""
    numbers = list(dict.fromkeys(r.nr_pfa.strip() for r in rows if r.nr_pfa and r.nr_pfa.strip()))
    places = list(
        dict.fromkeys(
            r.oertlichkeit.strip()
            for r in rows
            if r.oertlichkeit and r.oertlichkeit.strip() and r.oertlichkeit.strip() not in ("ABS", "NBS")
        )
    )
    labels = {r.abschnitt_label.strip() for r in rows if r.abschnitt_label and r.abschnitt_label.strip()}
    parts = []
    if numbers:
        parts.append("PFA " + ", ".join(numbers))
    if places:
        parts.append(" / ".join(places[:2]))
    elif len(labels) == 1:
        parts.append(labels.pop())
    return (" ".join(parts) or "PFA-Abschnitt")[:255]


def create_pfa_subprojects(
    db: Session,
    entry_id: int,
    items: list[tuple[list[int], int, str | None]],
    user: User | None,
) -> list[dict] | None:
    """Create a draft project (no geometry) per item ``(pfa_ids, parent_id,
    name)`` under ``parent_id`` and assign the rows to it. The parent must be
    one of the entry's projects or lie below them; rows must belong to the entry
    and be unassigned. A failing item does not stop the others; one commit.

    A parent without children so far becomes an interim node: its own state
    then gives way to the span of its subprojects — the result says so
    (``parent_was_leaf``) and the skill tells the agent what to check."""

    entry = _load_entry(db, entry_id)
    if entry is None:
        return None
    rows = {pfa.id: pfa for pfa in entry.pfa_entries}
    allowed = set(_pfa_candidates(db, entry)) | {p.id for p in entry.projects}
    year = entry.report.year if entry.report is not None else None
    results: list[dict] = []
    created_any = False
    affected: set[int] = set()
    for index, (pfa_ids, parent_id, name) in enumerate(items):
        label = f"Item {index + 1}"
        error = None
        picked = [rows.get(pid) for pid in pfa_ids]
        if not pfa_ids:
            error = "Keine PFA-Zeilen angegeben."
        elif any(p is None for p in picked):
            missing = [pid for pid, p in zip(pfa_ids, picked) if p is None]
            error = f"PFA-Zeilen {missing} gehören nicht zu Eintrag {entry_id}."
        elif parent_id not in allowed:
            error = (
                f"Projekt {parent_id} ist weder Projekt des Eintrags noch liegt es darunter."
            )
        elif any(p.project_id is not None for p in picked):
            taken = [p.id for p in picked if p.project_id is not None]
            error = f"PFA-Zeilen {taken} sind schon zugeordnet — erst mit assign_vib_pfa lösen."
        if error is not None:
            results.append({"item": label, "ok": False, "error": error})
            continue
        parent = db.get(Project, parent_id)
        was_leaf = (
            db.query(Project.id).filter(Project.superior_project_id == parent_id).first() is None
        )
        project = Project(
            name=((name or "").strip() or _default_subproject_name(picked))[:255],
            superior_project_id=parent_id,
            is_draft=True,
        )
        db.add(project)
        db.flush()
        create_changelog_for_create(
            db,
            project,
            {"name": project.name, "superior_project_id": parent_id, "is_draft": True},
            getattr(user, "id", None),
            getattr(user, "username", None),
        )
        if not created_any:
            affected |= _unconfirm(db, entry)
            created_any = True
        for pfa in picked:
            pfa.project_id = project.id
        affected |= {parent_id}
        result = {
            "item": label,
            "ok": True,
            "project_id": project.id,
            "name": project.name,
            "parent_id": parent_id,
            "pfa_ids": list(pfa_ids),
            "parent_was_leaf": was_leaf,
        }
        if was_leaf:
            result["warning"] = (
                f"„{parent.name}“ hatte bisher keine Teilprojekte: sein Stand ergibt sich jetzt "
                "nur noch aus der Spanne seiner Teilprojekte. Übrige PFA-Zeilen und eigene "
                f"Quellen des Projekts prüfen (Skill vib-import, Schritt 5; VIB {year})."
            )
        results.append(result)
    db.commit()
    recompute_for(db, affected)
    return results


def delete_entry(db: Session, entry_id: int) -> bool:
    entry = _load_entry(db, entry_id)
    if entry is None:
        return False
    affected = {p.id for p in entry.projects} | {
        pfa.project_id for pfa in entry.pfa_entries if pfa.project_id is not None
    }
    db.delete(entry)
    db.commit()
    recompute_for(db, affected)
    return True


def confirm_report(db: Session, report_id: int, entry_ids: list[int] | None = None) -> int:
    """Confirm open entries of a report that have at least one project.

    ``entry_ids`` limits the confirmation to these entries. Returns the count.
    """

    query = (
        db.query(VibEntry)
        .options(selectinload(VibEntry.projects), selectinload(VibEntry.pfa_entries))
        .filter(VibEntry.vib_report_id == report_id, VibEntry.confirmed.is_(False))
    )
    if entry_ids is not None:
        query = query.filter(VibEntry.id.in_(entry_ids))
    affected: set[int] = set()
    count = 0
    for entry in query.all():
        if not entry.projects:
            continue
        entry.confirmed = True
        affected.update(p.id for p in entry.projects)
        affected.update(pfa.project_id for pfa in entry.pfa_entries if pfa.project_id is not None)
        count += 1
    db.commit()
    recompute_for(db, affected)
    return count
