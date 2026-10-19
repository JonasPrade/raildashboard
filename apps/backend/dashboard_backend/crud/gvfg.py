"""GVFG-Bundesprogramm: project suggestions, staging, confirm and reads.

See docs/features/feature-gvfg-import.md. Matching order for a Vorhaben:
1. projects already linked to the same key in an earlier edition,
2. projects whose ``project_number`` normalises to the key,
3. the same key without suffix ("…_T" vs. "…_A"),
4. name similarity (as for FinVes).
Several hits, a weak name match or a key/name conflict are flagged for review.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from dashboard_backend.crud.changelog import create_changelog_for_create, create_changelog_for_patch
from dashboard_backend.models.gvfg import (
    GvfgEntry,
    GvfgEntryAmount,
    GvfgParseResult,
    GvfgProgram,
    gvfg_entry_project,
)
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.services.gvfg_parser import key_without_suffix, normalize_key
from dashboard_backend.tasks.finve_matching import _score as name_score

GVFG_GROUP = "GVFG"
GVFG_BW_GROUP = "GVFG BW"
BW_LAND_CODE = "08"

_NAME_THRESHOLD = 0.45
_MAX_NAME_SUGGESTIONS = 3


class GvfgConfirmError(ValueError):
    """Confirm not possible; the message is user-facing (German)."""


# --- Suggestions -------------------------------------------------------------


@dataclass
class _ProjectRef:
    id: int
    name: str
    project_number: str | None
    is_draft: bool


def _project_index(db: Session) -> tuple[dict[str, list[_ProjectRef]], list[_ProjectRef]]:
    by_key: dict[str, list[_ProjectRef]] = defaultdict(list)
    refs = []
    for pid, name, number, draft in db.execute(
        select(Project.id, Project.name, Project.project_number, Project.is_draft)
    ):
        ref = _ProjectRef(pid, name, number, bool(draft))
        refs.append(ref)
        key = normalize_key(number)
        if key:
            by_key[key].append(ref)
    return by_key, refs


def _previous_links(db: Session) -> dict[str, list[int]]:
    """Key → projects linked in the newest earlier edition that has links for it."""
    rows = db.execute(
        select(GvfgEntry.key, GvfgProgram.year_from, gvfg_entry_project.c.project_id)
        .join(GvfgProgram, GvfgProgram.id == GvfgEntry.program_id)
        .join(gvfg_entry_project, gvfg_entry_project.c.entry_id == GvfgEntry.id)
    ).all()
    newest: dict[str, int] = {}
    links: dict[str, list[int]] = defaultdict(list)
    for key, year, project_id in sorted(rows, key=lambda r: -r[1]):
        if newest.setdefault(key, year) == year and project_id not in links[key]:
            links[key].append(project_id)
    return links


def build_suggestions(db: Session, entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Suggestions per key for the review page, plus the referenced projects.

    Returns {"by_key": {key: {"selected": [ids], "source": str, "candidates":
    [{"id", "score", "reason"}], "flags": [str]}}, "projects": {id: {...}}}.
    """
    by_key, refs = _project_index(db)
    previous = _previous_links(db)
    by_base: dict[str, list[_ProjectRef]] = defaultdict(list)
    for key, projects in by_key.items():
        by_base[key_without_suffix(key)].extend(projects)
    lookup = {ref.id: ref for ref in refs}
    out: dict[str, Any] = {}
    used: set[int] = set()

    for entry in entries:
        key, name = entry["key"], entry.get("name") or ""
        candidates: list[dict[str, Any]] = []
        flags: list[str] = []
        source = "none"
        selected: list[int] = []

        if previous.get(key):
            selected = [pid for pid in previous[key] if pid in lookup]
            source = "previous"
        exact = by_key.get(key, [])
        for ref in exact:
            candidates.append({"id": ref.id, "score": 1.0, "reason": "key"})
        if not selected and exact:
            selected = [ref.id for ref in exact if not ref.is_draft] or [exact[0].id]
            source = "key"
            if len(exact) > 1:
                flags.append("mehrere Projekte mit diesem Schlüssel")
        if not exact:
            for ref in by_base.get(key_without_suffix(key), []):
                candidates.append({"id": ref.id, "score": 0.9, "reason": "key_without_suffix"})
            if not selected and candidates:
                selected = [candidates[0]["id"]]
                source = "key_without_suffix"
                flags.append("Schlüssel stimmt nur ohne Suffix überein")
        if name:
            scored = sorted(
                ((name_score(name, ref.name), ref) for ref in refs if ref.id not in {c["id"] for c in candidates}),
                key=lambda pair: -pair[0],
            )[:_MAX_NAME_SUGGESTIONS]
            for score, ref in scored:
                if score >= _NAME_THRESHOLD:
                    candidates.append({"id": ref.id, "score": round(score, 2), "reason": "name"})
        if selected and name:
            best = max((name_score(name, lookup[pid].name) for pid in selected), default=0.0)
            if best < _NAME_THRESHOLD:
                flags.append("Name weicht stark ab")
        if not selected:
            flags.append("kein Projekt gefunden")
        used.update(selected)
        used.update(c["id"] for c in candidates)
        out[key] = {"selected": selected, "source": source, "candidates": candidates, "flags": flags}

    projects = {
        str(pid): {
            "id": pid,
            "name": lookup[pid].name,
            "project_number": lookup[pid].project_number,
            "is_draft": lookup[pid].is_draft,
        }
        for pid in sorted(used)
        if pid in lookup
    }
    return {"by_key": out, "projects": projects}


# --- Parse results -----------------------------------------------------------


def save_parse_result(
    db: Session,
    *,
    filename: str,
    result_json: dict[str, Any] | None,
    status: str,
    error: str | None,
    user_info: dict | None,
) -> GvfgParseResult:
    record = GvfgParseResult(
        pdf_filename=filename,
        year_from=(result_json or {}).get("year_from"),
        year_to=(result_json or {}).get("year_to"),
        is_annex=bool((result_json or {}).get("is_annex")),
        status=status,
        result_json=result_json,
        error_message=error,
        parsed_by_user_id=(user_info or {}).get("id"),
        username_snapshot=(user_info or {}).get("username"),
    )
    db.add(record)
    db.flush()
    return record


def list_parse_results(db: Session) -> list[GvfgParseResult]:
    return db.query(GvfgParseResult).order_by(GvfgParseResult.parsed_at.desc()).all()


def get_parse_result(db: Session, parse_result_id: int) -> GvfgParseResult | None:
    return db.get(GvfgParseResult, parse_result_id)


# --- Confirm -----------------------------------------------------------------


def _decimal(value: Any) -> Decimal | None:
    return None if value in (None, "") else Decimal(str(value))


def _stand(text: str | None) -> date | None:
    if not text:
        return None
    try:
        return datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        return None


def _merge_periods(existing: list[dict], new: list[dict]) -> list[dict]:
    labels = {p["label"] for p in existing}
    merged = list(existing) + [p for p in new if p["label"] not in labels]
    return sorted(merged, key=lambda p: (p.get("year_from") or 0, p.get("kind") != "ausgezahlt"))


def _groups(db: Session) -> dict[str, ProjectGroup]:
    return {
        g.short_name: g
        for g in db.query(ProjectGroup).filter(ProjectGroup.short_name.in_([GVFG_GROUP, GVFG_BW_GROUP]))
    }


def _ensure_groups(
    db: Session, project: Project, key: str, groups: dict[str, ProjectGroup], user: Any
) -> bool:
    wanted = [groups[GVFG_GROUP]] if GVFG_GROUP in groups else []
    if key.startswith(BW_LAND_CODE) and GVFG_BW_GROUP in groups:
        wanted.append(groups[GVFG_BW_GROUP])
    current = {g.id for g in project.project_groups}
    missing = [g.id for g in wanted if g.id not in current]
    if not missing:
        return False
    update_data = {"project_group_ids": sorted(current | set(missing))}
    create_changelog_for_patch(db, project, update_data, user.id, user.username)
    # Set directly instead of update_project(): that commits, and the confirm
    # must stay one transaction.
    project.project_groups = list(project.project_groups) + [g for g in wanted if g.id in missing]
    return True


def confirm_parse_result(
    db: Session,
    record: GvfgParseResult,
    *,
    assignments: dict[str, list[int]],
    create_projects: Iterable[str],
    user: Any,
) -> dict[str, int]:
    """Write a reviewed parse result into its edition.

    The entries of the parts contained in the result (finanzrelevant and/or
    nachrichtlich) replace those of the edition; an annex only replaces the
    informational part. ``assignments`` maps keys to project ids, keys in
    ``create_projects`` get a new project. Projects are added to the GVFG group
    (and "GVFG BW" for Land 08), never removed from it.
    """
    if record.status != "SUCCESS" or not record.result_json:
        raise GvfgConfirmError("Dieser Lauf hat kein verwertbares Ergebnis.")
    if record.confirmed_at is not None:
        raise GvfgConfirmError("Dieser Lauf wurde bereits übernommen.")
    result = record.result_json
    entries: list[dict[str, Any]] = result["entries"]
    keys = {e["key"] for e in entries}
    unknown = sorted((set(assignments) | set(create_projects)) - keys)
    if unknown:
        raise GvfgConfirmError(f"Unbekannte Schlüssel: {', '.join(unknown)}")
    wanted_ids = {pid for ids in assignments.values() for pid in ids}
    projects = {p.id: p for p in db.query(Project).filter(Project.id.in_(wanted_ids))} if wanted_ids else {}
    missing = sorted(wanted_ids - set(projects))
    if missing:
        raise GvfgConfirmError(f"Projekte nicht gefunden: {', '.join(map(str, missing))}")

    parts = {e["part"] for e in entries}
    program = db.query(GvfgProgram).filter(GvfgProgram.year_from == result["year_from"]).one_or_none()
    if program is not None:
        clash = (
            db.query(GvfgEntry.key)
            .filter(
                GvfgEntry.program_id == program.id,
                GvfgEntry.part.not_in(parts),
                GvfgEntry.key.in_(keys),
            )
            .all()
        )
        if clash:
            raise GvfgConfirmError(
                "Schlüssel stehen schon im anderen Teil dieser Ausgabe: "
                + ", ".join(sorted(k for (k,) in clash))
            )

    # Everything above only reads; from here on the edition is written.
    if program is None:
        program = GvfgProgram(
            year_from=result["year_from"],
            year_to=result["year_to"],
            title=result.get("title") or f"GVFG-Bundesprogramm {result['year_from']}–{result['year_to']}",
            stand=_stand(result.get("stand")),
            periods=[],
        )
        db.add(program)
        db.flush()
    elif not result.get("is_annex"):
        program.stand = _stand(result.get("stand")) or program.stand
    program.periods = _merge_periods(program.periods or [], result.get("periods") or [])
    if result.get("is_annex"):
        program.has_annex = True
    program.imported_at = datetime.utcnow()

    for old in db.query(GvfgEntry).filter(GvfgEntry.program_id == program.id, GvfgEntry.part.in_(parts)):
        db.delete(old)
    db.flush()

    groups = _groups(db)
    to_create = set(create_projects)
    stats = {"entries": 0, "links": 0, "projects_created": 0, "groups_added": 0}
    for data in entries:
        entry = GvfgEntry(
            program_id=program.id,
            key=data["key"],
            key_raw=data["key_raw"],
            land=data["land"],
            kind=data["kind"],
            part=data["part"],
            nr=data.get("nr"),
            city=data.get("city"),
            name=data.get("name"),
            lph=data.get("lph"),
            funding_type=data.get("funding_type"),
            funding_rate=data.get("funding_rate"),
            start_year=data.get("start_year"),
            construction_start=data.get("construction_start"),
            commissioning_planned=data.get("commissioning_planned"),
            commissioning_actual=data.get("commissioning_actual"),
            page=data.get("page"),
        )
        for line_no, line in enumerate(data.get("amounts") or []):
            entry.amounts.append(
                GvfgEntryAmount(
                    line_no=line_no,
                    category=line["category"],
                    computed=bool(line.get("computed")),
                    cost_total=_decimal(line.get("cost_total")),
                    cost_eligible=_decimal(line.get("cost_eligible")),
                    aid_total=_decimal(line.get("aid_total")),
                    periods={k: str(v) for k, v in (line.get("periods") or {}).items()},
                )
            )
        db.add(entry)
        stats["entries"] += 1

        linked: list[Project] = [projects[pid] for pid in assignments.get(data["key"], [])]
        if data["key"] in to_create:
            created = Project(
                name=data.get("name") or data["key"], project_number=data["key"], is_draft=False
            )
            db.add(created)
            db.flush()
            create_changelog_for_create(
                db, created, {"name": created.name, "project_number": created.project_number},
                user.id, user.username,
            )
            linked.append(created)
            stats["projects_created"] += 1
        for project in linked:
            if project not in entry.projects:
                entry.projects.append(project)
                stats["links"] += 1
            if _ensure_groups(db, project, data["key"], groups, user):
                stats["groups_added"] += 1

    record.confirmed_at = datetime.utcnow()
    record.confirmed_by_snapshot = user.username
    db.commit()
    return stats


# --- Reads -------------------------------------------------------------------


def list_programs(db: Session) -> list[GvfgProgram]:
    return db.query(GvfgProgram).order_by(GvfgProgram.year_from.desc()).all()


def get_program(db: Session, program_id: int) -> GvfgProgram | None:
    return db.get(GvfgProgram, program_id)


def program_entries(db: Session, program_id: int) -> list[GvfgEntry]:
    return (
        db.query(GvfgEntry)
        .filter(GvfgEntry.program_id == program_id)
        .options(selectinload(GvfgEntry.amounts), selectinload(GvfgEntry.projects))
        .order_by(GvfgEntry.land, GvfgEntry.kind, GvfgEntry.part, GvfgEntry.key)
        .all()
    )


def project_entries(db: Session, project_id: int, with_subprojects: bool = False) -> list[GvfgEntry]:
    """GVFG entries linked to a project (and, optionally, to its direct
    subprojects — a parent shows them as "Förderung in Teilprojekten"),
    newest edition first."""
    ids = [project_id]
    if with_subprojects:
        ids += [pid for (pid,) in db.query(Project.id).filter(Project.superior_project_id == project_id)]
    rows = (
        db.query(GvfgEntry)
        .join(gvfg_entry_project, gvfg_entry_project.c.entry_id == GvfgEntry.id)
        .join(GvfgProgram, GvfgProgram.id == GvfgEntry.program_id)
        .filter(gvfg_entry_project.c.project_id.in_(ids))
        .options(
            selectinload(GvfgEntry.amounts),
            selectinload(GvfgEntry.program),
            selectinload(GvfgEntry.projects),
        )
        .order_by(GvfgProgram.year_from.desc(), GvfgEntry.key)
        .all()
    )
    # An entry linked to the parent and a child comes back twice; no DISTINCT
    # because Postgres wants ORDER BY columns in a DISTINCT select list.
    return list(dict.fromkeys(rows))


def unassigned_entries(db: Session) -> list[GvfgEntry]:
    """Entries of the newest edition without any project."""
    newest = db.query(GvfgProgram).order_by(GvfgProgram.year_from.desc()).first()
    if newest is None:
        return []
    linked = select(gvfg_entry_project.c.entry_id)
    return (
        db.query(GvfgEntry)
        .filter(GvfgEntry.program_id == newest.id, GvfgEntry.id.not_in(linked))
        .options(selectinload(GvfgEntry.amounts), selectinload(GvfgEntry.projects))
        .order_by(GvfgEntry.land, GvfgEntry.key)
        .all()
    )


def assign_entry(db: Session, entry: GvfgEntry, project_ids: list[int], user: Any) -> None:
    """Link an entry to projects (from "Offene Zuordnungen"); like the
    confirm, the projects get the GVFG group(s) — added, never removed."""
    projects = db.query(Project).filter(Project.id.in_(project_ids)).all()
    missing = set(project_ids) - {p.id for p in projects}
    if missing:
        raise GvfgConfirmError(f"Unbekannte Projekte: {sorted(missing)}")
    groups = _groups(db)
    for project in projects:
        if project not in entry.projects:
            entry.projects.append(project)
        _ensure_groups(db, project, entry.key, groups, user)
    db.commit()


def entries_with_key(db: Session, key: str) -> list[GvfgEntry]:
    """The entries of one key across all editions, newest first."""
    return (
        db.query(GvfgEntry)
        .join(GvfgProgram, GvfgProgram.id == GvfgEntry.program_id)
        .filter(GvfgEntry.key == key)
        .options(
            selectinload(GvfgEntry.amounts),
            selectinload(GvfgEntry.program),
            selectinload(GvfgEntry.projects),
        )
        .order_by(GvfgProgram.year_from.desc())
        .all()
    )


def set_entry_projects(
    db: Session, entries: list[GvfgEntry], project_ids: list[int], user: Any
) -> None:
    """Replace the projects of the entries (MCP correction of wrong links).
    New projects get the GVFG group(s); groups are never removed, even from a
    project that loses its link. An empty list removes every link."""
    projects = db.query(Project).filter(Project.id.in_(project_ids)).all() if project_ids else []
    missing = set(project_ids) - {p.id for p in projects}
    if missing:
        raise GvfgConfirmError(f"Unbekannte Projekte: {sorted(missing)}")
    groups = _groups(db)
    for entry in entries:
        entry.projects = list(projects)
        for project in projects:
            _ensure_groups(db, project, entry.key, groups, user)
    db.commit()
