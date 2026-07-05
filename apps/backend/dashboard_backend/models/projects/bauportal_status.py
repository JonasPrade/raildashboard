"""Raw record fetched from the DB-Bauportal open API (#47).

One row per Bauportal project (`bauportal_id`). The importer upserts these from
``GET bauprojekte.deutschebahn.com/api/getProjectsList`` and fuzzy-matches each
to one of our projects. Once an editor confirms a match (``project_id`` set),
``sync_derived_observations`` materialises a derived BAUPORTAL observation from
``status_raw``. The raw snapshot is kept so the mapping can be re-derived without
re-fetching.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from dashboard_backend.models.base import Base


class BauportalStatus(Base):
    __tablename__ = "bauportal_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # External Bauportal project id (stable key for upserts).
    bauportal_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    parent_bauportal_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    shorttitle: Mapped[str] = mapped_column(String(500), nullable=False)
    # icon_title — the clean status indicator ("Projekt in der Bauphase" etc.).
    status_raw: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # projecttime — build period or status text ("2025 – 2027", "in Planung").
    projecttime_raw: Mapped[str | None] = mapped_column(String(120), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Full API record as JSON string, so the mapping survives schema tweaks.
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Fuzzy-match suggestion (transient guidance for the review UI) and the
    # assigned match. Mirroring the Fulda-Runde importer, the suggestion is
    # pre-filled into ``project_id`` on import so the editor only reviews it;
    # materialisation happens once ``confirmed`` is set (not on mere assignment).
    suggested_project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("project.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("project.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Editor-confirmed the assigned match; only confirmed rows materialise a
    # derived BAUPORTAL observation.
    confirmed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<BauportalStatus(bauportal_id={self.bauportal_id}, "
            f"title={self.shorttitle!r}, status={self.status_raw!r}, "
            f"project_id={self.project_id})>"
        )
