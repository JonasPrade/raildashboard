from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


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
    project_status: Optional[str] = None   # "Planung" | "Bau" | None

    pfa_entries: list[VibPfaEntryProposed] = []

    # Matching result — editable by user in review UI
    project_id: Optional[int] = None
    # Auto-suggestion computed during parse (read-only hint for review UI)
    suggested_project_ids: list[int] = []
    # Set to True after LLM extraction has been applied
    ai_extracted: bool = False


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
    """One entry as submitted in the confirm request (project_id adjusted by user)."""

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
    project_status: Optional[str] = None

    pfa_entries: list[VibPfaEntryProposed] = []
    project_id: Optional[int] = None


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

class VibReportSchema(BaseModel):
    id: int
    year: int
    drucksache_nr: Optional[str] = None
    report_date: Optional[date] = None
    imported_at: datetime
    entry_count: int = 0

    model_config = ConfigDict(from_attributes=True)


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
    project_status: Optional[str] = None

    ai_extracted: bool = False

    pfa_entries: list[VibPfaEntrySchema] = []

    model_config = ConfigDict(from_attributes=True)


class VibAiAvailableResponse(BaseModel):
    available: bool
    model: Optional[str] = None
