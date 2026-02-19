# Data Models

## Overview

The backend uses a PostgreSQL database with the PostGIS extension.

Tables are grouped into three domains:

- **RailwayInfrastructure** – based on the ERA RINF data model
- **Projects** – planned or executed railway investments and related metadata
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

### ChangeTracking

| Table | Description |
|---|---|
| ChangeLog | High-level log of data modifications (what, when, by whom) |
| ChangeLogEntry | Detailed per-field changes linked to a ChangeLog entry |
