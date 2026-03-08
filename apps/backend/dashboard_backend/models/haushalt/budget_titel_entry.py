from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard_backend.models.base import Base


class BudgetTitelEntry(Base):
    """Normalized per-titel sub-entry for a Budget row."""

    __tablename__ = "budget_titel_entry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    budget_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    titel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("haushalt_titel.id"), nullable=False, index=True
    )

    cost_estimate_last_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_estimate_aktuell: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verausgabt_bis: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bewilligt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ausgabereste_transferred: Mapped[int | None] = mapped_column(Integer, nullable=True)
    veranschlagt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vorhalten_future: Mapped[int | None] = mapped_column(Integer, nullable=True)

    budget: Mapped["Budget"] = relationship("Budget", back_populates="titel_entries")  # noqa: F821
    titel: Mapped["HaushaltTitel"] = relationship(  # noqa: F821
        "HaushaltTitel", back_populates="budget_titel_entries"
    )

    __table_args__ = (UniqueConstraint("budget_id", "titel_id", name="uq_budget_titel"),)
