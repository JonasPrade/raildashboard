
# Data Models

## Overview
the backend works with a postgresql db with post-gis extension

the tables are sorted by groups
- RailwayInfrastructure
  - OperationalPoint: contains OperationalPoints as in RINF (era:OperationalPoint)
  - SectionOfLine: contains SectionsOfLine as in RINF (era:SectionOfLine)
  - SOLTrack: contains SOLTracks as in RINF (era:Track)
  - SOLTrackParameter: contains SOLTrackParameters as in RINF (era:TrackParameter)
  - PlatformEdge: passenger platforms at OPs (era:PlatformEdge)
  - Tunnel: tunnels along a SectionOfLine (era:Tunnel)
  - Bridge: bridges along a SectionOfLine (era:Bridge)
  - Siding: auxiliary tracks linked to OPs (era:Siding)
  - SpecialArea: restricted or functional areas (era:SpecialArea)
  - RailwayLocation: position along track in kilometers (era:RailwayLocation)
- Projects
  - Project: metadata container for planned or executed railway investments
  - ProjectGroup: groups of related projects (e.g. Deutschlandtakt clusters)
  - project_to_project_group: many-to-many link between Project and ProjectGroup
  - Budget: assigned or expected budget values linked to a project
  - FinVe: financial commitments (Verpflichtungsermächtigungen) associated with a project
  - finve_to_project: many-to-many link between FinVe and Project
  - ProjectText: descriptive or contextual content (e.g. sources, explanations)
  - ProjectTextType: classification of text content (e.g. source, summary, quote)
  - text_to_project: many-to-many link between Text and Project
  - BvwpData: optional extended metadata for projects listed in the Federal Transport Infrastructure Plan (BVWP)
  - ProjectProgress: tracks the progress state of a project, including date and source information
  - project_to_section_of_line: many-to-many link between Project and SectionOfLine
  - project_to_operational_point: many-to-many link between Project and OperationalPoint
  - document: metadata for files (e.g. PDFs, maps) linked to projects
  - document_to_project: many-to-many link between Document and Project
  - ProjectPhase: structured timeline of milestone events (e.g. planning, approval, construction)
  - ProjectUpdateSource: tracks sources and content of automated data updates to projects
- ChangeTracking
  - ChangeLog: high-level log of data modifications (what, when, by whom)
  - ChangeLogEntry: detailed per-field changes linked to ChangeLog

## RailwayInfrastructure
[[RINF Railway Infrastructure Data]]
The RailwayInfrastructure bases on the RINF data model of ERA (https://rinf.era.europa.eu/rinf/)
the documentation is https://www.era.europa.eu/sites/default/files/2025-03/rinf_application_guide_3.1.0.pdf?t=1751549631
