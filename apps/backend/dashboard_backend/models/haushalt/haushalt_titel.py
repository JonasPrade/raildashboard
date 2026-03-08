from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard_backend.models.base import Base


class HaushaltTitel(Base):
    """Lookup table for Haushaltskapitel/Titel (e.g. Kap. 1202, Titel 891 01)."""

    __tablename__ = "haushalt_titel"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    titel_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    kapitel: Mapped[str] = mapped_column(String(20), nullable=False)
    titel_nr: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    is_nachrichtlich: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    budget_titel_entries: Mapped[list["BudgetTitelEntry"]] = relationship(  # noqa: F821
        "BudgetTitelEntry", back_populates="titel"
    )
