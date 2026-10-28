"""Project, planning-state, financing and text tools.

Outputs stay compact on purpose: every answer lands in the client's context
window, so lists are paginated and geometries (``geojson_representation``,
``centroid``) are never returned.
"""

from __future__ import annotations

import calendar
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Literal, get_args

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import String, and_, cast, exists, func, not_, or_, select
from sqlalchemy.orm import Session, selectinload

from dashboard_backend.crud.changelog import (
    create_changelog_for_create,
    create_changelog_for_patch,
    create_text_changelog_for_create,
    create_text_changelog_for_patch,
)
from dashboard_backend.crud.finves import get_project_finves_with_budgets
from dashboard_backend.crud.projects import progress as progress_crud
from dashboard_backend.crud.projects.archive import (
    ArchiveError,
    archive_project as archive_project_crud,
    replacement as replacement_crud,
    unarchive_project as unarchive_project_crud,
)
from dashboard_backend.crud.projects.bvwp import get_bvwp_data
from dashboard_backend.crud.projects.merge import MergeError, resolve_redirect
from dashboard_backend.crud.projects.merge import merge_projects as merge_projects_crud
from dashboard_backend.crud.projects.projects import (
    ProjectHierarchyError,
    create_project as create_project_crud,
    get_project_by_id,
    get_subprojects,
    update_project as update_project_crud,
    validate_superior_project,
)
from dashboard_backend.crud.projects.project_groups import (
    create_project_group as create_project_group_crud,
)
from dashboard_backend.crud.projects.texts import (
    create_text_for_project,
    get_default_text_category,
    get_text_categories,
    get_text_category,
    get_text_types,
    get_texts_for_project,
    update_project_text,
)
from dashboard_backend.crud.projects.progress import BEDARFSPLAN_GROUP_SHORT_NAME_PREFIX
from dashboard_backend.mcp.context import get_principal, load_user, require, tool_session
from dashboard_backend.models.associations.project_to_project_group import ProjectToProjectGroup
from dashboard_backend.models.change_tracking import ChangeLog
from dashboard_backend.models.infraplan import (
    InfraplanEntry,
    InfraplanEntryProject,
    InfraplanReport,
)
from dashboard_backend.models.associations.text_to_project import TextToProject
from dashboard_backend.models.projects.project import Project
from dashboard_backend.models.projects.project_group import ProjectGroup
from dashboard_backend.models.projects.project_progress import ProjectProgress
from dashboard_backend.models.projects.project_text import ProjectText
from dashboard_backend.schemas.projects import ProjectGroupCreate, ProjectSchema
from dashboard_backend.schemas.projects.bvwp_schema import BvwpProjectDataSchema
from dashboard_backend.schemas.projects.progress_schema import (
    DatePrecisionLiteral,
    LifecycleStatusLiteral,
    MainPhaseLiteral,
    ManualSourceTypeLiteral,
    ProgressObservationCreate,
    ProgressObservationUpdate,
    ProjectProgressSchema,
    TrackLiteral,
)
from dashboard_backend.schemas.projects.project_create_schema import ProjectCreate
from dashboard_backend.schemas.projects.project_text_schema import ProjectTextSchema
from dashboard_backend.schemas.projects.project_update_schema import ProjectUpdate
from dashboard_backend.services.date_precision import date_text
from dashboard_backend.services.geo_length import compute_geojson_length_km

MAX_LIMIT = 200

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False)
DESTRUCTIVE = ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=False)

# Never sent to the client: geometry blobs are huge and useless as text.
_GEOMETRY_FIELDS = {"geojson_representation", "centroid"}
# Fields update_project may not touch: geometry (no meaningful text edit) and the
# draft flag (set_project_draft).
_READONLY_UPDATE_FIELDS = {"geojson_representation", "is_draft"}
# Changed through set_project_groups, which resolves names and keeps other groups.
_GROUP_FIELD = "project_group_ids"


def _project_or_error(db: Session, project_id: int) -> Project:
    project = get_project_by_id(db, project_id)
    if project is None:
        target = resolve_redirect(db, project_id)
        if target is not None:
            raise ToolError(
                f"Projekt {project_id} wurde mit Projekt {target} zusammengeführt — "
                f"bitte Projekt {target} verwenden."
            )
        raise ToolError(f"Projekt {project_id} nicht gefunden.")
    return project


def _project_dict(project: Project) -> dict[str, Any]:
    return ProjectSchema.model_validate(project).model_dump(mode="json", exclude=_GEOMETRY_FIELDS)


_SENTENCE_END = re.compile(r"(?<=[^\s.]{3}[.!?])\s")
_SHORT_DESCRIPTION = 200


def short_description(text: str | None) -> str | None:
    """First sentence of a description, at most 200 characters."""
    if not text or not text.strip():
        return None
    text = " ".join(text.split())
    first = _SENTENCE_END.split(text, maxsplit=1)[0]
    if len(first) > _SHORT_DESCRIPTION:
        first = first[: _SHORT_DESCRIPTION - 1].rstrip() + "…"
    return first


def _milestone_summary(value: date | None, precision: str | None) -> dict[str, Any] | None:
    """Cached forecast date for list output: sort value, precision, label."""
    if value is None:
        return None
    precision = precision or "EXACT"
    return {"date": value.isoformat(), "precision": precision, "text": date_text(value, precision)}


def _project_summary(
    project: Project,
    phase: str | None,
    is_known: bool | None = None,
    with_description: bool = False,
    milestones: tuple | None = None,
) -> dict[str, Any]:
    summary = {
        "id": project.id,
        "name": project.name,
        "project_number": project.project_number,
        "superior_project_id": project.superior_project_id,
        "project_groups": [g.short_name for g in project.project_groups],
        "phase": phase,
        "is_draft": bool(project.is_draft),
    }
    if is_known is not None:
        summary["is_known"] = is_known
    if milestones is not None:
        start_date, start_precision, ibn_date, ibn_precision = milestones
        summary["construction_start"] = _milestone_summary(start_date, start_precision)
        summary["commissioning"] = _milestone_summary(ibn_date, ibn_precision)
    if with_description:
        summary["short_description"] = short_description(project.description)
        summary["aliases"] = list(project.aliases or [])
    return summary


# --- SQL expressions over Project (outer-joined to ProjectProgress) ----------
# Shared by list_projects and the data-quality tools (mcp/tools/data_quality.py).


def effective_phase_expr():
    return func.coalesce(ProjectProgress.manual_phase_override, ProjectProgress.computed_phase)


def is_known_expr():
    """SQL twin of ``stored_headline_phase(...) is not None``: an override, or a
    computed phase that a credible observation decided (confidence > 0). The
    ``NICHT_GESTARTET``/0.0 fallback and a missing progress row are unknown."""
    return or_(
        ProjectProgress.manual_phase_override.isnot(None),
        and_(ProjectProgress.computed_phase.isnot(None), ProjectProgress.computed_confidence > 0),
    )


def has_geometry_expr():
    # An empty FeatureCollection carries no "coordinates" key.
    return and_(
        Project.geojson_representation.isnot(None),
        Project.geojson_representation.contains('"coordinates"'),
    )


def has_length_expr():
    return and_(Project.length.isnot(None), Project.length > 0)


def _bswag_member_expr():
    return exists().where(
        ProjectToProjectGroup.project_id == Project.id,
        ProjectToProjectGroup.project_group_id == ProjectGroup.id,
        func.upper(ProjectGroup.short_name).like(f"{BEDARFSPLAN_GROUP_SHORT_NAME_PREFIX}%"),
    )


def _infraplan_parl_exprs():
    """(has statement, statement says relevant) of the newest Infraplan year
    that states the Befassung for the project — twin of
    ``progress_crud.infraplan_parl_relevance``."""
    stated = and_(
        InfraplanEntryProject.project_id == Project.id,
        InfraplanEntryProject.entry_id == InfraplanEntry.id,
        InfraplanEntry.report_id == InfraplanReport.id,
        InfraplanEntry.parl_state.isnot(None),
    )
    newest_year = (
        select(func.max(InfraplanReport.year)).where(stated).correlate(Project).scalar_subquery()
    )
    relevant = exists().where(
        stated,
        InfraplanReport.year == newest_year,
        InfraplanEntry.parl_state != "NICHT_VEREINBART",
    )
    return newest_year.isnot(None), relevant


def parl_relevant_expr(relevant: bool):
    """SQL twin of ``resolve_parl_relevant``: the override wins, then the
    newest Infraplan statement, else BSWAG* groups."""
    override = ProjectProgress.parl_befassung_relevant
    member = _bswag_member_expr()
    has_infraplan, infraplan_relevant = _infraplan_parl_exprs()
    if relevant:
        default = or_(
            and_(has_infraplan, infraplan_relevant), and_(not_(has_infraplan), member)
        )
        return or_(override.is_(True), and_(override.is_(None), default))
    default = or_(
        and_(has_infraplan, not_(infraplan_relevant)), and_(not_(has_infraplan), not_(member))
    )
    return or_(override.is_(False), and_(override.is_(None), default))


def last_change_expr():
    return (
        select(func.max(ChangeLog.timestamp))
        .where(ChangeLog.project_id == Project.id)
        .correlate(Project)
        .scalar_subquery()
    )


def _text_dict(text: ProjectText, default_category: Any = None) -> dict[str, Any]:
    data = ProjectTextSchema.model_validate(text).model_dump(mode="json")
    data["text_type"] = data["text_type"]["name"]
    # Texts from before categories carry none; they count as the default.
    category = data["category"] or (
        {"name": default_category.name, "style": default_category.style}
        if default_category
        else None
    )
    data["category"] = category["name"] if category else None
    data["category_style"] = category["style"] if category else None
    data["attachments"] = [a["filename"] for a in data["attachments"]]
    return data


def _group_filter(project_group: str):
    """Match a project group by id, short name or name (case-insensitive)."""
    value = project_group.strip()
    lowered = value.lower()
    clauses = [
        func.lower(ProjectGroup.short_name) == lowered,
        func.lower(ProjectGroup.name) == lowered,
    ]
    if value.isdigit():
        clauses.append(ProjectGroup.id == int(value))
    return or_(*clauses)


def _resolve_group_ids(db: Session, values: list[str]) -> set[int]:
    ids = set()
    for value in values:
        group = db.query(ProjectGroup).filter(_group_filter(value)).first()
        if group is None:
            raise ToolError(f"Projektgruppe '{value}' nicht gefunden.")
        ids.add(group.id)
    return ids


def list_project_groups(search: str | None = None, *, ctx: Context) -> dict[str, Any]:
    """Project groups (e.g. Bedarfsplan, Deutschlandtakt) with id, short name,
    name and the number of (non-draft, non-archived) projects. ``search`` is a case-insensitive
    substring of short name or name. Use the short name or id as ``project_group``
    in list_projects."""
    get_principal(ctx)
    project_count = func.count(Project.id)
    with tool_session(ctx) as db:
        query = (
            db.query(ProjectGroup, project_count)
            .outerjoin(
                ProjectGroup.projects.and_(Project.is_draft.is_(False), Project.is_archived.is_(False))
            )
            .group_by(ProjectGroup.id)
        )
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(ProjectGroup.short_name.ilike(pattern), ProjectGroup.name.ilike(pattern))
            )
        rows = query.order_by(ProjectGroup.name, ProjectGroup.id).all()
        return {
            "groups": [
                {
                    "id": group.id,
                    "short_name": group.short_name,
                    "name": group.name,
                    "description": group.description,
                    "project_count": count,
                }
                for group, count in rows
            ]
        }


# --- Filter registry ---------------------------------------------------------
# One entry per filterable project property. list_projects applies them (named
# parameters and the generic ``filters`` list share this code) and
# list_project_filters publishes the catalog, so a new field is added here only.

_OPERATOR_HELP = {
    "eq": "equals (text: case-insensitive)",
    "ne": "does not equal",
    "contains": "text contains the value (case-insensitive)",
    "not_contains": "text does not contain the value",
    "starts_with": "text starts with the value (case-insensitive)",
    "ends_with": "text ends with the value (case-insensitive)",
    "gt": "greater than",
    "gte": "greater than or equal (date: on or after)",
    "lt": "less than",
    "lte": "less than or equal (date: on or before)",
    "in": "equals one of the values in a list",
    "is_empty": "not set (no value needed)",
    "not_empty": "set (no value needed)",
}
_EMPTY_OPS = {"is_empty", "not_empty"}
_TEXT_OPS = ("eq", "ne", "contains", "not_contains", "starts_with", "ends_with", *_EMPTY_OPS)
_NUMBER_OPS = ("eq", "ne", "gt", "gte", "lt", "lte", *_EMPTY_OPS)
_ENUM_OPS = ("eq", "ne", "in")


class ProjectFilter(BaseModel):
    """One condition of list_projects: ``field`` and ``op`` come from
    list_project_filters; ``value`` is omitted for is_empty / not_empty."""

    model_config = ConfigDict(extra="forbid")

    field: str
    op: str = "eq"
    value: Any = None


@dataclass(frozen=True)
class FilterField:
    name: str
    type: str
    description: str
    operators: tuple[str, ...]
    clause: Callable[[str, Any], Any]
    values: tuple[str, ...] | None = None

    def describe(self) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "field": self.name,
            "type": self.type,
            "operators": list(self.operators),
            "description": self.description,
        }
        if self.values is not None:
            entry["values"] = list(self.values)
        return entry


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
        return value.strip().lower() == "true"
    raise ToolError("Erwartet wird ein Wahrheitswert (true oder false).")


def _as_number(value: Any, integer: bool) -> int | float:
    if isinstance(value, bool):
        raise ToolError("Erwartet wird eine Zahl.")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ToolError("Erwartet wird eine Zahl.") from None
    if integer:
        if number != int(number):
            raise ToolError("Erwartet wird eine ganze Zahl.")
        return int(number)
    return number


def _as_date(value: Any) -> date:
    try:
        return date.fromisoformat(value.strip()) if isinstance(value, str) else value.date()
    except (AttributeError, ValueError):
        raise ToolError("Erwartet wird ein Datum im Format JJJJ-MM-TT.") from None


def _as_text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolError("Erwartet wird ein nicht-leerer Text.")
    return value.strip()


def _text_field(name: str, column: Any, description: str) -> FilterField:
    def clause(op: str, value: Any):
        if op in _EMPTY_OPS:
            empty = or_(column.is_(None), func.trim(column) == "")
            return empty if op == "is_empty" else not_(empty)
        text = _as_text(value)
        match op:
            case "eq":
                return func.lower(column) == text.lower()
            case "ne":
                return or_(column.is_(None), func.lower(column) != text.lower())
            case "contains":
                return column.icontains(text, autoescape=True)
            case "not_contains":
                return or_(column.is_(None), not_(column.icontains(text, autoescape=True)))
            case "starts_with":
                return column.istartswith(text, autoescape=True)
            case _:
                return column.iendswith(text, autoescape=True)

    return FilterField(name, "text", description, _TEXT_OPS, clause)


def _number_field(
    name: str, column: Any, description: str, *, integer: bool = False, operators=_NUMBER_OPS
) -> FilterField:
    def clause(op: str, value: Any):
        if op in _EMPTY_OPS:
            return column.is_(None) if op == "is_empty" else column.isnot(None)
        number = _as_number(value, integer)
        match op:
            case "eq":
                return column == number
            case "ne":
                return or_(column.is_(None), column != number)
            case "gt":
                return column > number
            case "gte":
                return column >= number
            case "lt":
                return column < number
            case _:
                return column <= number

    return FilterField(name, "integer" if integer else "number", description, operators, clause)


def _enum_field(name: str, column: Any, values: tuple[str, ...], description: str) -> FilterField:
    def normalize(value: Any) -> str:
        text = _as_text(value).upper()
        if text not in values:
            raise ToolError(f"Ungültiger Wert '{value}'. Erlaubt: {', '.join(values)}")
        return text

    def clause(op: str, value: Any):
        if op == "in":
            if not isinstance(value, list) or not value:
                raise ToolError("Für 'in' wird eine nicht-leere Liste erwartet.")
            return column.in_([normalize(v) for v in value])
        chosen = normalize(value)
        if op == "eq":
            return column == chosen
        return or_(column.is_(None), column != chosen)

    return FilterField(name, "enum", description, _ENUM_OPS, clause, values)


def _flag_field(name: str, description: str, make: Callable[[bool], Any]) -> FilterField:
    return FilterField(name, "boolean", description, ("eq",), lambda op, value: make(_as_bool(value)))


def _group_clause(op: str, value: Any):
    values = value if op == "in" else [value]
    if not isinstance(values, list) or not values:
        raise ToolError("Für 'in' wird eine nicht-leere Liste erwartet.")
    member = or_(*(Project.project_groups.any(_group_filter(_as_text(v))) for v in values))
    return not_(member) if op == "ne" else member


def _last_change_clause(op: str, value: Any):
    day = _as_date(value)
    changed = last_change_expr()
    if op == "gte":
        return changed >= datetime.combine(day, time.min)
    return changed < datetime.combine(day + timedelta(days=1), time.min)


def _milestone_field(name: str, column: Any, precision: Any, description: str) -> FilterField:
    """Cached forecast date with its precision: ``gte``/``lte`` count a YEAR or
    MONTH date when its period overlaps the bound (2028 matches gte
    2028-06-01); a NOT_BEFORE date („nach 2031“) is never a hit — it is no
    date. Same rule as ``services.date_precision.in_period``."""

    def clause(op: str, value: Any):
        day = _as_date(value)
        if op == "gte":
            year_bound, month_bound = date(day.year, 1, 1), day.replace(day=1)
            compare = lambda bound: column >= bound  # noqa: E731
        else:
            last = calendar.monthrange(day.year, day.month)[1]
            year_bound, month_bound = date(day.year, 12, 31), day.replace(day=last)
            compare = lambda bound: column <= bound  # noqa: E731
        return and_(
            column.isnot(None),
            or_(
                and_(precision == "YEAR", compare(year_bound)),
                and_(precision == "MONTH", compare(month_bound)),
                and_(
                    or_(precision.is_(None), precision.in_(("EXACT", "ASSUMED"))),
                    compare(day),
                ),
            ),
        )

    return FilterField(name, "date", description, ("gte", "lte"), clause)


def date_open_expr():
    """Baubeginn or Inbetriebnahme is only a lower bound („nach 2031“)."""
    return or_(
        ProjectProgress.construction_start_precision == "NOT_BEFORE",
        ProjectProgress.commissioning_precision == "NOT_BEFORE",
    )


def _build_filter_fields() -> dict[str, FilterField]:
    effective_phase = effective_phase_expr()
    fields = [
        _text_field("name", Project.name, "Project name"),
        _text_field("project_number", Project.project_number, "Project number"),
        _text_field("description", Project.description, "Project description"),
        _flag_field(
            "closure",
            "Flagged as a line closure (Stilllegung); an unset flag counts as false",
            lambda v: func.coalesce(Project.closure, False) == v,
        ),
        _enum_field(
            "phase",
            effective_phase,
            get_args(MainPhaseLiteral),
            "Planning phase (cached headline; manual override wins)",
        ),
        _enum_field(
            "lifecycle_status",
            func.coalesce(ProjectProgress.lifecycle_status, "AKTIV"),
            get_args(LifecycleStatusLiteral),
            "Lifecycle; projects without planning state count as AKTIV",
        ),
        FilterField(
            "project_group",
            "text",
            "Member of a project group, given as id, short name or name "
            "(case-insensitive, see list_project_groups); 'in' = any of the groups",
            _ENUM_OPS,
            _group_clause,
        ),
        _number_field(
            "superior_project_id",
            Project.superior_project_id,
            "Id of the direct superior project; is_empty = top-level project",
            integer=True,
            operators=("eq", "ne", *_EMPTY_OPS),
        ),
        _number_field("length", Project.length, "Stored length in km"),
        _flag_field(
            "is_known",
            "Planning state backed by an observation or an override (false = unknown)",
            lambda v: is_known_expr() if v else not_(is_known_expr()),
        ),
        _flag_field(
            "has_geometry",
            "A line/point geometry is stored",
            lambda v: has_geometry_expr() if v else not_(has_geometry_expr()),
        ),
        _flag_field(
            "has_length",
            "A length greater than zero is stored",
            lambda v: has_length_expr() if v else not_(has_length_expr()),
        ),
        _flag_field(
            "parl_befassung_relevant",
            "Parliamentary involvement relevant (override, else newest Infraplan "
            "statement, else BSWAG* group)",
            parl_relevant_expr,
        ),
        _milestone_field(
            "construction_start",
            ProjectProgress.construction_start_date,
            ProjectProgress.construction_start_precision,
            "Baubeginn of the forecast (JJJJ-MM-TT; gte/lte, a year-only date matches "
            "when its year overlaps; „nach 2031“ never matches — use date_open)",
        ),
        _milestone_field(
            "commissioning",
            ProjectProgress.commissioning_date,
            ProjectProgress.commissioning_precision,
            "Inbetriebnahme of the forecast incl. assumed ones (JJJJ-MM-TT; same rules "
            "as construction_start)",
        ),
        _flag_field(
            "date_open",
            "Termin offen: Baubeginn or Inbetriebnahme known only as a lower bound "
            "(NOT_BEFORE, „nach 2031“)",
            lambda v: date_open_expr() if v else not_(func.coalesce(date_open_expr(), False)),
        ),
        FilterField(
            "last_change",
            "date",
            "Date of the newest changelog entry (JJJJ-MM-TT); never-changed projects match neither",
            ("gte", "lte"),
            _last_change_clause,
        ),
    ]
    return {f.name: f for f in fields}


_FILTER_FIELDS = _build_filter_fields()


def filter_clause(spec: ProjectFilter):
    """SQL condition for one filter spec; a ToolError names what is wrong."""
    field = _FILTER_FIELDS.get(spec.field)
    if field is None:
        raise ToolError(
            f"Unbekanntes Filterfeld '{spec.field}'. Verfügbar: {', '.join(_FILTER_FIELDS)} "
            "(Details: list_project_filters)"
        )
    if spec.op not in field.operators:
        raise ToolError(
            f"Operator '{spec.op}' passt nicht zu '{spec.field}'. "
            f"Erlaubt: {', '.join(field.operators)}"
        )
    try:
        return field.clause(spec.op, spec.value)
    except ToolError as exc:
        raise ToolError(f"Filter '{spec.field}' {spec.op}: {exc}") from exc


def list_project_filters(*, ctx: Context) -> dict[str, Any]:
    """Catalog of the filters list_projects accepts in its ``filters`` list: per
    field its type, allowed operators, description and (for enums) the allowed
    values, plus what each operator means. Conditions are combined with AND."""
    get_principal(ctx)
    return {
        "fields": [f.describe() for f in _FILTER_FIELDS.values()],
        "operators": _OPERATOR_HELP,
        "example": [
            {"field": "description", "op": "starts_with", "value": "Reaktivierung"},
            {"field": "project_group", "op": "eq", "value": "GVFG"},
        ],
    }


ProjectOrder = Literal["name", "id", "length", "last_change"]
DraftFilter = Literal["exclude", "only", "include"]


def draft_filter(drafts: DraftFilter):
    """SQL condition on Project.is_draft for a ``drafts`` argument. Archived
    projects are excluded in every mode (feature-project-archive.md)."""
    not_archived = Project.is_archived.is_(False)
    if drafts == "exclude":
        return and_(Project.is_draft.is_(False), not_archived)
    if drafts == "only":
        return and_(Project.is_draft.is_(True), not_archived)
    return not_archived


def list_projects(
    search: str | None = None,
    project_group: str | list[str] | None = None,
    phase: MainPhaseLiteral | None = None,
    superior_project_id: int | None = None,
    is_known: bool | None = None,
    has_geometry: bool | None = None,
    has_length: bool | None = None,
    lifecycle_status: LifecycleStatusLiteral | None = None,
    parl_befassung_relevant: bool | None = None,
    date_open: bool | None = None,
    updated_since: date | None = None,
    filters: list[ProjectFilter] | None = None,
    drafts: DraftFilter = "exclude",
    order_by: ProjectOrder = "name",
    descending: bool = False,
    limit: int = 50,
    offset: int = 0,
    with_description: bool = False,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Search projects (drafts excluded unless ``drafts`` says otherwise, archived
    projects always excluded), sorted by name unless ``order_by`` says otherwise.

    - search: case-insensitive substring of name, project number, description
      or an alias ("DT 38", "Gäubahn")
    - with_description: true adds the first sentence of the description
      (``short_description``, max. 200 characters) and the ``aliases`` to every
      entry — e.g. with superior_project_id to tell subprojects named only
      "Teilmaßnahme 3" apart without get_project per project
    - project_group: id, short name or name of a project group (case-insensitive,
      see list_project_groups); a list matches projects in all of the groups
    - phase: planning phase (cached headline; manual override wins)
    - superior_project_id: only direct subprojects of this project
    - is_known: true = the planning state is backed by an observation or an
      override; false = unknown (``phase`` then shows the NICHT_GESTARTET fallback)
    - has_geometry / has_length: whether a line/point geometry or a length is stored
    - lifecycle_status: AKTIV (also projects without planning state), PAUSIERT, ABGEBROCHEN
    - parl_befassung_relevant: parliamentary involvement relevant (override, else
      membership in a BSWAG* group)
    - date_open: true = Termin offen — Baubeginn or Inbetriebnahme is only a
      lower bound (date_precision NOT_BEFORE, „nach 2031“)
    - updated_since: only projects with a changelog entry on or after this date
    - filters: further conditions, combined with AND with everything above, as a
      list of ``{field, op, value}`` — e.g. description starts_with
      "Reaktivierung", or closure eq true. Which fields and operators exist
      (also name, project_number, length, …) is answered by list_project_filters
    - drafts: exclude (default) = finalized projects only, only = drafts only
      (e.g. created by an import and not yet maintained), include = both; each
      entry carries ``is_draft``. Finalize or revert with set_project_draft.
    - order_by: name, id, length or last_change (newest change; projects never
      changed come last); descending reverses the order
    Each entry carries ``construction_start`` and ``commissioning`` of the
    forecast (``{date, precision, text}`` or null): ``date`` is only the sort
    value — show ``text`` („2028“, „nach 2031“, „ca. 07/2028 (Annahme)“).
    Filter them with ``filters`` on construction_start / commissioning (gte/lte;
    a NOT_BEFORE date never matches a period).
    Returns ``total`` plus one page of compact entries; use get_project for details.
    """
    get_principal(ctx)
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    effective_phase = effective_phase_expr()
    known = is_known_expr()
    with tool_session(ctx) as db:
        query = (
            db.query(
                Project,
                effective_phase,
                known,
                ProjectProgress.construction_start_date,
                ProjectProgress.construction_start_precision,
                ProjectProgress.commissioning_date,
                ProjectProgress.commissioning_precision,
            )
            .outerjoin(ProjectProgress, ProjectProgress.project_id == Project.id)
        )
        draft_condition = draft_filter(drafts)
        if draft_condition is not None:
            query = query.filter(draft_condition)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Project.name.ilike(pattern),
                    Project.project_number.ilike(pattern),
                    Project.description.ilike(pattern),
                    cast(Project.aliases, String).ilike(pattern),
                )
            )
        groups = [project_group] if isinstance(project_group, str) else project_group or []
        # The named parameters are shortcuts for registry filters; a list of groups
        # means membership in all of them.
        specs = [ProjectFilter(field="project_group", value=g) for g in groups if g.strip()]
        named = {
            "phase": phase,
            "superior_project_id": superior_project_id,
            "is_known": is_known,
            "has_geometry": has_geometry,
            "has_length": has_length,
            "lifecycle_status": lifecycle_status,
            "parl_befassung_relevant": parl_befassung_relevant,
            "date_open": date_open,
        }
        specs += [ProjectFilter(field=k, value=v) for k, v in named.items() if v is not None]
        if updated_since is not None:
            specs.append(ProjectFilter(field="last_change", op="gte", value=updated_since.isoformat()))
        specs += filters or []
        for spec in specs:
            query = query.filter(filter_clause(spec))
        total = query.count()

        sort_key = {
            "name": Project.name,
            "id": Project.id,
            "length": Project.length,
            "last_change": last_change_expr(),
        }[order_by]
        primary = sort_key.desc() if descending else sort_key.asc()
        if order_by in {"length", "last_change"}:
            # Projects without a length / without changes go last in both directions.
            primary = primary.nulls_last()
        rows = (
            query.options(selectinload(Project.project_groups))
            .order_by(primary, Project.name, Project.id)
            .offset(offset)
            .limit(limit)
            .all()
        )
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "projects": [
                _project_summary(project, row_phase, bool(row_known), with_description, tuple(dates))
                for project, row_phase, row_known, *dates in rows
            ],
        }


def get_project(project_id: int, *, ctx: Context) -> dict[str, Any]:
    """Project detail: all fields, project groups, direct subprojects and BVWP data.
    The id of a merged project resolves to the project it was merged into
    (``redirected_from`` then names the old id)."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        redirected_from = None
        if get_project_by_id(db, project_id) is None:
            target = resolve_redirect(db, project_id)
            if target is not None:
                redirected_from, project_id = project_id, target
        project = _project_or_error(db, project_id)
        data = _project_dict(project)
        if redirected_from is not None:
            data["redirected_from"] = redirected_from
        data["subprojects"] = [
            {"id": sub.id, "name": sub.name, "project_number": sub.project_number}
            for sub in get_subprojects(db, project.id)
        ]
        bvwp = get_bvwp_data(db, project.id)
        data["bvwp"] = (
            BvwpProjectDataSchema.model_validate(bvwp).model_dump(mode="json", exclude_none=True)
            if bvwp
            else None
        )
        # Successor of an archived, replaced project / archived projects it replaces.
        data.update(replacement_crud(db, project.id))
        return data


def get_project_progress(project_id: int, *, ctx: Context) -> dict[str, Any]:
    """Planning state (Planungsstand): effective phase, parallel tracks (PF,
    parliament), observations with their trust and role (decisive, lower bound,
    in conflict), a set-back ``conflict`` (newer report with a lower phase than
    older information), subproject span and forecast.
    Dates: ``observed_date`` / ``expected_date`` are sort values only — every
    observation and forecast step carries ``date_precision`` (EXACT, MONTH,
    YEAR, NOT_BEFORE = lower bound only, ASSUMED = derived by a rule) and
    ``date_text`` („2028“, „nach 2031“, „ca. 07/2028 (Annahme)“); quote
    ``date_text``, never the bare date. A step's ``derivation`` says how an
    assumed date came about. Fix the precision of a manual observation with
    update_progress_observation.
    ``forecast.ibn_doubt`` set → the GVFG-Finanzreihe still funds the project
    after the known Inbetriebnahme year; question that year and cite it."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        view = progress_crud.get_progress_view(db, project_id)
        return ProjectProgressSchema.model_validate(view).model_dump(mode="json")


def list_project_finves(
    project_id: int, include_subprojects: bool = False, *, ctx: Context
) -> list[dict[str, Any]]:
    """Financing agreements (FinVe) of a project with their budget history per
    budget year, including the per-Haushaltstitel breakdown. Amounts in T€.
    ``include_subprojects`` adds the FinVes of all sub-projects, each once;
    those carry ``from_subprojects`` and name the carrying ``subprojects``.
    To find FinVes regardless of a project link, use list_finves."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        finves = get_project_finves_with_budgets(db, project, include_subprojects=include_subprojects)
        return [f.model_dump(mode="json") for f in finves]


def get_project_texts(
    project_id: int, text_type: str | None = None, *, ctx: Context
) -> list[dict[str, Any]]:
    """Texts of a project, optionally filtered by text type name (case-insensitive).
    Use list_text_types for the available types."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        texts = get_texts_for_project(db, project_id)
        if text_type:
            wanted = text_type.strip().lower()
            texts = [t for t in texts if t.text_type and t.text_type.name.lower() == wanted]
        default = get_default_text_category(db)
        return [_text_dict(t, default) for t in texts]


def list_text_types(*, ctx: Context) -> list[dict[str, Any]]:
    """Available project text types (id + name), needed for upsert_project_text."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        return [{"id": t.id, "name": t.name} for t in get_text_types(db)]


def list_text_categories(*, ctx: Context) -> list[dict[str, Any]]:
    """Available text categories (id, name, style), e.g. Info or Warnung, for the
    ``category_id`` of upsert_project_text. The style decides the display:
    neutral, info, warning (highlighted) or critical (highlighted)."""
    get_principal(ctx)
    with tool_session(ctx) as db:
        return [
            {"id": c.id, "name": c.name, "style": c.style} for c in get_text_categories(db)
        ]


def create_project(
    name: str,
    superior_project_id: int | None = None,
    project_number: str | None = None,
    description: str | None = None,
    project_groups: list[str] | None = None,
    fields: dict[str, Any] | None = None,
    final: bool = False,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Create a project, e.g. a subproject (stage) of an existing one (requires
    ``project.create``). The project is created as a draft (hidden from the
    default lists and the map) unless ``final=true``; finalize or revert with
    set_project_draft.

    - superior_project_id: the parent project (see get_project for subprojects)
    - project_groups: ids, short names or names (see list_project_groups)
    - fields: further project fields as in update_project, e.g. {"length": 12.5}
    Geometry cannot be set here: add it afterwards with route_project_geometry or
    edit_project_geometry. The creation is written to the project
    changelog. Returns the new project."""
    principal = get_principal(ctx)
    require(principal, "project.create")
    extra = dict(fields or {})
    blocked = sorted(set(extra) & (_READONLY_UPDATE_FIELDS | {_GROUP_FIELD}))
    if blocked:
        raise ToolError(f"Diese Felder sind hier nicht setzbar: {', '.join(blocked)}")
    unknown = sorted(set(extra) - set(ProjectCreate.model_fields))
    if unknown:
        raise ToolError(f"Unbekannte Felder: {', '.join(unknown)}")
    extra.update(
        {
            key: value
            for key, value in {
                "name": name,
                "superior_project_id": superior_project_id,
                "project_number": project_number,
                "description": description,
            }.items()
            if value is not None
        }
    )
    try:
        data = ProjectCreate.model_validate(extra).model_dump(exclude_unset=True)
    except ValidationError as exc:
        raise ToolError(f"Ungültige Werte: {exc}") from exc
    data["is_draft"] = not final

    with tool_session(ctx) as db:
        if "superior_project_id" in data:
            try:
                validate_superior_project(db, None, data["superior_project_id"])
            except ProjectHierarchyError as exc:
                raise ToolError(str(exc)) from exc
        groups = [g for g in project_groups or [] if g.strip()]
        if groups:
            data[_GROUP_FIELD] = sorted(_resolve_group_ids(db, groups))
        user = load_user(db, principal)
        project = create_project_crud(db, data)
        create_changelog_for_create(
            db,
            project,
            {k: v for k, v in data.items() if k != _GROUP_FIELD and (k != "is_draft" or v)},
            user.id,
            user.username,
        )
        db.commit()
        db.refresh(project)
        return _project_dict(project)


def compute_project_length(
    project_id: int, apply: bool = False, *, ctx: Context
) -> dict[str, Any]:
    """Length in km computed from the project geometry — the same calculation as
    "Länge aus Geometrie berechnen" in the UI (geodesic sum over all lines).
    Returns the computed and the stored length. With ``apply=true`` the computed
    value is written to the ``length`` field (requires ``project.edit``; recorded
    in the changelog). This is the source for ``length``: use it instead of
    published lengths (e.g. from DB press releases), which measure differently."""
    principal = get_principal(ctx)
    if apply:
        require(principal, "project.edit")
    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        computed = compute_geojson_length_km(project.geojson_representation)
        result = {
            "project_id": project.id,
            "has_geometry": bool(project.geojson_representation),
            "geometry_from_subprojects": bool(project.geojson_from_subprojects),
            "computed_length_km": computed,
            "stored_length_km": project.length,
            "applied": False,
        }
        if not apply:
            return result
        if computed is None:
            raise ToolError("Aus der Projektgeometrie lässt sich keine Länge berechnen.")
        if project.length != computed:
            update_data = {"length": computed}
            user = load_user(db, principal)
            create_changelog_for_patch(db, project, update_data, user.id, user.username)
            project = update_project_crud(db, project.id, update_data, project=project)
        result.update(stored_length_km=project.length, applied=True)
        return result


def update_project(project_id: int, changes: dict[str, Any], *, ctx: Context) -> dict[str, Any]:
    """Change project fields (requires ``project.edit``). ``changes`` maps field
    names to new values, e.g. {"description": "…", "nbs": true}; see get_project
    for the field names. Geometry and the draft flag cannot be changed here
    (geometry: route_project_geometry / edit_project_geometry; draft flag:
    set_project_draft); use
    set_project_groups for the group assignment. ``length`` comes from the
    geometry: set it with compute_project_length, not from published figures.
    ``aliases`` replaces the list of other names and ids, e.g.
    {"aliases": ["DT 38", "Gäubahn"]} — a Deutschlandtakt id "DT nn" counts as a
    sure hit when the Infraplan import matches rows, free aliases help the name
    matching and the search.
    Every change is written to the project changelog and can be reverted in the UI."""
    principal = get_principal(ctx)
    require(principal, "project.edit")
    if _GROUP_FIELD in changes:
        raise ToolError("Projektgruppen bitte mit set_project_groups ändern.")
    blocked = sorted(set(changes) & _READONLY_UPDATE_FIELDS)
    if blocked:
        raise ToolError(f"Diese Felder sind über MCP nicht änderbar: {', '.join(blocked)}")
    unknown = sorted(set(changes) - set(ProjectUpdate.model_fields))
    if unknown:
        raise ToolError(f"Unbekannte Felder: {', '.join(unknown)}")
    try:
        update_data = ProjectUpdate.model_validate(changes).model_dump(exclude_unset=True)
    except ValidationError as exc:
        raise ToolError(f"Ungültige Werte: {exc}") from exc
    if not update_data:
        raise ToolError("Keine Änderungen übergeben.")

    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        if "superior_project_id" in update_data:
            try:
                validate_superior_project(db, project.id, update_data["superior_project_id"])
            except ProjectHierarchyError as exc:
                raise ToolError(str(exc)) from exc
        user = load_user(db, principal)
        create_changelog_for_patch(db, project, update_data, user.id, user.username)
        updated = update_project_crud(db, project.id, update_data, project=project)
        return _project_dict(updated)


def set_project_draft(project_id: int, is_draft: bool, *, ctx: Context) -> dict[str, Any]:
    """Turn a project into a draft or finalize a draft (requires ``project.edit``).
    Drafts are hidden from list_projects (unless ``drafts`` is set), the map and
    the public lists; their funding data (GVFG, FinVe, …) stays linked. Finalize
    a draft once its data is maintained. The change is written to the project
    changelog and can be reverted in the UI. Returns the project."""
    principal = get_principal(ctx)
    require(principal, "project.edit")
    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        update_data = {"is_draft": is_draft}
        user = load_user(db, principal)
        create_changelog_for_patch(db, project, update_data, user.id, user.username)
        updated = update_project_crud(db, project.id, update_data, project=project)
        return _project_dict(updated)


def create_project_group(
    name: str,
    short_name: str,
    description: str | None = None,
    color: str = "#6E50FA",
    public: bool = False,
    plot_only_superior_projects: bool = True,
    is_visible: bool = True,
    is_default_selected: bool = False,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Create a new project group (requires ``projectgroup.create``). ``short_name``
    (max. 20 characters) must be unique and is what list_projects and
    set_project_groups accept as ``project_group``; ``name`` is the display name
    (max. 100). ``color`` is a hex colour for the map. New groups are not public
    and hold no projects — add projects with set_project_groups. Check
    list_project_groups first to avoid near-duplicates. Returns the group."""
    principal = get_principal(ctx)
    require(principal, "projectgroup.create")
    try:
        payload = ProjectGroupCreate(
            name=name.strip(),
            short_name=short_name.strip(),
            description=description,
            color=color.strip(),
            public=public,
            plot_only_superior_projects=plot_only_superior_projects,
            is_visible=is_visible,
            is_default_selected=is_default_selected,
        )
    except ValidationError as exc:
        raise ToolError(f"Ungültige Werte: {exc}") from exc
    if not payload.name or not payload.short_name:
        raise ToolError("name und short_name dürfen nicht leer sein.")
    if len(payload.name) > 100 or len(payload.short_name) > 20 or len(payload.color) > 10:
        raise ToolError("Zu lang: name max. 100, short_name max. 20, color max. 10 Zeichen.")
    with tool_session(ctx) as db:
        if db.query(ProjectGroup).filter(_group_filter(payload.short_name)).first():
            raise ToolError(
                f"Eine Projektgruppe mit Kurzname oder Name '{payload.short_name}' existiert bereits."
            )
        group = create_project_group_crud(db, payload.model_dump())
        return {
            "id": group.id,
            "short_name": group.short_name,
            "name": group.name,
            "description": group.description,
            "color": group.color,
            "public": group.public,
            "plot_only_superior_projects": group.plot_only_superior_projects,
            "is_visible": group.is_visible,
            "is_default_selected": group.is_default_selected,
            "project_count": 0,
        }


def set_project_groups(
    project_id: int,
    add: list[str] | None = None,
    remove: list[str] | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Add the project to and/or remove it from project groups (requires
    ``project.edit``). Groups are given by id, short name or name
    (case-insensitive, see list_project_groups); other memberships stay.
    The change is written to the project changelog and can be reverted in the UI.
    Returns the project's groups afterwards."""
    principal = get_principal(ctx)
    require(principal, "project.edit")
    add = [g for g in add or [] if g.strip()]
    remove = [g for g in remove or [] if g.strip()]
    if not add and not remove:
        raise ToolError("Keine Gruppen übergeben (add oder remove).")

    with tool_session(ctx) as db:
        project = _project_or_error(db, project_id)
        add_ids, remove_ids = _resolve_group_ids(db, add), _resolve_group_ids(db, remove)
        if add_ids & remove_ids:
            raise ToolError("Eine Gruppe steht sowohl in add als auch in remove.")
        current = {g.id for g in project.project_groups}
        new_ids = sorted((current | add_ids) - remove_ids)
        if set(new_ids) != current:
            update_data = {_GROUP_FIELD: new_ids}
            user = load_user(db, principal)
            create_changelog_for_patch(db, project, update_data, user.id, user.username)
            project = update_project_crud(db, project.id, update_data, project=project)
        return {
            "project_id": project.id,
            "project_groups": [
                {"id": g.id, "short_name": g.short_name, "name": g.name}
                for g in sorted(project.project_groups, key=lambda g: g.id)
            ],
        }


def add_progress_observation(
    project_id: int,
    track: TrackLiteral,
    asserted_state: str,
    observed_date: date | None = None,
    note: str | None = None,
    confidence: float | None = None,
    is_expected: bool = False,
    source_type: ManualSourceTypeLiteral = "MANUELL",
    date_precision: DatePrecisionLiteral = "EXACT",
    date_label: str | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Add a planning-state observation (requires ``progress.edit``).

    - track MAIN: asserted_state is a phase (NICHT_GESTARTET, VORPLANUNG,
      GENEHMIGUNGSPLANUNG, BAU, IN_BETRIEB)
    - track PF / PARL: asserted_state is OFFEN, LAEUFT or ABGESCHLOSSEN
    - is_expected: the date is a forecast, not a fact
    - date_precision: how much of observed_date the source states (default
      EXACT). Never invent a day the source does not give:
      EXACT = a day is published (06.02.2026);
      MONTH = only the month („Februar 2027“, stored as the 1st);
      YEAR = only the year („2028 geplant“, stored as 1 Jan);
      NOT_BEFORE = only a lower bound, no date („nach 2031“, „frühestens 2032“,
      not in a published ranking) — observed_date is the first possible day,
      e.g. 2032-01-01 for „nach 2031“; it never matches a period filter;
      ASSUMED = not published, derived by you from a rule — say how in note.
      Do not add the commissioning of a corridor renewal as Baubeginn + 6
      months: the forecast derives it from the group's assumed build period.
    - date_label: optional short text shown with the date, e.g.
      „Priorisierung 2027 offen“ („nach 2031 – Priorisierung 2027 offen“)
    - confidence: trust of this report (default: source default). The newest
      report wins; within one year trust decides. A MANUELL observation may set
      a project back without a conflict; other sources only when they are at
      least as trusted as the contradicting older information.
    Returns the recomputed planning state."""
    principal = get_principal(ctx)
    require(principal, "progress.edit")
    try:
        payload = ProgressObservationCreate(
            source_type=source_type,
            track=track,
            asserted_state=asserted_state,
            observed_date=observed_date,
            confidence=confidence,
            note=note,
            is_expected=is_expected,
            date_precision=date_precision,
            date_label=date_label,
        ).model_dump(exclude_unset=True)
    except ValidationError as exc:
        raise ToolError(f"Ungültige Werte: {exc}") from exc
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        user = load_user(db, principal)
        progress_crud.create_observation(db, project_id, payload, user)
        view = progress_crud.get_progress_view(db, project_id)
        return ProjectProgressSchema.model_validate(view).model_dump(mode="json")


def update_progress_observation(
    project_id: int,
    observation_id: int,
    date_precision: DatePrecisionLiteral | None = None,
    date_label: str | None = None,
    clear_date_label: bool = False,
    observed_date: date | None = None,
    note: str | None = None,
    confidence: float | None = None,
    is_expected: bool | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Change a manual planning-state observation in place (requires
    ``progress.edit``) — e.g. add the date precision to an existing entry
    instead of deleting and re-adding it. Only the given fields change; the
    change log records old and new value. Observation ids come from
    get_project_progress; derived observations (``is_derived``) cannot be
    changed.

    - date_precision: EXACT, MONTH, YEAR, NOT_BEFORE or ASSUMED (see
      add_progress_observation). MONTH / YEAR move observed_date to the first
      day of the month / year; for NOT_BEFORE set observed_date to the first
      possible day (2032-01-01 for „nach 2031“) if it is not already
    - date_label: short text shown with the date; clear_date_label removes it
    Returns the recomputed planning state."""
    principal = get_principal(ctx)
    require(principal, "progress.edit")
    try:
        payload = ProgressObservationUpdate(
            date_precision=date_precision,
            date_label=date_label,
            clear_date_label=clear_date_label,
            observed_date=observed_date,
            note=note,
            confidence=confidence,
            is_expected=is_expected,
        ).model_dump(exclude_none=True)
    except ValidationError as exc:
        raise ToolError(f"Ungültige Werte: {exc}") from exc
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        user = load_user(db, principal)
        try:
            updated = progress_crud.update_observation(
                db, project_id, observation_id, payload, user
            )
        except progress_crud.DerivedObservationUpdateError as exc:
            raise ToolError(
                "Abgeleitete Beobachtungen stammen aus den Importen und lassen sich "
                "nicht ändern."
            ) from exc
        if updated is None:
            raise ToolError(f"Beobachtung {observation_id} gehört nicht zu Projekt {project_id}.")
        view = progress_crud.get_progress_view(db, project_id)
        return ProjectProgressSchema.model_validate(view).model_dump(mode="json")


def delete_progress_observation(
    project_id: int, observation_id: int, *, ctx: Context
) -> dict[str, Any]:
    """Delete a manual planning-state observation (requires ``progress.edit``),
    e.g. a duplicate or a wrong entry. Observation ids are listed by
    get_project_progress. Derived observations (``is_derived``, from the
    imports) cannot be deleted. Returns the recomputed planning state."""
    principal = get_principal(ctx)
    require(principal, "progress.edit")
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        user = load_user(db, principal)
        try:
            deleted = progress_crud.delete_observation(db, project_id, observation_id, user)
        except progress_crud.DerivedObservationDeleteError as exc:
            raise ToolError(
                "Abgeleitete Beobachtungen stammen aus den Importen und lassen sich "
                "nicht löschen."
            ) from exc
        if deleted is None:
            raise ToolError(f"Beobachtung {observation_id} gehört nicht zu Projekt {project_id}.")
        view = progress_crud.get_progress_view(db, project_id)
        return ProjectProgressSchema.model_validate(view).model_dump(mode="json")


def set_phase_override(
    project_id: int,
    phase: MainPhaseLiteral | None = None,
    note: str | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Set or clear the manual phase override of a project (requires
    ``progress.edit``). The override wins over the phase computed from the
    observations; the observations stay untouched as evidence.

    - phase: the phase to pin; ``null`` clears the override (the computed phase
      applies again)
    - note: why the override is set (required when setting, e.g. the source)
    An override on a superior project pins its whole subtree.
    Returns the recomputed planning state."""
    principal = get_principal(ctx)
    require(principal, "progress.edit")
    if phase is not None and not (note and note.strip()):
        raise ToolError("Zum Setzen eines Overrides ist eine Begründung (note) nötig.")
    payload: dict[str, Any] = (
        {"manual_phase_override": phase, "manual_override_note": note.strip()}
        if phase is not None
        else {"clear_phase_override": True}
    )
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        progress_crud.update_progress(db, project_id, payload, load_user(db, principal))
        view = progress_crud.get_progress_view(db, project_id)
        return ProjectProgressSchema.model_validate(view).model_dump(mode="json")


def upsert_project_text(
    project_id: int,
    header: str | None = None,
    text: str | None = None,
    text_type_id: int | None = None,
    weblink: str | None = None,
    text_id: int | None = None,
    category_id: int | None = None,
    is_public: bool | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Create a project text, or update one when ``text_id`` is given (requires
    ``projecttext.edit``). Creating needs ``header`` and ``text_type_id`` (see
    list_text_types); on update only the passed fields change. ``category_id``
    (see list_text_categories) defaults to „Info“ on create. ``is_public=false``
    shows the text to signed-in users only (default on create: public). The
    category and visibility apply to every project the text is linked to.
    Changes are written to the text changelog."""
    principal = get_principal(ctx)
    require(principal, "projecttext.edit")
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        if text_type_id is not None and text_type_id not in {t.id for t in get_text_types(db)}:
            raise ToolError(f"Texttyp {text_type_id} existiert nicht.")
        if category_id is not None and get_text_category(db, category_id) is None:
            raise ToolError(f"Kategorie {category_id} existiert nicht.")
        user = load_user(db, principal)

        if text_id is None:
            if not header or text_type_id is None:
                raise ToolError("Zum Anlegen sind header und text_type_id nötig.")
            created = create_text_for_project(
                db,
                project_id,
                {
                    "header": header,
                    "text": text,
                    "weblink": weblink,
                    "type": text_type_id,
                    "category_id": category_id,
                    "is_public": True if is_public is None else is_public,
                },
            )
            create_text_changelog_for_create(db, created, project_id, user.id, user.username)
            db.commit()
            return _text_dict(created)

        linked = (
            db.query(TextToProject)
            .filter(TextToProject.text_id == text_id, TextToProject.project_id == project_id)
            .first()
        )
        existing = db.query(ProjectText).filter(ProjectText.id == text_id).first()
        if linked is None or existing is None:
            raise ToolError(f"Text {text_id} gehört nicht zu Projekt {project_id}.")
        update_data = {
            key: value
            for key, value in {
                "header": header,
                "text": text,
                "weblink": weblink,
                "type": text_type_id,
                "category_id": category_id,
                "is_public": is_public,
            }.items()
            if value is not None
        }
        if not update_data:
            raise ToolError("Keine Änderungen übergeben.")
        create_text_changelog_for_patch(
            db, existing, update_data, project_id, user.id, user.username
        )
        return _text_dict(update_project_text(db, text_id, update_data), get_default_text_category(db))


def merge_projects(
    survivor_id: int,
    merged_id: int,
    geometry_from: Literal["survivor", "merged"] = "survivor",
    apply: bool = False,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Merge a duplicate into another project (requires ``project.merge``).
    ``survivor_id`` stays, ``merged_id`` is deleted; its old id redirects to the
    survivor. Without ``apply`` (default) nothing is written — the answer is the
    plan: field changes, links moved/dropped per table, moved subprojects and
    warnings. Check it, then call again with ``apply=true``.

    - Fields: the survivor wins, its empty fields are filled, flags are OR-ed.
    - geometry_from: whose geometry (with length, operational points and routes)
      is kept; ``survivor`` by default, automatically ``merged`` when the
      survivor has none.
    - All links (groups, texts, FinVe/VIB/…, todos, observations, changelog,
      subprojects) move to the survivor; duplicates are dropped.
    - Rejected when one project is an ancestor of the other.
    One pair per call."""
    principal = get_principal(ctx)
    require(principal, "project.merge")
    with tool_session(ctx) as db:
        user = load_user(db, principal) if apply else None
        try:
            return merge_projects_crud(
                db,
                survivor_id,
                merged_id,
                geometry_from=geometry_from,
                apply=apply,
                user_id=user.id if user else None,
                username=user.username if user else None,
            )
        except MergeError as exc:
            raise ToolError(str(exc)) from exc


def archive_project(
    project_id: int, reason: str, replaced_by_project_id: int | None = None, *, ctx: Context
) -> dict[str, Any]:
    """Archive a project that was replaced or superseded by other projects
    (requires ``project.delete``), e.g. old Teilmaßnahmen replaced by PFA-section
    subprojects. ``reason`` is mandatory and names what replaced it. An archived
    project keeps its history (VIB, Infraplan, changelog, geometry) and stays
    readable with get_project, but counts nowhere: not in list_projects, groups,
    the map, subproject lists, import candidates, nor in its parent's geometry,
    planning-state span or sums. Not for duplicates (merge_projects) and never
    for a really cancelled project (lifecycle ABGEBROCHEN stays visible).
    ``replaced_by_project_id`` names the successor when one project replaced
    this one (not itself, no draft, not archived): the detail page then links
    both ways, get_project shows ``replaced_by`` / ``replaces``, and last year's
    import assignments to this project are suggested for the successor.
    Refused while FinVe or GVFG links or non-archived subprojects exist — the
    error names them; move them first. Exception: Sammel-FinVe year links from
    the Haushalt import (``linked_permanently`` false) do not block; they stay on
    the archived project as history (not moved: the successors usually carry
    their own links) and no longer count in the Sammel-FinVe. Recorded in the
    changelog. Returns the project and ``kept_links`` (historical links that stay
    on the project, e.g. ``sammel_finve_year_links: [763, 1168]``)."""
    principal = get_principal(ctx)
    require(principal, "project.delete")
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        user = load_user(db, principal)
        try:
            result = archive_project_crud(
                db,
                project_id,
                reason,
                user.id,
                user.username,
                replaced_by_project_id=replaced_by_project_id,
            )
        except ArchiveError as exc:
            raise ToolError(str(exc)) from exc
        return {"project": _project_dict(result["project"]), "kept_links": result["kept_links"]}


def unarchive_project(project_id: int, reason: str | None = None, *, ctx: Context) -> dict[str, Any]:
    """Restore an archived project (requires ``project.delete``); ``reason`` is
    an optional note for the changelog. The project counts again in lists and in
    its parent's aggregation. Returns the project."""
    principal = get_principal(ctx)
    require(principal, "project.delete")
    with tool_session(ctx) as db:
        _project_or_error(db, project_id)
        user = load_user(db, principal)
        try:
            project = unarchive_project_crud(db, project_id, reason, user.id, user.username)
        except ArchiveError as exc:
            raise ToolError(str(exc)) from exc
        return _project_dict(project)


def register(server: MCPServer) -> None:
    for fn in (
        list_project_groups,
        list_projects,
        list_project_filters,
        get_project,
        get_project_progress,
        list_project_finves,
        get_project_texts,
        list_text_types,
        list_text_categories,
    ):
        server.add_tool(fn, annotations=READ_ONLY)
    for fn in (
        create_project,
        create_project_group,
        compute_project_length,
        update_project,
        set_project_draft,
        archive_project,
        unarchive_project,
        set_project_groups,
        add_progress_observation,
        update_progress_observation,
        set_phase_override,
        upsert_project_text,
    ):
        server.add_tool(fn, annotations=WRITE)
    server.add_tool(delete_progress_observation, annotations=DESTRUCTIVE)
    server.add_tool(merge_projects, annotations=DESTRUCTIVE)
