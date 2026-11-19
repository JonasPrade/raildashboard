from typing import Optional, Sequence

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from dashboard_backend.models.railway_infrastructure.operational_point import OperationalPoint

# Networks an operational point can belong to: RINF points are main line ("rail"),
# stops imported from OSM (scripts/import_osm_stops.py) are light_rail, subway or tram.
OP_NETWORKS = ("rail", "light_rail", "subway", "tram")


def search_operational_points(
    db: Session,
    query: str,
    limit: int = 20,
    networks: Optional[Sequence[str]] = None,
) -> list[OperationalPoint]:
    """Search operational points by name or op_id (case-insensitive substring match),
    optionally only in the given networks. Exact matches first, then shorter names."""
    if not query:
        return []
    pattern = f"%{query}%"
    lowered = query.lower()
    exact = or_(
        func.lower(OperationalPoint.name) == lowered,
        func.lower(OperationalPoint.op_id) == lowered,
    )
    q = db.query(OperationalPoint).filter(
        or_(
            OperationalPoint.name.ilike(pattern),
            OperationalPoint.op_id.ilike(pattern),
        )
    )
    if networks:
        q = q.filter(OperationalPoint.network.in_(list(networks)))
    return (
        q.order_by(exact.desc(), func.length(OperationalPoint.name), OperationalPoint.name)
        .limit(limit)
        .all()
    )
