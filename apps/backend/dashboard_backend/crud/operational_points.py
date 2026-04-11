from sqlalchemy import or_
from sqlalchemy.orm import Session

from dashboard_backend.models.railway_infrastructure.operational_point import OperationalPoint


def search_operational_points(
    db: Session, query: str, limit: int = 20
) -> list[OperationalPoint]:
    """Search operational points by name or op_id (case-insensitive substring match)."""
    if not query:
        return []
    pattern = f"%{query}%"
    return (
        db.query(OperationalPoint)
        .filter(
            or_(
                OperationalPoint.name.ilike(pattern),
                OperationalPoint.op_id.ilike(pattern),
            )
        )
        .limit(limit)
        .all()
    )
