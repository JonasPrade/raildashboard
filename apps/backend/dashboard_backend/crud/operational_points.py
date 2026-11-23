from typing import Optional, Sequence

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from dashboard_backend.models.railway_infrastructure.operational_point import OperationalPoint

# Networks an operational point can belong to: RINF points are main line ("rail"),
# stops imported from OSM (scripts/import_osm_stops.py) are light_rail, subway or tram.
OP_NETWORKS = ("rail", "light_rail", "subway", "tram")


def collapse_spaces(column):
    """SQL expression: runs of spaces in ``column`` collapsed to one (RINF pads names to
    a fixed width). Nested ``replace`` instead of a regex so it runs on every backend;
    six passes collapse runs of up to 64 spaces."""
    expression = column
    for _ in range(6):
        expression = func.replace(expression, "  ", " ")
    return expression


def search_operational_points(
    db: Session,
    query: str,
    limit: int = 20,
    networks: Optional[Sequence[str]] = None,
) -> list[OperationalPoint]:
    """Search operational points by name or op_id, optionally only in the given networks.

    Case-insensitive; every word of the query must occur in the name or op_id, so
    "Westkreuz S-Bahn" finds RINF names padded with spaces ("Berlin Westkreuz      S-Bahn").
    Exact matches (whitespace collapsed) first, then shorter names."""
    words = query.split()
    if not words:
        return []
    normalized = " ".join(words).lower()
    collapsed_name = func.lower(collapse_spaces(OperationalPoint.name))
    exact = or_(collapsed_name == normalized, func.lower(OperationalPoint.op_id) == normalized)
    q = db.query(OperationalPoint)
    for word in words:
        pattern = f"%{word}%"
        q = q.filter(or_(OperationalPoint.name.ilike(pattern), OperationalPoint.op_id.ilike(pattern)))
    if networks:
        q = q.filter(OperationalPoint.network.in_(list(networks)))
    return (
        q.order_by(exact.desc(), func.length(OperationalPoint.name), OperationalPoint.name)
        .limit(limit)
        .all()
    )
