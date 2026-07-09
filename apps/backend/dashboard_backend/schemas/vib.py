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
    # Leaf subproject this section is assigned to (editor-confirmed). When set,
    # the section's status is materialised on that subproject instead of being
    # flattened onto the parent.
    project_id: Optional[int] = None
    # Read-only fuzzy suggestion (subproject of the viewing project) for the
    # review UI; not persisted.
    suggested_project_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Shared VIB entry content fields
# ---------------------------------------------------------------------------

class VibEntryFieldsBase(BaseModel):
    """Single source of truth for the VIB entry content block.

    Every schema that carries the parsed Vorhaben content (proposed entry,
    confirm input, read schemas, update schema) inherits these fields instead
    of repeating them. ``VibEntryFieldsBase.model_fields`` is also used by
    ``crud/vib.py`` to derive the schema→ORM field mapping.
    """

    vib_name_raw: str                        # full heading name as in PDF
    category: str = "laufend"                # laufend | neu | potentiell | abgeschlossen

    verkehrliche_zielsetzung: Optional[str] = None
    durchgefuehrte_massnahmen: Optional[str] = None
    noch_umzusetzende_massnahmen: Optional[str] = None
    bauaktivitaeten: Optional[str] = None
    teilinbetriebnahmen: Optional[str] = None
    raw_text: Optional[str] = None
    sonstiges: Optional[str] = None          # leftover text: footnotes, preambles, unclassified

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


def _fields_from_orm(cls: type[BaseModel], entry: object) -> dict:
    """Copy every schema field that exists on the ORM object.

    Avoids hand-maintained field-by-field mappers: adding a field to a schema
    (or to ``VibEntryFieldsBase``) automatically flows into the read schemas.
    Computed fields (not present on the ORM object) are set by the caller.
    """
    return {
        name: getattr(entry, name)
        for name in cls.model_fields
        if hasattr(entry, name)
    }


# ---------------------------------------------------------------------------
# Single VIB entry (one Vorhaben block from the PDF)
# ---------------------------------------------------------------------------

class VibEntryProposed(VibEntryFieldsBase):
    """One Vorhaben as extracted from the VIB PDF."""

    vib_section: Optional[str] = None        # e.g. "B.4.1.3"
    vib_lfd_nr: Optional[str] = None         # sequential number within section

    pfa_entries: list[VibPfaEntryProposed] = []
    pfa_raw_markdown: Optional[str] = None  # complete markdown pipe table, unmodified

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

class VibConfirmEntryInput(VibEntryFieldsBase):
    """One entry as submitted in the confirm request (project_ids adjusted by user)."""

    vib_section: Optional[str] = None
    vib_lfd_nr: Optional[str] = None

    pfa_entries: list[VibPfaEntryProposed] = []
    pfa_raw_markdown: Optional[str] = None  # complete markdown pipe table, unmodified
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
    # Assigned leaf subproject + read-only fuzzy suggestion (see VibPfaEntryProposed).
    project_id: Optional[int] = None
    suggested_project_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class _VibEntryForProjectIds(BaseModel):
    """Leading identity fields of VibEntryForProjectSchema.

    Kept in a separate base listed LAST in the bases tuple: pydantic collects
    fields in reverse MRO order, so these fields come first — which pins the
    OpenAPI ``required`` array to ["id", "year", "vib_name_raw", "category"]
    (its order follows field order and is part of the frozen API contract).
    """

    id: int
    year: int                             # from the parent VibReport
    drucksache_nr: Optional[str] = None  # from the parent VibReport


class VibEntryForProjectSchema(VibEntryFieldsBase, _VibEntryForProjectIds):
    """VIB entry as returned in GET /projects/{id}/vib."""

    # NOTE: deliberately has NO vib_lfd_nr (not part of this endpoint's contract).
    category: str  # required here (no default), unlike the input schemas
    vib_section: Optional[str] = None

    ai_extracted: bool = False

    pfa_entries: list[VibPfaEntrySchema] = []
    project_ids: list[int] = []

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_entry(cls, entry) -> "VibEntryForProjectSchema":
        """Build from a VibEntry ORM object with report + projects loaded."""
        data = _fields_from_orm(cls, entry)
        data["year"] = entry.report.year
        data["drucksache_nr"] = entry.report.drucksache_nr
        data["project_ids"] = [p.id for p in entry.projects]
        return cls(**data)


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


# ---------------------------------------------------------------------------
# PATCH entry: update schema + full read schema
# ---------------------------------------------------------------------------

class VibEntryUpdateSchema(VibEntryFieldsBase):
    """All fields optional — only non-None fields are applied."""
    # Inherits the shared content block; overrides only the fields whose
    # optionality differs. vib_section / vib_lfd_nr are deliberately absent
    # (not editable). The entwurfsgeschwindigkeit coercion is inherited.
    vib_name_raw: Optional[str] = None
    category: Optional[str] = None
    status_planung: Optional[bool] = None
    status_bau: Optional[bool] = None
    status_abgeschlossen: Optional[bool] = None
    pfa_entries: Optional[list[VibPfaEntryProposed]] = None
    project_ids: Optional[list[int]] = None


class VibEntryListItemSchema(BaseModel):
    """Lean list item used by wizards to pick confirmed VIB entries."""
    id: int
    vib_name_raw: Optional[str] = None
    report_year: int
    project_ids: list[int] = []

    model_config = ConfigDict(from_attributes=True)


class _VibEntryIds(BaseModel):
    """Leading identity fields of VibEntrySchema.

    Separate base listed LAST in the bases tuple so its fields come first
    (reverse MRO), pinning the OpenAPI ``required`` array to
    ["id", "vib_report_id", "vib_name_raw", "category", "report_year"].
    """

    id: int
    vib_report_id: int


class VibEntrySchema(VibEntryFieldsBase, _VibEntryIds):
    """Full VIB entry as returned by the PATCH endpoint."""

    category: str  # required here (no default), unlike the input schemas
    vib_section: Optional[str] = None
    vib_lfd_nr: Optional[str] = None

    ai_extracted: bool = False
    pfa_entries: list[VibPfaEntrySchema] = []
    project_ids: list[int] = []
    report_year: int

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_entry(cls, entry) -> "VibEntrySchema":
        """Build from a VibEntry ORM object with report + projects loaded."""
        data = _fields_from_orm(cls, entry)
        data["project_ids"] = [p.id for p in entry.projects]
        data["report_year"] = entry.report.year
        return cls(**data)
