"""InfraGO-Zustandsbericht: one report per year, asset classes shared by all
years and the values in long format.

See docs/features/feature-zustandsbericht.md ("Datenmodell").
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard_backend.models.base import Base


class ConditionReport(Base):
    """One InfraGO-Zustandsbericht (Jahrgang). Values hang off it, so deleting
    the year removes everything read from it."""

    __tablename__ = "condition_report"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    price_basis: Mapped[str | None] = mapped_column(String(100), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # ENTWURF | FREIGEGEBEN — only released years are public.
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ENTWURF", server_default="ENTWURF"
    )
    # Checks accepted with a reason: [{"at", "by", "scope", "reason", "errors"}].
    accepted_mismatches: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_by_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    released_by_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)

    values = relationship(
        "ConditionValue",
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ConditionAssetClass(Base):
    """An asset class (Anlagenklasse) of the Fahrweg or the Personenbahnhöfe."""

    __tablename__ = "condition_asset_class"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    domain: Mapped[str] = mapped_column(String(20), nullable=False)  # FAHRWEG | PERSONENBAHNHOF
    trade: Mapped[str | None] = mapped_column(String(10), nullable=True)  # KIB | OB | LST | ET
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)  # Stk. | km
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    values = relationship("ConditionValue", back_populates="asset_class", passive_deletes=True)


class ConditionValue(Base):
    """One number of a report.

    ``asset_class_id`` NULL is the total of the scope; ``grade`` is set for the
    grade distributions only; ``reference_year`` is the year the value refers
    to (the previous-year column of the Kennzahlenvergleich carries the year
    before the report).
    """

    __tablename__ = "condition_value"
    __table_args__ = (
        UniqueConstraint(
            "report_id", "domain", "scope", "region", "asset_class_id", "metric", "grade",
            "reference_year",
            name="uq_condition_value",
            # region, asset_class_id and grade are NULL for most values.
            postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("condition_report.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(20), nullable=False)
    scope: Mapped[str] = mapped_column(String(10), nullable=False)  # GESAMT | HLN | FLN | SE | LAND
    region: Mapped[str | None] = mapped_column(String(2), nullable=True)  # Länderkürzel for LAND
    asset_class_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("condition_asset_class.id", ondelete="CASCADE"), nullable=True, index=True
    )
    metric: Mapped[str] = mapped_column(String(30), nullable=False)
    grade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reference_year: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="UNGEPRUEFT", server_default="UNGEPRUEFT"
    )  # UNGEPRUEFT | GEPRUEFT
    entered_by_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    report = relationship("ConditionReport", back_populates="values")
    asset_class = relationship("ConditionAssetClass", back_populates="values")
