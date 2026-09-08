"""SQLite fallback for PostGIS geometry columns.

Production runs on PostgreSQL/PostGIS; the API test suite runs on SQLite, which
has no spatial types. Geometry columns therefore declare a ``with_variant`` that
stores raw WKB on SQLite — the same approach ``models/routes/route.py`` uses for
the cached route geometries. Spatial *functions* are never available on SQLite,
so every query using them is guarded by a dialect check (see
``services/constituency_matching.py``).
"""

from __future__ import annotations

from geoalchemy2.elements import WKBElement
from sqlalchemy.types import LargeBinary, TypeDecorator


class SqliteGeometry(TypeDecorator):
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
