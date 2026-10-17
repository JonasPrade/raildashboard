"""GVFG-Bundesprogramm: editions, their projects and amounts.

See docs/features/feature-gvfg-import.md. One ``GvfgProgram`` per edition
(e.g. 2025–2029); an edition can come from several PDFs (2024–2028: main part
and a separate annex). ``GvfgEntry`` is one Vorhaben of an edition, identified by
its normalised key; ``GvfgEntryAmount`` holds its ∑/A/B/C lines with the yearly
aid as ``{period label: amount}`` (the labels are listed on the programme), so
editions with different year columns fit the same schema.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard_backend.models.base import Base

gvfg_entry_project = Table(
    "gvfg_entry_project",
    Base.metadata,
    Column("entry_id", Integer, ForeignKey("gvfg_entry.id", ondelete="CASCADE"), primary_key=True),
    Column("project_id", Integer, ForeignKey("project.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_gvfg_entry_project_project_id", "project_id"),
)


class GvfgProgram(Base):
    __tablename__ = "gvfg_program"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year_from: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    year_to: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    stand: Mapped[date | None] = mapped_column(Date, nullable=True)
    # [{"label", "year_from", "year_to", "kind"}] in column order
    periods: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    has_annex: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    entries: Mapped[list[GvfgEntry]] = relationship(
        "GvfgEntry", back_populates="program", cascade="all, delete-orphan"
    )


class GvfgEntry(Base):
    __tablename__ = "gvfg_entry"
    __table_args__ = (UniqueConstraint("program_id", "key", name="uq_gvfg_entry_program_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gvfg_program.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Normalised "LL X NNNN_S"; the printed spelling stays in key_raw.
    key: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    key_raw: Mapped[str] = mapped_column(String(40), nullable=False)
    land: Mapped[str] = mapped_column(String(40), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)  # kommunal | db
    part: Mapped[str] = mapped_column(String(20), nullable=False)  # finanzrelevant | nachrichtlich
    nr: Mapped[str | None] = mapped_column(String(10), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    lph: Mapped[str | None] = mapped_column(String(20), nullable=True)
    funding_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    funding_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    construction_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    commissioning_planned: Mapped[int | None] = mapped_column(Integer, nullable=True)
    commissioning_actual: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)

    program: Mapped[GvfgProgram] = relationship("GvfgProgram", back_populates="entries")
    amounts: Mapped[list[GvfgEntryAmount]] = relationship(
        "GvfgEntryAmount",
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="GvfgEntryAmount.line_no",
    )
    projects = relationship("Project", secondary=gvfg_entry_project, backref="gvfg_entries")


class GvfgEntryAmount(Base):
    __tablename__ = "gvfg_entry_amount"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gvfg_entry.id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(5), nullable=False)  # SUM | A | B | C
    # True for a ∑ line computed from A/B/C because the PDF printed none.
    computed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cost_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    cost_eligible: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    aid_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    # {period label: amount as string}, e.g. {"1967–2023": "33.42", "2025": "0.85"}
    periods: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    entry: Mapped[GvfgEntry] = relationship("GvfgEntry", back_populates="amounts")


class GvfgParseResult(Base):
    """A parsed PDF waiting for review (or already confirmed)."""

    __tablename__ = "gvfg_parse_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pdf_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    year_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_annex: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # SUCCESS | FAILURE
    # ParseResult.to_json() plus "suggestions" per key
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    parsed_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    username_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmed_by_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
