# Data Models

## Overview

The backend uses a PostgreSQL database with the PostGIS extension.

Tables are grouped into five domains:

- **RailwayInfrastructure** – based on the ERA RINF data model
- **Projects** – planned or executed railway investments and related metadata
- **Parliament** – Bundestag constituencies, mandates and their link to projects
- **Infraplan** – the federal five-year rail infrastructure plan: measure tables and KPIs per year
- **ChangeTracking** – audit log of data modifications

### RailwayInfrastructure

Based on the RINF data model of ERA (https://rinf.era.europa.eu/rinf/).
Full documentation: https://www.era.europa.eu/sites/default/files/2025-03/rinf_application_guide_3.1.0.pdf

See `apps/backend/docs/RINF Railway Infrastructure Data.md` for import details.

| Table | ERA concept | Description |
|---|---|---|
| OperationalPoint | era:OperationalPoint | Stations, junctions, border points |
| SectionOfLine | era:SectionOfLine | Track sections between operational points |
| SOLTrack | era:Track | Individual tracks within a section |
| SOLTrackParameter | era:TrackParameter | Technical parameters of a track |
| PlatformEdge | era:PlatformEdge | Passenger platforms at operational points |
| Tunnel | era:Tunnel | Tunnels along a section of line |
| Bridge | era:Bridge | Bridges along a section of line |
| Siding | era:Siding | Auxiliary tracks linked to operational points |
| SpecialArea | era:SpecialArea | Restricted or functional areas |
| RailwayLocation | era:RailwayLocation | Position along track in kilometres |

### Projects

| Table | Description |
|---|---|
| Project | Metadata container for planned or executed railway investments |
| ProjectGroup | Groups of related projects (e.g. Deutschlandtakt clusters) |
| project_to_project_group | Many-to-many: Project ↔ ProjectGroup |
| Budget | Assigned or expected budget values linked to a project |
| FinVe | Financial commitments (Verpflichtungsermächtigungen) |
| finve_to_project | Many-to-many: FinVe ↔ Project |
| ProjectText | Descriptive or contextual content (sources, explanations) |
| ProjectTextType | Classification of text content (source, summary, quote) |
| text_to_project | Many-to-many: Text ↔ Project |
| BvwpData | Extended metadata for projects listed in the Federal Transport Infrastructure Plan (BVWP) |
| ProjectProgress | Progress state of a project, including date and source |
| project_to_section_of_line | Many-to-many: Project ↔ SectionOfLine |
| project_to_operational_point | Many-to-many: Project ↔ OperationalPoint |
| document | Metadata for files (PDFs, maps) linked to projects |
| document_to_project | Many-to-many: Document ↔ Project |
| ProjectPhase | Structured timeline of milestone events (planning, approval, construction) |
| ProjectUpdateSource | Sources and content of automated data updates to projects |

### Parliament

Constituencies of the Bundestag and the members of parliament responsible for
them, joined to projects through a materialised spatial intersection. See
`docs/features/feature-abgeordnete.md`.

Sources: constituency outlines from Die Bundeswahlleiterin (© GeoBasis-DE / BKG),
people from the abgeordnetenwatch API v2 (CC0).

| Table | Description |
|---|---|
| ParliamentPeriod | One legislative period of one parliament (currently the Bundestag only) |
| Constituency | Wahlkreis: number 1–299, name, Bundesland, outline (`MULTIPOLYGON`, SRID 4326, GiST index) |
| Politician | A person; outlives any single mandate |
| Mandate | One seat in one period: faction, constituency, `is_direct_mandate` (`mandate_won == "constituency"`) |
| Committee | Transport and budget committee of a period |
| CommitteeMembership | Role of a mandate in a committee, strongest role only |
| project_to_constituency | Materialised intersection: kilometres, share and overlap kind (`line` / `point`) per project and constituency |
| ParliamentImportRun | Abrufstand per import run (kind, status, counters), shown in the UI |

### Infraplan

The yearly Infraplan of the federal government (BMV), imported per year
(Jahrgang). No year overwrites another, so costs, commissioning years and KPI
targets form time series. See `docs/features/feature-infraplan-import.md`;
migration `20261015002`.

| Table | Description |
|---|---|
| infraplan_parse_result | Draft per upload: `year`, `status`, parsed rows (`result_json`), plausibility findings (`warnings_json`), KPI chart pages (`kpi_pages_json`), stored PDF (`pdf_path`, for re-parsing and page images), `confirmed_at` |
| infraplan_report | A confirmed year (`year` unique, `published_on`); entries and KPI values cascade with it |
| infraplan_entry | One row of a measure table: `section` (`BP_A`…`BP_D`, `GVFG_A`, `GVFG_C`, `INVKG`) + `lfd_nr` (unique per report), project numbers (`primary_number` indexed, recognition key across years), Realisierungsstand/Lph, commissioning (`ibn_raw`, `ibn_year`, `ibn_qualifier` `OFFEN`/`BIS`/`SPANNE`), cost (`cost_mio`, `cost_kind` `GWU`/`GESAMTKOSTEN`, or a reference `cost_ref_entry_id` → entry carrying the cost), Befassung (`parl_state`), footnotes |
| infraplan_entry_project | Many-to-many: entry ↔ project, with `assignment_source` (`NUMBER`/`FUZZY`/`MANUAL`/`AGENT`) and `note` |
| infraplan_kpi | KPI definition shared by all years: stable `key`, `kind` (`STEUERUNG`/`INFORMATION`), `category`, unit |
| infraplan_kpi_value | One value as published in one year: `report_id` (source year), `year` (reference year), `value_kind` (`IST`/`ZIEL`), optional `series`, `status` (`UNGEPRUEFT`/`GEPRUEFT`); unique per (report, kpi, year, kind, series) |

`progress_observation.infraplan_entry_id` (nullable, `SET NULL`) is the
provenance of observations derived from an entry (source type `INFRAPLAN`).

### ChangeTracking

| Table | Description |
|---|---|
| ChangeLog | High-level log of data modifications (what, when, by whom) |
| ChangeLogEntry | Detailed per-field changes linked to a ChangeLog entry |
