from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Iterable

from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import BigInteger, Column, Float, JSON, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import LargeBinary, TypeDecorator

from dashboard_backend.models.base import Base


def _normalize_waypoints(waypoints: Iterable[dict[str, Any]]) -> list[list[float]]:
    normalized: list[list[float]] = []
    for waypoint in waypoints:
        lat = round(float(waypoint["lat"]), 6)
        lon = round(float(waypoint["lon"]), 6)
        normalized.append([lat, lon])
    return normalized


def route_hash(
    waypoints: Iterable[dict[str, Any]],
    profile: str,
    options: dict[str, Any],
    graph_version: str,
) -> str:
    key = {
        "w": _normalize_waypoints(waypoints),
        "p": profile,
        "o": options,
        "g": graph_version,
    }
    serialized = json.dumps(key, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class _SqliteUUID(TypeDecorator):
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):  # type: ignore[override]
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(str(value)))

    def process_result_value(self, value, dialect):  # type: ignore[override]
        if value is None:
            return None
        return uuid.UUID(str(value))


_UUID_TYPE = _SqliteUUID().with_variant(PG_UUID(as_uuid=True), "postgresql")


class _SqliteGeometry(TypeDecorator):
    impl = LargeBinary
    cache_ok = True

    def __init__(self, srid: int) -> None:
        super().__init__()
        self._srid = srid

    def process_bind_param(self, value, dialect):  # type: ignore[override]
        if value is None:
            return None
        if isinstance(value, WKBElement):
            return bytes(value.data)
        raise TypeError("expected WKBElement for geometry storage")

    def process_result_value(self, value, dialect):  # type: ignore[override]
        if value is None:
            return None
        if isinstance(value, memoryview):
            value = value.tobytes()
        if isinstance(value, (bytes, bytearray)):
            return WKBElement(value, srid=self._srid)
        return value


class Route(Base):
    __tablename__ = "routes"

    id = Column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    project_id = Column(_UUID_TYPE, nullable=False, index=True)
    profile = Column(String, nullable=False)
    graph_version = Column(String, nullable=False)
    distance_m = Column(Float, nullable=False)
    duration_ms = Column(BigInteger, nullable=False)
    _geom_sqlite = _SqliteGeometry(4326)
    _bbox_sqlite = _SqliteGeometry(4326)
    geom = Column(
        _geom_sqlite.with_variant(
            Geography(geometry_type="LINESTRING", srid=4326), "postgresql"
        ),
        nullable=False,
    )
    bbox = Column(
        _bbox_sqlite.with_variant(
            Geography(geometry_type="POLYGON", srid=4326), "postgresql"
        ),
        nullable=True,
    )
    details = Column(JSON, nullable=False, default=dict)
    cache_key = Column(String, nullable=False, unique=True, index=True)
