"""Constituency and members-of-parliament endpoints.

Mounted under ``/parliament``. **Reading requires a login** (any role) — unlike
most other ``GET``s in this API, the members of parliament are only shown to
signed-in users, so every read route carries ``_require_login`` explicitly
(``AuthRouter`` only gates non-GET methods on its own). Writing means
*importing*, and that gets its own capability ``parliament.import``: not because
of the data, but because a run triggers external requests and overwrites
existing rows.
"""

from __future__ import annotations

import json

from fastapi import Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from dashboard_backend.api.deps import launch_with_staged_file, read_upload_within_limit
from dashboard_backend.core.security import require_auth, require_permission
from dashboard_backend.crud import parliament as parliament_crud
from dashboard_backend.database import get_db
from dashboard_backend.models.parliament import (
    COMMITTEE_KEY_BUDGET,
    COMMITTEE_KEY_TRANSPORT,
    IMPORT_KIND_CONSTITUENCIES,
    IMPORT_KIND_LINKS,
    IMPORT_KIND_POLITICIANS,
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
from dashboard_backend.services.parliament_import import (
    ConstituencyFileError,
    parse_constituency_geojson,
)

router = AuthRouter()

# Any signed-in user may read; anonymous visitors get 401.
_require_login = Depends(require_auth())

VALID_COMMITTEE_KEYS = {COMMITTEE_KEY_TRANSPORT, COMMITTEE_KEY_BUDGET}

# Shown wherever the outlines are drawn.
GEOMETRY_ATTRIBUTION = (
    "Wahlkreisgeometrien: Die Bundeswahlleiterin, © GeoBasis-DE / BKG"
)
GEOMETRY_SOURCE = "Die Bundeswahlleiterin, © GeoBasis-DE / BKG"
# abgeordnetenwatch parliament-period id of "Bundestag 2025 - 2029" — used when
# no period has been imported yet.
DEFAULT_PERIOD_EXTERNAL_ID = 161


@router.get("/status", response_model=ParliamentStatusSchema, dependencies=[_require_login])
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


@router.get("/politicians", response_model=list[PoliticianListItemSchema], dependencies=[_require_login])
def read_politicians(
    query: str | None = Query(default=None, description="Namensteil"),
    committee: str | None = Query(default=None, description="verkehr | haushalt"),
    fraction: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """The working list before an appointment: name search + committee/faction filter."""
    if committee and committee not in VALID_COMMITTEE_KEYS:
        raise HTTPException(status_code=400, detail=f"unknown committee: {committee}")
    return parliament_crud.politician_list(db, query=query, committee=committee, fraction=fraction)


@router.get("/politicians/{mandate_id}", response_model=PoliticianDetailSchema, dependencies=[_require_login])
def read_politician(mandate_id: int, db: Session = Depends(get_db)):
    detail = parliament_crud.politician_detail(db, mandate_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Mandat nicht gefunden")
    return detail


@router.get("/constituencies", response_model=list[ConstituencyListItemSchema], dependencies=[_require_login])
def read_constituencies(db: Session = Depends(get_db)):
    return parliament_crud.constituency_list(db)


@router.get("/constituencies/geojson", dependencies=[_require_login])
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


@router.get("/constituencies/{constituency_id}", response_model=ConstituencyDetailSchema, dependencies=[_require_login])
def read_constituency(constituency_id: int, db: Session = Depends(get_db)):
    detail = parliament_crud.constituency_detail(db, constituency_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Wahlkreis nicht gefunden")
    return detail


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


@router.post("/constituencies/import", response_model=TaskLaunchResponse, status_code=202)
async def start_constituency_import(
    geojson: UploadFile = File(..., description="Wahlkreisgeometrien als GeoJSON (WGS 84)"),
    election_year: int = Form(..., ge=1949, le=2100),
    period_external_id: int | None = Form(
        default=None, description="abgeordnetenwatch-Wahlperiode; leer = aktuelle"
    ),
    current_user: User = Depends(require_permission("parliament.import")),
    db: Session = Depends(get_db),
):
    """Upload the constituency outlines and rebuild the project links afterwards.

    The file is checked here (JSON, features, coordinates in degrees) so a wrong
    file fails at once; the import itself and the ``ST_Intersection`` rebuild
    run in the worker. Without an explicit period the outlines go to the current
    one — after a new election, refresh the members of parliament first.
    """
    raw = await read_upload_within_limit(geojson)
    try:
        parse_constituency_geojson(raw)
    except ConstituencyFileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if period_external_id is None:
        period = parliament_crud.current_period(db)
        period_external_id = period.external_id if period else DEFAULT_PERIOD_EXTERNAL_ID

    from dashboard_backend.tasks.parliament import import_constituency_file

    task = launch_with_staged_file(
        import_constituency_file,
        raw,
        ".geojson",
        period_external_id=period_external_id,
        election_year=election_year,
        source=GEOMETRY_SOURCE,
        user_id=current_user.id,
    )
    return TaskLaunchResponse(task_id=task.id)
