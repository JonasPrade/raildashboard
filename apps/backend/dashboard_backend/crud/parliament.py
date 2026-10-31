"""Read access for the constituency / members-of-parliament feature.

Every query here answers the same question from a different side: what connects
this member of parliament with this project? Ordering is therefore always by
weight — kilometres first, because that is what carries the argument.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta
from typing import Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from dashboard_backend.models.associations.project_to_constituency import (
    ProjectToConstituency,
)
from dashboard_backend.models.parliament import (
    Committee,
    CommitteeMembership,
    Constituency,
    IMPORT_KIND_CONSTITUENCIES,
    IMPORT_KIND_LINKS,
    IMPORT_KIND_POLITICIANS,
    IMPORT_STATUS_SUCCESS,
    Mandate,
    ParliamentImportRun,
    ParliamentPeriod,
    Politician,
)
from dashboard_backend.models.projects import Project
from dashboard_backend.schemas.parliament import (
    CommitteeRoleSchema,
    ConstituencyDetailSchema,
    ConstituencyListItemSchema,
    ConstituencyProjectSchema,
    ConstituencySummarySchema,
    ImportRunSchema,
    MandateSchema,
    PoliticianDetailSchema,
    PoliticianListItemSchema,
    PoliticianProjectSchema,
    ProjectConstituenciesSchema,
    ProjectConstituencySchema,
)
from dashboard_backend.services import constituency_matching

STALE_AFTER_DAYS = 60


def current_period(db: Session) -> ParliamentPeriod | None:
    return (
        db.query(ParliamentPeriod)
        .filter(ParliamentPeriod.is_current.is_(True))
        .order_by(ParliamentPeriod.external_id.desc())
        .first()
    )


def last_run(db: Session, kind: str) -> ParliamentImportRun | None:
    return (
        db.query(ParliamentImportRun)
        .filter(ParliamentImportRun.kind == kind)
        .order_by(ParliamentImportRun.started_at.desc(), ParliamentImportRun.id.desc())
        .first()
    )


def last_successful_run(db: Session, kind: str) -> ParliamentImportRun | None:
    return (
        db.query(ParliamentImportRun)
        .filter(
            ParliamentImportRun.kind == kind,
            ParliamentImportRun.status == IMPORT_STATUS_SUCCESS,
        )
        .order_by(ParliamentImportRun.started_at.desc(), ParliamentImportRun.id.desc())
        .first()
    )


def is_stale(run: ParliamentImportRun | None, days: int = STALE_AFTER_DAYS) -> bool:
    """People data older than *days* is flagged — substitutes and committee
    reshuffles move the assignment without anything looking wrong."""
    if run is None or run.finished_at is None:
        return True
    return run.finished_at < datetime.utcnow() - timedelta(days=days)


# --- mandates ---------------------------------------------------------------


def _committee_roles(mandate: Mandate) -> list[CommitteeRoleSchema]:
    roles = [
        CommitteeRoleSchema(
            key=membership.committee.key,
            label=membership.committee.label,
            role=membership.role,
            role_label=membership.role_label,
        )
        for membership in mandate.committee_memberships
        if membership.committee is not None
    ]
    roles.sort(key=lambda role: role.key)
    return roles


def mandate_to_schema(mandate: Mandate) -> MandateSchema:
    politician = mandate.politician
    return MandateSchema(
        mandate_id=mandate.id,
        politician_id=politician.id if politician else 0,
        name=politician.label if politician else "",
        first_name=politician.first_name if politician else None,
        last_name=politician.last_name if politician else None,
        fraction=mandate.fraction_label,
        party=politician.party_label if politician else None,
        mandate_type=mandate.mandate_type,
        is_direct_mandate=mandate.is_direct_mandate,
        profile_url=politician.abgeordnetenwatch_url if politician else None,
        info=mandate.info,
        committees=_committee_roles(mandate),
    )


def _sort_mandates(mandates: Iterable[MandateSchema]) -> list[MandateSchema]:
    """Committee members first — they are the actual working list — then by
    last name."""
    return sorted(
        mandates,
        key=lambda mandate: (
            0 if mandate.committees else 1,
            (mandate.last_name or mandate.name or "").lower(),
        ),
    )


def mandates_for_constituencies(
    db: Session, constituency_ids: Iterable[int]
) -> dict[int, list[Mandate]]:
    ids = list(constituency_ids)
    if not ids:
        return {}
    rows = (
        db.query(Mandate)
        .options(
            selectinload(Mandate.politician),
            selectinload(Mandate.committee_memberships).selectinload(
                CommitteeMembership.committee
            ),
        )
        .filter(Mandate.constituency_id.in_(ids))
        .all()
    )
    grouped: dict[int, list[Mandate]] = {}
    for mandate in rows:
        grouped.setdefault(mandate.constituency_id, []).append(mandate)
    return grouped


def split_mandates(
    mandates: Iterable[Mandate],
) -> tuple[list[MandateSchema], list[MandateSchema]]:
    """Direct mandate versus "ran here, entered over the state list"."""
    direct: list[MandateSchema] = []
    listed: list[MandateSchema] = []
    for mandate in mandates:
        schema = mandate_to_schema(mandate)
        (direct if schema.is_direct_mandate else listed).append(schema)
    return _sort_mandates(direct), _sort_mandates(listed)


# --- project → constituencies ----------------------------------------------


def links_for_project(db: Session, project_id: int) -> list[tuple[ProjectToConstituency, Constituency]]:
    """Links of one project, heaviest first (a point project has no kilometres)."""
    return (
        db.query(ProjectToConstituency, Constituency)
        .join(Constituency, Constituency.id == ProjectToConstituency.constituency_id)
        .filter(ProjectToConstituency.project_id == project_id)
        .order_by(
            ProjectToConstituency.length_km.desc(),
            ProjectToConstituency.share.desc(),
            Constituency.number,
        )
        .all()
    )


# --- politicians ------------------------------------------------------------


def politician_rows(
    db: Session,
    *,
    query: str | None = None,
    committee: str | None = None,
    fraction: str | None = None,
) -> list[Mandate]:
    """Mandates of the current period, filtered for the working list."""
    period = current_period(db)
    q = (
        db.query(Mandate)
        .options(
            selectinload(Mandate.politician),
            selectinload(Mandate.constituency),
            selectinload(Mandate.committee_memberships).selectinload(
                CommitteeMembership.committee
            ),
        )
        .join(Politician, Politician.id == Mandate.politician_id)
    )
    if period is not None:
        q = q.filter(Mandate.parliament_period_id == period.id)
    if fraction:
        q = q.filter(Mandate.fraction_label == fraction)
    if committee:
        q = (
            q.join(CommitteeMembership, CommitteeMembership.mandate_id == Mandate.id)
            .join(Committee, Committee.id == CommitteeMembership.committee_id)
            .filter(Committee.key == committee)
        )
    rows = q.order_by(Politician.last_name, Politician.label).all()

    if query:
        # 630 mandates: filtering in Python keeps the search umlaut-tolerant on
        # *both* sides, which a SQL LIKE over the raw column cannot do.
        needle = normalize_search(query)
        if needle:
            rows = [
                mandate
                for mandate in rows
                if needle in normalize_search(mandate.politician.label if mandate.politician else "")
            ]
    return rows


def normalize_search(term: str) -> str:
    """Fold a name into a comparable form, same rule as the project search in
    ``features/projects/projectSearch.ts``: diacritics stripped (Bär → bar),
    ß → ss, every non-alphanumeric run collapsed to a single space."""
    folded = unicodedata.normalize("NFD", term or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.lower().replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


def project_counts_by_constituency(db: Session, constituency_ids: Iterable[int]) -> dict[int, int]:
    ids = list(constituency_ids)
    if not ids:
        return {}
    rows = (
        db.query(
            ProjectToConstituency.constituency_id,
            func.count(ProjectToConstituency.project_id),
        )
        .join(Project, Project.id == ProjectToConstituency.project_id)
        .filter(
            ProjectToConstituency.constituency_id.in_(ids),
            Project.is_draft.is_(False),
            Project.is_archived.is_(False),
        )
        .group_by(ProjectToConstituency.constituency_id)
        .all()
    )
    return {constituency_id: count for constituency_id, count in rows}


def projects_for_constituency(db: Session, constituency_id: int) -> list[ConstituencyProjectSchema]:
    rows = (
        db.query(ProjectToConstituency, Project)
        .join(Project, Project.id == ProjectToConstituency.project_id)
        .filter(
            ProjectToConstituency.constituency_id == constituency_id,
            Project.is_draft.is_(False),
            Project.is_archived.is_(False),
        )
        .order_by(ProjectToConstituency.length_km.desc(), Project.name)
        .all()
    )
    return [
        ConstituencyProjectSchema(
            project_id=project.id,
            name=project.name,
            project_number=project.project_number,
            length_km=link.length_km,
            share=link.share,
            overlap_kind=link.overlap_kind,
        )
        for link, project in rows
    ]


def projects_for_politician(db: Session, constituency: Constituency | None) -> list[PoliticianProjectSchema]:
    """The working list before an appointment: the projects in their constituency."""
    if constituency is None:
        return []
    rows = (
        db.query(ProjectToConstituency, Project)
        .join(Project, Project.id == ProjectToConstituency.project_id)
        .filter(
            ProjectToConstituency.constituency_id == constituency.id,
            Project.is_draft.is_(False),
            Project.is_archived.is_(False),
        )
        .order_by(ProjectToConstituency.length_km.desc(), Project.name)
        .all()
    )
    return [
        PoliticianProjectSchema(
            project_id=project.id,
            name=project.name,
            project_number=project.project_number,
            length_km=link.length_km,
            share=link.share,
            overlap_kind=link.overlap_kind,
            constituency_number=constituency.number,
            constituency_name=constituency.name,
        )
        for link, project in rows
    ]


def constituency_summary(constituency: Constituency) -> ConstituencySummarySchema:
    return ConstituencySummarySchema(
        id=constituency.id,
        number=constituency.number,
        name=constituency.name,
        state=constituency.state,
    )


# --- status -----------------------------------------------------------------


def fractions(db: Session) -> list[str]:
    period = current_period(db)
    q = db.query(Mandate.fraction_label).filter(Mandate.fraction_label.isnot(None))
    if period is not None:
        q = q.filter(Mandate.parliament_period_id == period.id)
    return sorted({row[0] for row in q.distinct().all() if row[0]})


def committee_counts(db: Session) -> list[tuple[Committee, int]]:
    rows = (
        db.query(Committee, func.count(CommitteeMembership.id))
        .outerjoin(CommitteeMembership, CommitteeMembership.committee_id == Committee.id)
        .group_by(Committee.id)
        .order_by(Committee.key)
        .all()
    )
    return [(committee, count) for committee, count in rows]


def counts(db: Session) -> dict[str, int]:
    period = current_period(db)
    mandate_q = db.query(Mandate)
    constituency_q = db.query(Constituency)
    if period is not None:
        mandate_q = mandate_q.filter(Mandate.parliament_period_id == period.id)
        constituency_q = constituency_q.filter(
            Constituency.parliament_period_id == period.id
        )
    constituencies = constituency_q.count()
    with_geometry = constituency_q.filter(Constituency.geom.isnot(None)).count()
    direct = mandate_q.filter(Mandate.is_direct_mandate.is_(True)).count()
    return {
        "constituencies": constituencies,
        "constituencies_with_geometry": with_geometry,
        "mandates": mandate_q.count(),
        "direct_mandates": direct,
        "constituencies_without_direct_mandate": max(constituencies - direct, 0),
    }


def coverage(db: Session) -> dict[str, int]:
    return constituency_matching.coverage(db)


LAST_RUN_KINDS = (IMPORT_KIND_POLITICIANS, IMPORT_KIND_CONSTITUENCIES, IMPORT_KIND_LINKS)


# --- assembled views (shared by the REST endpoints and the MCP tools) -------


def politician_list_item(mandate: Mandate, counts: dict[int, int]) -> PoliticianListItemSchema:
    schema = mandate_to_schema(mandate)
    constituency = mandate.constituency
    return PoliticianListItemSchema(
        politician_id=schema.politician_id,
        mandate_id=schema.mandate_id,
        name=schema.name,
        first_name=schema.first_name,
        last_name=schema.last_name,
        fraction=schema.fraction,
        party=schema.party,
        mandate_type=schema.mandate_type,
        is_direct_mandate=schema.is_direct_mandate,
        profile_url=schema.profile_url,
        constituency=constituency_summary(constituency) if constituency else None,
        committees=schema.committees,
        project_count=counts.get(mandate.constituency_id, 0) if mandate.constituency_id else 0,
    )


def politician_list(
    db: Session,
    *,
    query: str | None = None,
    committee: str | None = None,
    fraction: str | None = None,
) -> list[PoliticianListItemSchema]:
    """The working list before an appointment: name search + committee/faction filter."""
    mandates = politician_rows(db, query=query, committee=committee, fraction=fraction)
    counts = project_counts_by_constituency(
        db, {mandate.constituency_id for mandate in mandates if mandate.constituency_id}
    )
    return [politician_list_item(mandate, counts) for mandate in mandates]


def politician_detail(db: Session, mandate_id: int) -> PoliticianDetailSchema | None:
    mandate = (
        db.query(Mandate)
        .options(
            selectinload(Mandate.politician),
            selectinload(Mandate.constituency),
            selectinload(Mandate.committee_memberships).selectinload(
                CommitteeMembership.committee
            ),
        )
        .filter(Mandate.id == mandate_id)
        .one_or_none()
    )
    if mandate is None:
        return None
    projects = projects_for_politician(db, mandate.constituency)
    base = politician_list_item(
        mandate,
        {mandate.constituency_id: len(projects)} if mandate.constituency_id else {},
    )
    return PoliticianDetailSchema(**base.model_dump(), projects=projects)


def constituency_list(db: Session) -> list[ConstituencyListItemSchema]:
    """Constituencies of the current period with project and mandate counts."""
    period = current_period(db)
    q = db.query(Constituency)
    if period is not None:
        q = q.filter(Constituency.parliament_period_id == period.id)
    constituencies = q.order_by(Constituency.number).all()

    ids = [constituency.id for constituency in constituencies]
    project_counts = project_counts_by_constituency(db, ids)
    mandates = mandates_for_constituencies(db, ids)

    items: list[ConstituencyListItemSchema] = []
    for constituency in constituencies:
        rows = mandates.get(constituency.id, [])
        items.append(
            ConstituencyListItemSchema(
                id=constituency.id,
                number=constituency.number,
                name=constituency.name,
                state=constituency.state,
                project_count=project_counts.get(constituency.id, 0),
                mandate_count=len(rows),
                has_direct_mandate=any(mandate.is_direct_mandate for mandate in rows),
                has_geometry=constituency.geom is not None,
            )
        )
    return items


def constituency_detail(db: Session, constituency_id: int) -> ConstituencyDetailSchema | None:
    constituency = db.query(Constituency).filter(Constituency.id == constituency_id).one_or_none()
    if constituency is None:
        return None
    mandates = mandates_for_constituencies(db, [constituency.id]).get(constituency.id, [])
    direct, listed = split_mandates(mandates)
    return ConstituencyDetailSchema(
        id=constituency.id,
        number=constituency.number,
        name=constituency.name,
        state=constituency.state,
        projects=projects_for_constituency(db, constituency.id),
        direct_mandates=direct,
        list_mandates=listed,
        has_direct_mandate=bool(direct),
        has_any_mandate=bool(direct or listed),
    )


def project_constituencies(db: Session, project: Project) -> ProjectConstituenciesSchema:
    """Constituencies a project touches, heaviest first, with their MPs.

    A project without a geometry returns an empty list plus ``has_geometry =
    false`` so callers can say *why* there is nothing to show.
    """
    rows = links_for_project(db, project.id)
    mandates_by_constituency = mandates_for_constituencies(
        db, [constituency.id for _, constituency in rows]
    )

    constituencies: list[ProjectConstituencySchema] = []
    for link, constituency in rows:
        direct, listed = split_mandates(mandates_by_constituency.get(constituency.id, []))
        constituencies.append(
            ProjectConstituencySchema(
                id=constituency.id,
                number=constituency.number,
                name=constituency.name,
                state=constituency.state,
                length_km=link.length_km,
                share=link.share,
                overlap_kind=link.overlap_kind,
                direct_mandates=direct,
                list_mandates=listed,
                has_direct_mandate=bool(direct),
                has_any_mandate=bool(direct or listed),
            )
        )

    last_import = last_successful_run(db, IMPORT_KIND_POLITICIANS)
    return ProjectConstituenciesSchema(
        project_id=project.id,
        has_geometry=bool(project.geojson_representation),
        constituencies=constituencies,
        last_import=ImportRunSchema.model_validate(last_import) if last_import else None,
    )
