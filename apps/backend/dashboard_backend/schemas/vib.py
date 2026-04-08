from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator


# ---------------------------------------------------------------------------
# PFA entry (one row in the Planfeststellungsabschnitt table)
# ---------------------------------------------------------------------------

class VibPfaEntryProposed(BaseModel):
    """One row from the PFA table extracted from the PDF."""

    abschnitt_label: Optional[str] = None   # e.g. "1. Baustufe"
    nr_pfa: Optional[str] = None
    oertlichkeit: Optional[str] = None
    entwurfsplanung: Optional[str] = None
    abschluss_finve: Optional[str] = None
    datum_pfb: Optional[str] = None
    baubeginn: Optional[str] = None
    inbetriebnahme: Optional[str] = None


# ---------------------------------------------------------------------------
# Single VIB entry (one Vorhaben block from the PDF)
# ---------------------------------------------------------------------------

class VibEntryProposed(BaseModel):
    """One Vorhaben as extracted from the VIB PDF."""

    vib_section: Optional[str] = None        # e.g. "B.4.1.3"
    vib_lfd_nr: Optional[str] = None         # sequential number within section
    vib_name_raw: str                         # full heading name as in PDF
    category: str = "laufend"                # laufend | neu | potentiell | abgeschlossen

    verkehrliche_zielsetzung: Optional[str] = None
    durchgefuehrte_massnahmen: Optional[str] = None
    noch_umzusetzende_massnahmen: Optional[str] = None
    bauaktivitaeten: Optional[str] = None
    teilinbetriebnahmen: Optional[str] = None
    raw_text: Optional[str] = None

    strecklaenge_km: Optional[float] = None
    gesamtkosten_mio_eur: Optional[float] = None
    entwurfsgeschwindigkeit: Optional[str] = None
    planungsstand: Optional[str] = None

    @field_validator("entwurfsgeschwindigkeit", mode="before")
    @classmethod
    def coerce_geschwindigkeit_to_str(cls, v: object) -> str | None:
        """LLMs sometimes return this as an integer (e.g. 160). Coerce to string."""
        if v is None:
            return None
        return str(v) if not isinstance(v, str) else v

    # Project phase status (multiple can be true simultaneously)
    status_planung: bool = False
    status_bau: bool = False
    status_abgeschlossen: bool = False

    pfa_entries: list[VibPfaEntryProposed] = []
    pfa_raw_markdown: Optional[str] = None  # complete markdown pipe table, unmodified
    sonstiges: Optional[str] = None         # leftover text: footnotes, preambles, unclassified

    # Matching result — editable by user in review UI (m:n: multiple projects allowed)
    project_ids: list[int] = []
    # Auto-suggestion computed during parse (read-only hint for review UI)
    suggested_project_ids: list[int] = []
    # Set to True after LLM extraction has been applied
    ai_extracted: bool = False
    # Set to True when LLM extraction was attempted but failed for this entry
    ai_extraction_failed: bool = False
    # Short error description when ai_extraction_failed=True (e.g. "429 capacity exceeded")
    ai_extraction_error: Optional[str] = None


# ---------------------------------------------------------------------------
# Full task result (stored in Celery result backend / Redis)
# ---------------------------------------------------------------------------

class VibParseTaskResult(BaseModel):
    """Complete result returned by the parse_vib_pdf Celery task."""

    year: int
    drucksache_nr: Optional[str] = None
    report_date: Optional[str] = None   # ISO date string or None
    entries: list[VibEntryProposed] = []


# ---------------------------------------------------------------------------
# Confirm request / response
# ---------------------------------------------------------------------------

class VibConfirmEntryInput(BaseModel):
    """One entry as submitted in the confirm request (project_ids adjusted by user)."""

    vib_section: Optional[str] = None
    vib_lfd_nr: Optional[str] = None
    vib_name_raw: str
    category: str = "laufend"

    verkehrliche_zielsetzung: Optional[str] = None
    durchgefuehrte_massnahmen: Optional[str] = None
    noch_umzusetzende_massnahmen: Optional[str] = None
    bauaktivitaeten: Optional[str] = None
    teilinbetriebnahmen: Optional[str] = None
    raw_text: Optional[str] = None

    strecklaenge_km: Optional[float] = None
    gesamtkosten_mio_eur: Optional[float] = None
    entwurfsgeschwindigkeit: Optional[str] = None
    planungsstand: Optional[str] = None

    @field_validator("entwurfsgeschwindigkeit", mode="before")
    @classmethod
    def coerce_geschwindigkeit_to_str(cls, v: object) -> str | None:
        if v is None:
            return None
        return str(v) if not isinstance(v, str) else v

    status_planung: bool = False
    status_bau: bool = False
    status_abgeschlossen: bool = False

    pfa_entries: list[VibPfaEntryProposed] = []
    pfa_raw_markdown: Optional[str] = None  # complete markdown pipe table, unmodified
    sonstiges: Optional[str] = None         # leftover text: footnotes, preambles, unclassified
    project_ids: list[int] = []


class VibConfirmRequest(BaseModel):
    task_id: str
    year: int
    drucksache_nr: Optional[str] = None
    report_date: Optional[str] = None
    entries: list[VibConfirmEntryInput] = []


class VibConfirmResponse(BaseModel):
    report_id: int
    entries_created: int
    pfa_entries_created: int


# ---------------------------------------------------------------------------
# Report list schema
# ---------------------------------------------------------------------------

def _as_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (UTC). Treats naive datetimes as UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class VibReportSchema(BaseModel):
    id: int
    year: int
    drucksache_nr: Optional[str] = None
    report_date: Optional[date] = None
    imported_at: datetime
    entry_count: int = 0

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("imported_at")
    def serialize_imported_at(self, dt: datetime) -> str:
        return _as_utc(dt).isoformat()


# ---------------------------------------------------------------------------
# Project-detail view: VIB entries linked to a specific project
# ---------------------------------------------------------------------------

class VibPfaEntrySchema(BaseModel):
    id: int
    abschnitt_label: Optional[str] = None
    nr_pfa: Optional[str] = None
    oertlichkeit: Optional[str] = None
    entwurfsplanung: Optional[str] = None
    abschluss_finve: Optional[str] = None
    datum_pfb: Optional[str] = None
    baubeginn: Optional[str] = None
    inbetriebnahme: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class VibEntryForProjectSchema(BaseModel):
    """VIB entry as returned in GET /projects/{id}/vib."""

    id: int
    year: int                             # from the parent VibReport
    drucksache_nr: Optional[str] = None  # from the parent VibReport
    vib_section: Optional[str] = None
    vib_name_raw: str
    category: str

    bauaktivitaeten: Optional[str] = None
    teilinbetriebnahmen: Optional[str] = None
    verkehrliche_zielsetzung: Optional[str] = None
    durchgefuehrte_massnahmen: Optional[str] = None
    noch_umzusetzende_massnahmen: Optional[str] = None
    raw_text: Optional[str] = None

    strecklaenge_km: Optional[float] = None
    gesamtkosten_mio_eur: Optional[float] = None
    entwurfsgeschwindigkeit: Optional[str] = None
    planungsstand: Optional[str] = None

    status_planung: bool = False
    status_bau: bool = False
    status_abgeschlossen: bool = False

    ai_extracted: bool = False

    pfa_entries: list[VibPfaEntrySchema] = []

    model_config = ConfigDict(from_attributes=True)


class VibDraftSchema(BaseModel):
    """Metadata for an unconfirmed VIB draft (excludes the raw JSON payload)."""

    task_id: str
    year: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime) -> str:
        return _as_utc(dt).isoformat()


class VibAiAvailableResponse(BaseModel):
    available: bool
    model: Optional[str] = None


class VibOcrAvailableResponse(BaseModel):
    available: bool
    model: Optional[str] = None
