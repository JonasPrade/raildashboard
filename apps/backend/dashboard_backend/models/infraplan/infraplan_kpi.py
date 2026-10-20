from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard_backend.models.base import Base


class InfraplanKpi(Base):
    """Definition of a Steuerungs-/Informationskennzahl, shared by all years."""

    __tablename__ = "infraplan_kpi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # STEUERUNG | INFORMATION
    # AUS_NEUBAU | BESTANDSNETZ | UEBERGEORDNET
    category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    # How /infraplan draws the KPI (docs/features/feature-infraplan-import.md,
    # "Öffentliche Seite"), editable in the admin settings.
    # None = automatic | split (one chart per series) | grouped (bars side by
    # side) | flow (one year as Herkunft/Einsatz lists).
    chart_layout: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # The sub-series that already is the whole (others are subsets of it).
    total_series: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Key of a KPI drawn into this chart on its own right-hand axis.
    companion_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    companion_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Axis starts just below the values instead of at 0 (rates near 100 %).
    zoomed_axis: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    values = relationship("InfraplanKpiValue", back_populates="kpi", passive_deletes=True)


class InfraplanKpiValue(Base):
    """One KPI value as published in one Infraplan year.

    ``report_id`` is the year the value comes *from*, ``year`` the year it
    refers to — so target values of every year stay side by side.
    """

    __tablename__ = "infraplan_kpi_value"
    __table_args__ = (
        UniqueConstraint(
            "report_id", "kpi_id", "year", "value_kind", "series",
            name="uq_infraplan_kpi_value",
            # ``series`` is NULL for most KPIs; without this two NULLs would
            # count as distinct and let a value be stored twice.
            postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("infraplan_report.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kpi_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("infraplan_kpi.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    value_kind: Mapped[str] = mapped_column(String(10), nullable=False)  # IST | ZIEL
    series: Mapped[str | None] = mapped_column(String(100), nullable=True)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="UNGEPRUEFT", server_default="UNGEPRUEFT"
    )  # UNGEPRUEFT | GEPRUEFT
    entered_by_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    report = relationship("InfraplanReport", back_populates="kpi_values")
    kpi = relationship("InfraplanKpi", back_populates="values")
