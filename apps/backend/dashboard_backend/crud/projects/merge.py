"""Merge two projects: the *survivor* absorbs the *merged* project, which is deleted.

See docs/features/feature-project-merge.md for the rules. In short:

- Project fields: the survivor wins, its empty fields are filled from the merged
  project, property flags are OR-ed.
- Geometry (with length, bound operational points/sections and stored routes)
  comes from one side only (``geometry_from``).
- Every table with a foreign key to ``project.id`` is re-pointed to the survivor.
  The tables are found through the metadata, so a new link table is covered
  without touching this module; rows that would then violate a unique key (the
  same group on both projects, …) are dropped instead. A few tables need their
  own rule (``_SPECIAL_TABLES``).
- A ``project_redirect`` row keeps ``/projects/<merged id>`` working, and a MERGE
  changelog entry records the field changes on the survivor.

``merge_projects(..., apply=False)`` only reads and returns the plan; with
``apply=True`` it executes the same plan and commits.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import Boolean, Column, Table, delete, inspect, select, update
from sqlalchemy.orm import Session

from dashboard_backend.crud.changelog import diff_to_entries
from dashboard_backend.crud.projects import progress as progress_crud
from dashboard_backend.crud.projects.projects import (
    ProjectHierarchyError,
    ancestor_ids,
    get_project_by_id,
    has_subprojects,
    recompute_geojson_for_parent,
    validate_superior_project,
)
from dashboard_backend.models.base import Base
from dashboard_backend.models.change_tracking import ChangeLog, ChangeLogEntry
from dashboard_backend.models.projects.bvwp_project_data import BvwpProjectData
from dashboard_backend.models.projects.progress_observation import ProgressObservation
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.models.projects.project_redirect import ProjectRedirect
from dashboard_backend.models.routes.route import Route
from dashboard_backend.services.constituency_matching import recompute_links_for_project_ids

GeometrySource = Literal["survivor", "merged"]

# Project columns the merge never copies from the merged project. Geometry and
# length follow ``geometry_from``; the superior project is checked separately.
_KEEP_FIELDS = {
    "id",
    "name",
    "is_draft",
    "is_archived",
    "archived_reason",
    "archived_at",
    "old_id",
    "superior_project_old_id",
    "geojson_from_subprojects",
    "geojson_representation",
    "length",
    "superior_project_id",
}

# Editorial progress fields filled from the merged project when empty on the
# survivor. ``has_planfeststellung`` is OR-ed; the computed fields are rebuilt.
_PROGRESS_FILL_FIELDS = (
    "parl_befassung_relevant",
    "parl_befassung_text",
    "parl_drucksache_url",
    "parl_befassung_date",
    "pf_text",
    "pf_date",
    "pf_links",
    "pf_state_override",
    "parl_state_override",
)

# Tables with their own rule (see _special_* below); every other foreign key to
# project.id goes through the generic re-pointing.
_GEOMETRY_LINK_TABLES = ("project_to_operation_point", "project_to_section_of_line")
_SPECIAL_TABLES = {
    "project_progress",
    "progress_observation",
    "bvwp_project_data",
    "project_to_constituency",
    *_GEOMETRY_LINK_TABLES,
}

# Uniqueness the metadata cannot express portably: finve_to_project has two
# partial unique indexes (permanent link / per Haushalt year), i.e. one link
# per (finve, year) with NULL as its own value.
_EXTRA_UNIQUE_KEYS: dict[str, list[tuple[str, ...]]] = {
    "finve_to_project": [("project_id", "finve_id", "haushalt_year")],
}


class MergeError(ValueError):
    """The merge is not possible; the message is user-facing (German)."""


@dataclass
class _LinkPlan:
    table: Table
    column: Column
    move_keys: list[dict[str, Any]] = field(default_factory=list)
    drop_keys: list[dict[str, Any]] = field(default_factory=list)


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _summary(project: Project) -> dict[str, Any]:
    return {"id": project.id, "name": project.name, "project_number": project.project_number}


def _existing_tables(db: Session) -> set[str]:
    return set(inspect(db.get_bind()).get_table_names())


def _project_fk_columns(existing: set[str]) -> list[Column]:
    """Every column referencing project.id, in tables that exist in this database."""
    project_table = Project.__table__
    columns = []
    for table in Base.metadata.sorted_tables:
        if table.name not in existing or table.name in _SPECIAL_TABLES:
            continue
        for fk in table.foreign_keys:
            if fk.column.table is project_table and fk.column.name == "id":
                columns.append(fk.parent)
    return columns


def _unique_keys(table: Table, column: Column) -> list[tuple[str, ...]]:
    """Unique column sets of *table* that contain *column* (partial indexes excluded)."""
    keys: list[tuple[str, ...]] = []
    pk = tuple(c.name for c in table.primary_key.columns)
    if column.name in pk:
        keys.append(pk)
    for constraint in table.constraints:
        cols = tuple(c.name for c in getattr(constraint, "columns", ()))
        if constraint.__class__.__name__ == "UniqueConstraint" and column.name in cols:
            keys.append(cols)
    for index in table.indexes:
        if not index.unique or index.dialect_options["postgresql"].get("where") is not None:
            continue
        cols = tuple(c.name for c in index.columns)
        if column.name in cols:
            keys.append(cols)
    keys.extend(k for k in _EXTRA_UNIQUE_KEYS.get(table.name, []) if column.name in k)
    return keys


def _row_key(table: Table, row: Any) -> dict[str, Any]:
    """Identify one row: its primary key, or the full row if the table has none."""
    pk_cols = list(table.primary_key.columns) or list(table.columns)
    return {c.name: row._mapping[c.name] for c in pk_cols}


def _where(table: Table, key: dict[str, Any]):
    clauses = [
        table.c[name].is_(None) if value is None else table.c[name] == value
        for name, value in key.items()
    ]
    return clauses


def _plan_link(db: Session, column: Column, survivor_id: int, merged_id: int) -> _LinkPlan:
    table = column.table
    plan = _LinkPlan(table=table, column=column)
    merged_rows = db.execute(select(table).where(column == merged_id)).all()
    if not merged_rows:
        return plan
    keys = _unique_keys(table, column)
    taken: dict[tuple[str, ...], set[tuple]] = {}
    if keys:
        survivor_rows = db.execute(select(table).where(column == survivor_id)).all()
        for key in keys:
            others = [c for c in key if c != column.name]
            taken[key] = {tuple(r._mapping[c] for c in others) for r in survivor_rows}
    for row in merged_rows:
        duplicate = any(
            tuple(row._mapping[c] for c in key if c != column.name) in taken[key] for key in keys
        )
        (plan.drop_keys if duplicate else plan.move_keys).append(_row_key(table, row))
    return plan


def _execute_link(db: Session, plan: _LinkPlan, survivor_id: int) -> None:
    table, column = plan.table, plan.column
    for key in plan.drop_keys:
        db.execute(delete(table).where(*_where(table, key)))
    for key in plan.move_keys:
        db.execute(update(table).where(*_where(table, key)).values({column.name: survivor_id}))


def _check_hierarchy(db: Session, survivor: Project, merged: Project) -> None:
    def parent_of(pid: int) -> int | None:
        return db.query(Project.superior_project_id).filter(Project.id == pid).scalar()

    if merged.id in ancestor_ids(survivor.id, parent_of):
        raise MergeError(
            f"Projekt {merged.id} ist ein übergeordnetes Projekt von {survivor.id}. "
            "Erst die Hierarchie auflösen, dann zusammenführen."
        )
    if survivor.id in ancestor_ids(merged.id, parent_of):
        raise MergeError(
            f"Projekt {merged.id} ist ein Unterprojekt von {survivor.id}. "
            "Erst die Hierarchie auflösen, dann zusammenführen."
        )


def _plan_fields(
    db: Session, survivor: Project, merged: Project, geometry_from: GeometrySource
) -> tuple[dict[str, Any], list[str]]:
    """New values for the survivor's columns (only those that change) + warnings."""
    changes: dict[str, Any] = {}
    warnings: list[str] = []
    for column in Project.__table__.columns:
        name = column.name
        if name in _KEEP_FIELDS:
            continue
        current, other = getattr(survivor, name), getattr(merged, name)
        if isinstance(column.type, Boolean):
            new = True if (current or other) else current
        else:
            new = other if _is_empty(current) and not _is_empty(other) else current
        if new != current:
            changes[name] = new

    if geometry_from == "merged":
        for name in ("geojson_representation", "length"):
            if getattr(merged, name) != getattr(survivor, name):
                changes[name] = getattr(merged, name)

    if survivor.superior_project_id is None and merged.superior_project_id is not None:
        try:
            validate_superior_project(db, survivor.id, merged.superior_project_id)
            changes["superior_project_id"] = merged.superior_project_id
        except ProjectHierarchyError as exc:
            warnings.append(f"Übergeordnetes Projekt nicht übernommen: {exc}")
    elif (
        merged.superior_project_id is not None
        and merged.superior_project_id != survivor.superior_project_id
    ):
        warnings.append(
            f"Das verworfene Projekt hing unter Projekt {merged.superior_project_id}, "
            f"das bleibende bleibt unter {survivor.superior_project_id}."
        )
    return changes, warnings


def _plan_progress(db: Session, survivor_id: int, merged_id: int) -> dict[str, Any]:
    """Editorial progress fields the survivor takes over."""
    rows = {
        p.project_id: p
        for p in db.query(ProjectProgress)
        .filter(ProjectProgress.project_id.in_([survivor_id, merged_id]))
        .all()
    }
    mine, other = rows.get(survivor_id), rows.get(merged_id)
    if other is None:
        return {}
    if mine is None:
        return {"move_row": True}
    fills: dict[str, Any] = {}
    if other.has_planfeststellung and not mine.has_planfeststellung:
        fills["has_planfeststellung"] = True
    if mine.manual_phase_override is None and other.manual_phase_override is not None:
        fills["manual_phase_override"] = other.manual_phase_override
        fills["manual_override_note"] = other.manual_override_note
    for name in _PROGRESS_FILL_FIELDS:
        if _is_empty(getattr(mine, name)) and not _is_empty(getattr(other, name)):
            fills[name] = getattr(other, name)
    return fills


def merge_projects(
    db: Session,
    survivor_id: int,
    merged_id: int,
    *,
    geometry_from: GeometrySource = "survivor",
    apply: bool = False,
    user_id: int | None = None,
    username: str | None = None,
) -> dict[str, Any]:
    """Plan (``apply=False``) or execute the merge of *merged_id* into *survivor_id*.

    Returns the plan: survivor/merged summaries, effective geometry source,
    field changes, per-table link counts, moved subprojects and warnings.
    Raises MergeError if the merge is not possible.
    """
    if survivor_id == merged_id:
        raise MergeError("Ein Projekt kann nicht mit sich selbst zusammengeführt werden.")
    survivor = get_project_by_id(db, survivor_id)
    merged = get_project_by_id(db, merged_id)
    for pid, project in ((survivor_id, survivor), (merged_id, merged)):
        if project is None:
            raise MergeError(f"Projekt {pid} nicht gefunden.")
    _check_hierarchy(db, survivor, merged)

    warnings: list[str] = []
    if not survivor.geojson_representation and merged.geojson_representation:
        if geometry_from == "survivor":
            warnings.append("Das bleibende Projekt hat keine Geometrie — sie kommt vom verworfenen.")
        geometry_from = "merged"

    field_changes, field_warnings = _plan_fields(db, survivor, merged, geometry_from)
    warnings += field_warnings
    progress_fills = _plan_progress(db, survivor_id, merged_id)

    existing = _existing_tables(db)
    link_plans = [
        _plan_link(db, column, survivor_id, merged_id) for column in _project_fk_columns(existing)
    ]
    links: dict[str, dict[str, int]] = defaultdict(lambda: {"moved": 0, "dropped": 0})
    for plan in link_plans:
        if plan.move_keys or plan.drop_keys:
            label = (
                plan.table.name
                if plan.column.name == "project_id"
                else f"{plan.table.name}.{plan.column.name}"
            )
            links[label]["moved"] += len(plan.move_keys)
            links[label]["dropped"] += len(plan.drop_keys)
    children = sorted(
        pid for (pid,) in db.query(Project.id).filter(Project.superior_project_id == merged_id)
    )
    if children and survivor.geojson_from_subprojects:
        warnings.append(
            "Unterprojekte wandern mit — die Geometrie des bleibenden Projekts wird danach "
            "aus seinen Unterprojekten zusammengesetzt."
        )

    # Special tables, counted the way they will be executed.
    loser_side, winner_side = (
        (merged_id, survivor_id) if geometry_from == "survivor" else (survivor_id, merged_id)
    )
    for name in _GEOMETRY_LINK_TABLES:
        if name not in existing:
            continue
        table = Base.metadata.tables[name]
        dropped = len(db.execute(select(table).where(table.c.project_id == loser_side)).all())
        moved = (
            len(db.execute(select(table).where(table.c.project_id == merged_id)).all())
            if winner_side == merged_id
            else 0
        )
        if moved or dropped:
            links[name] = {"moved": moved, "dropped": dropped}
    observations = (
        db.query(ProgressObservation).filter(ProgressObservation.project_id == merged_id).all()
        if "progress_observation" in existing
        else []
    )
    derived = sum(1 for o in observations if o.is_derived)
    if observations:
        links["progress_observation"] = {"moved": len(observations) - derived, "dropped": derived}
    has_bvwp_merged = (
        "bvwp_project_data" in existing
        and db.query(BvwpProjectData).filter(BvwpProjectData.project_id == merged_id).count() > 0
    )
    has_bvwp_survivor = (
        "bvwp_project_data" in existing
        and db.query(BvwpProjectData).filter(BvwpProjectData.project_id == survivor_id).count() > 0
    )
    if has_bvwp_merged:
        links["bvwp_project_data"] = (
            {"moved": 0, "dropped": 1} if has_bvwp_survivor else {"moved": 1, "dropped": 0}
        )

    result: dict[str, Any] = {
        "survivor": _summary(survivor),
        "merged": _summary(merged),
        "geometry_from": geometry_from,
        "field_changes": {
            name: {"old": getattr(survivor, name), "new": value}
            for name, value in field_changes.items()
            if name != "geojson_representation"
        },
        "geometry_changed": "geojson_representation" in field_changes,
        "progress_changes": sorted(progress_fills),
        "links": dict(sorted(links.items())),
        "subprojects_moved": children,
        "warnings": warnings,
        "applied": False,
    }
    if not apply:
        return result

    _apply(
        db,
        survivor,
        merged,
        geometry_from=geometry_from,
        field_changes=field_changes,
        progress_fills=progress_fills,
        link_plans=link_plans,
        existing=existing,
        has_bvwp_survivor=has_bvwp_survivor,
        user_id=user_id,
        username=username,
    )
    result["applied"] = True
    return result


def _apply(
    db: Session,
    survivor: Project,
    merged: Project,
    *,
    geometry_from: GeometrySource,
    field_changes: dict[str, Any],
    progress_fills: dict[str, Any],
    link_plans: list[_LinkPlan],
    existing: set[str],
    has_bvwp_survivor: bool,
    user_id: int | None,
    username: str | None,
) -> None:
    survivor_id, merged_id = survivor.id, merged.id
    merged_name = merged.name
    old_parent_of_merged = merged.superior_project_id

    # 1. Changelog entry for the field changes (diffed before they are applied).
    entries = diff_to_entries(ChangeLogEntry, survivor, field_changes)
    entries.append(
        ChangeLogEntry(
            field_name="merged_project",
            old_value=None,
            new_value=json.dumps({"id": merged_id, "name": merged_name}),
        )
    )
    db.add(
        ChangeLog(
            project_id=survivor_id,
            user_id=user_id,
            username_snapshot=username,
            timestamp=datetime.utcnow(),
            action="MERGE",
            entries=entries,
        )
    )
    for name, value in field_changes.items():
        setattr(survivor, name, value)

    # 2. Planning-state row: fill the survivor's, or adopt the merged one.
    if progress_fills.get("move_row"):
        db.execute(
            update(ProjectProgress.__table__)
            .where(ProjectProgress.project_id == merged_id)
            .values(project_id=survivor_id)
        )
    elif progress_fills:
        mine = db.query(ProjectProgress).filter(ProjectProgress.project_id == survivor_id).one()
        for name, value in progress_fills.items():
            setattr(mine, name, value)
    db.flush()

    # 3. Geometry-bound links and stored routes: keep one side.
    loser_side = merged_id if geometry_from == "survivor" else survivor_id
    for name in _GEOMETRY_LINK_TABLES:
        if name in existing:
            table = Base.metadata.tables[name]
            db.execute(delete(table).where(table.c.project_id == loser_side))
            db.execute(
                update(table).where(table.c.project_id == merged_id).values(project_id=survivor_id)
            )
    if "routes" in existing:
        db.execute(delete(Route.__table__).where(Route.project_id == loser_side))
        db.execute(
            update(Route.__table__).where(Route.project_id == merged_id).values(project_id=survivor_id)
        )

    # 4. Tables with a fixed rule.
    if "project_to_constituency" in existing:
        table = Base.metadata.tables["project_to_constituency"]
        db.execute(delete(table).where(table.c.project_id == merged_id))
    if "progress_observation" in existing:
        obs = ProgressObservation.__table__
        db.execute(delete(obs).where(obs.c.project_id == merged_id, obs.c.is_derived.is_(True)))
        db.execute(update(obs).where(obs.c.project_id == merged_id).values(project_id=survivor_id))
    if "bvwp_project_data" in existing:
        bvwp = BvwpProjectData.__table__
        if has_bvwp_survivor:
            db.execute(delete(bvwp).where(bvwp.c.project_id == merged_id))
        else:
            db.execute(update(bvwp).where(bvwp.c.project_id == merged_id).values(project_id=survivor_id))
    if "project_progress" in existing:
        db.execute(
            delete(ProjectProgress.__table__).where(ProjectProgress.project_id == merged_id)
        )

    # 5. Everything else that points at the merged project (incl. subprojects,
    #    changelog, redirects that targeted it).
    for plan in link_plans:
        _execute_link(db, plan, survivor_id)

    # 6. Delete the merged project and leave a redirect behind.
    db.expunge(merged)
    db.execute(delete(Project.__table__).where(Project.id == merged_id))
    db.add(
        ProjectRedirect(
            old_project_id=merged_id,
            new_project_id=survivor_id,
            old_name=merged_name,
            merged_at=datetime.utcnow(),
            merged_by_user_id=user_id,
        )
    )
    db.commit()
    db.expire_all()

    # 7. Rebuild what is derived from the merged data.
    progress_crud.sync_derived_observations(db, survivor_id)
    progress_crud.recompute_progress(db, survivor_id)
    survivor = get_project_by_id(db, survivor_id)
    if survivor.geojson_from_subprojects and has_subprojects(db, survivor_id):
        recompute_geojson_for_parent(db, survivor_id)
    else:
        recompute_links_for_project_ids(db, [survivor_id])
        recompute_geojson_for_parent(db, survivor.superior_project_id)
    if old_parent_of_merged not in (None, survivor.superior_project_id):
        recompute_geojson_for_parent(db, old_parent_of_merged)
    db.commit()


def resolve_redirect(db: Session, project_id: int) -> int | None:
    """The project an old (merged) id now points to, or None."""
    return (
        db.query(ProjectRedirect.new_project_id)
        .filter(ProjectRedirect.old_project_id == project_id)
        .scalar()
    )
