"""Constituency and members-of-parliament endpoints.

Mounted under ``/parliament``. **Reading is public** — like every other ``GET``
in this API (``AuthRouter`` only gates non-GET methods). The assignment is public
information about officeholders from a CC0 source; there is no reason in the
permission model to put it behind ``editor``. Writing means *importing*, and that
gets its own capability ``parliament.import``: not because of the data, but
because a run triggers external requests and overwrites existing rows.
"""

from __future__ import annotations

import json

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from dashboard_backend.core.security import require_permission
from dashboard_backend.crud import parliament as parliament_crud
from dashboard_backend.database import get_db
from dashboard_backend.models.parliament import (
    COMMITTEE_KEY_BUDGET,
    COMMITTEE_KEY_TRANSPORT,
    CommitteeMembership,
    Constituency,
    IMPORT_KIND_CONSTITUENCIES,
    IMPORT_KIND_LINKS,
    IMPORT_KIND_POLITICIANS,
    Mandate,
)
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.parliament import (
    CommitteeSchema,
    ConstituencyDetailSchema,
    ConstituencyListItemSchema,
    ImportRunSchema,
    ParliamentPeriodSchema,
    ParliamentStatusSchema,
    PoliticianDetailSchema,
    PoliticianListItemSchema,
)
from dashboard_backend.schemas.tasks import TaskLaunchResponse

router = AuthRouter()

VALID_COMMITTEE_KEYS = {COMMITTEE_KEY_TRANSPORT, COMMITTEE_KEY_BUDGET}

# Shown wherever the outlines are drawn.
GEOMETRY_ATTRIBUTION = (
    "Wahlkreisgeometrien: Die Bundeswahlleiterin, © GeoBasis-DE / BKG"
)


@router.get("/status", response_model=ParliamentStatusSchema)
def read_status(db: Session = Depends(get_db)):
    """Abrufstand, key figures and how much of the portfolio is covered."""
    period = parliament_crud.current_period(db)
    politician_run = parliament_crud.last_successful_run(db, IMPORT_KIND_POLITICIANS)
    return ParliamentStatusSchema(
        period=ParliamentPeriodSchema.model_validate(period) if period else None,
        last_politician_import=(
            ImportRunSchema.model_validate(politician_run) if politician_run else None
        ),
        last_constituency_import=_run_schema(
            parliament_crud.last_successful_run(db, IMPORT_KIND_CONSTITUENCIES)
        ),
        last_link_run=_run_schema(parliament_crud.last_run(db, IMPORT_KIND_LINKS)),
        is_stale=parliament_crud.is_stale(politician_run),
        stale_after_days=parliament_crud.STALE_AFTER_DAYS,
        counts=parliament_crud.counts(db),
        coverage=parliament_crud.coverage(db),
        fractions=parliament_crud.fractions(db),
        committees=[
            CommitteeSchema(key=committee.key, label=committee.label, member_count=count)
            for committee, count in parliament_crud.committee_counts(db)
        ],
        geometry_attribution=GEOMETRY_ATTRIBUTION,
    )


def _run_schema(run) -> ImportRunSchema | None:
    return ImportRunSchema.model_validate(run) if run else None


@router.get("/politicians", response_model=list[PoliticianListItemSchema])
def read_politicians(
    query: str | None = Query(default=None, description="Namensteil"),
    committee: str | None = Query(default=None, description="verkehr | haushalt"),
    fraction: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """The working list before an appointment: name search + committee/faction filter."""
    if committee and committee not in VALID_COMMITTEE_KEYS:
        raise HTTPException(status_code=400, detail=f"unknown committee: {committee}")

    mandates = parliament_crud.politician_rows(
        db, query=query, committee=committee, fraction=fraction
    )
    counts = parliament_crud.project_counts_by_constituency(
        db, {mandate.constituency_id for mandate in mandates if mandate.constituency_id}
    )
    return [_politician_list_item(mandate, counts) for mandate in mandates]


def _politician_list_item(mandate: Mandate, counts: dict[int, int]) -> PoliticianListItemSchema:
    schema = parliament_crud.mandate_to_schema(mandate)
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
        constituency=(
            parliament_crud.constituency_summary(constituency) if constituency else None
        ),
        committees=schema.committees,
        project_count=counts.get(mandate.constituency_id, 0) if mandate.constituency_id else 0,
    )


@router.get("/politicians/{mandate_id}", response_model=PoliticianDetailSchema)
def read_politician(mandate_id: int, db: Session = Depends(get_db)):
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
        raise HTTPException(status_code=404, detail="Mandat nicht gefunden")

    projects = parliament_crud.projects_for_politician(db, mandate.constituency)
    base = _politician_list_item(
        mandate,
        {mandate.constituency_id: len(projects)} if mandate.constituency_id else {},
    )
    return PoliticianDetailSchema(**base.model_dump(), projects=projects)


@router.get("/constituencies", response_model=list[ConstituencyListItemSchema])
def read_constituencies(db: Session = Depends(get_db)):
    period = parliament_crud.current_period(db)
    q = db.query(Constituency)
    if period is not None:
        q = q.filter(Constituency.parliament_period_id == period.id)
    constituencies = q.order_by(Constituency.number).all()

    ids = [constituency.id for constituency in constituencies]
    project_counts = parliament_crud.project_counts_by_constituency(db, ids)
    mandates = parliament_crud.mandates_for_constituencies(db, ids)

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


@router.get("/constituencies/geojson")
def read_constituencies_geojson(
    tolerance: float = Query(
        default=0.002,
        ge=0.0,
        le=0.05,
        description="Vereinfachung in Grad (0 = Rohgeometrie)",
    ),
    db: Session = Depends(get_db),
):
    """Outlines as a map layer, simplified so the map stays responsive.

    0.002° is roughly 150 m — the same order the prototype used, fine enough for
    a constituency outline and small enough to ship to the browser.
    """
    from sqlalchemy import text

    if not _is_postgres(db):
        return {"type": "FeatureCollection", "features": [], "attribution": GEOMETRY_ATTRIBUTION}

    period = parliament_crud.current_period(db)
    rows = db.execute(
        text(
            """
            SELECT c.id, c.number, c.name, c.state,
                   ST_AsGeoJSON(
                       CASE WHEN :tolerance > 0
                            THEN ST_SimplifyPreserveTopology(c.geom, :tolerance)
                            ELSE c.geom END
                   ) AS geometry
            FROM constituency c
            WHERE c.geom IS NOT NULL
              AND (:period_id IS NULL OR c.parliament_period_id = :period_id)
            ORDER BY c.number
            """
        ),
        {"tolerance": tolerance, "period_id": period.id if period else None},
    ).mappings().all()

    return {
        "type": "FeatureCollection",
        "attribution": GEOMETRY_ATTRIBUTION,
        "features": [
            {
                "type": "Feature",
                "id": row["id"],
                "geometry": json.loads(row["geometry"]),
                "properties": {
                    "constituency_id": row["id"],
                    "number": row["number"],
                    "name": row["name"],
                    "state": row["state"],
                },
            }
            for row in rows
        ],
    }


def _is_postgres(db: Session) -> bool:
    bind = db.get_bind()
    return bool(bind is not None and bind.dialect.name == "postgresql")


@router.get("/constituencies/{constituency_id}", response_model=ConstituencyDetailSchema)
def read_constituency(constituency_id: int, db: Session = Depends(get_db)):
    constituency = db.query(Constituency).filter(Constituency.id == constituency_id).one_or_none()
    if constituency is None:
        raise HTTPException(status_code=404, detail="Wahlkreis nicht gefunden")

    mandates = parliament_crud.mandates_for_constituencies(db, [constituency.id]).get(
        constituency.id, []
    )
    direct, listed = parliament_crud.split_mandates(mandates)
    return ConstituencyDetailSchema(
        id=constituency.id,
        number=constituency.number,
        name=constituency.name,
        state=constituency.state,
        projects=parliament_crud.projects_for_constituency(db, constituency.id),
        direct_mandates=direct,
        list_mandates=listed,
        has_direct_mandate=bool(direct),
        has_any_mandate=bool(direct or listed),
    )


@router.post("/import", response_model=TaskLaunchResponse, status_code=202)
def start_import(
    current_user: User = Depends(require_permission("parliament.import")),
    db: Session = Depends(get_db),
):
    """Refresh the members of parliament from abgeordnetenwatch."""
    from dashboard_backend.tasks.parliament import refresh_parliament_data

    task = refresh_parliament_data.delay(user_id=current_user.id)
    return TaskLaunchResponse(task_id=task.id)


@router.post("/recompute-links", response_model=TaskLaunchResponse, status_code=202)
def start_recompute_links(
    current_user: User = Depends(require_permission("parliament.import")),
    db: Session = Depends(get_db),
):
    """Rebuild ``project_to_constituency`` for the whole portfolio."""
    from dashboard_backend.tasks.parliament import rebuild_constituency_links

    task = rebuild_constituency_links.delay(user_id=current_user.id)
    return TaskLaunchResponse(task_id=task.id)
