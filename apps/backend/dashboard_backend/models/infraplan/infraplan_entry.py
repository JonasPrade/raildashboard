from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    Boolean,
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


class InfraplanEntry(Base):
    """One row of a measure table (chapter 2.3) of a confirmed Infraplan year."""

    __tablename__ = "infraplan_entry"
    __table_args__ = (
        UniqueConstraint("report_id", "section", "lfd_nr", name="uq_infraplan_entry_report_section_lfd"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("infraplan_report.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # BP_A | BP_B | BP_C | BP_D | GVFG_A | GVFG_C | INVKG
    section: Mapped[str] = mapped_column(String(10), nullable=False)
    lfd_nr: Mapped[int] = mapped_column(Integer, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # All printed numbers; the first one is the recognition key across years.
    project_numbers: Mapped[list | None] = mapped_column(JSON, nullable=True)
    primary_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    bezeichnung: Mapped[str | None] = mapped_column(Text, nullable=True)
    massnahme: Mapped[str | None] = mapped_column(Text, nullable=True)
    laender: Mapped[str | None] = mapped_column(String(255), nullable=True)

    state_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lph_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lph_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    under_construction: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    baurecht: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    ibn_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ibn_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ibn_qualifier: Mapped[str | None] = mapped_column(String(10), nullable=True)  # OFFEN | BIS | SPANNE

    cost_mio: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    cost_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)  # GWU | GESAMTKOSTEN
    cost_ref_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cost_ref_entry_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("infraplan_entry.id", ondelete="SET NULL"), nullable=True
    )

    parl_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # ABGESCHLOSSEN | LAEUFT | VORGESEHEN | NICHT_VEREINBART
    parl_state: Mapped[str | None] = mapped_column(String(20), nullable=True)

    footnote_refs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    footnotes: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    report = relationship("InfraplanReport", back_populates="entries", foreign_keys=[report_id])
