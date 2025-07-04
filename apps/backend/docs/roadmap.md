# Roadmap

## RINF Implementation
- [ ] Implement RINF data model to models.py
  -   [ ] Create models for PlatformEdge, Tunnel, Bridge, Siding, SpecialArea, RailwayLocation
- [ ] Implement RINF data import
  - [ ] Use the serialization possibilites of RINF (https://data-interop.era.europa.eu/vocabulary)
  - [ ] Add import of border points .csv (https://www.era.europa.eu/domains/registers/rinf_en)
- [ ] Add source ERA to web interface Datenquelle: European Union Agency for Railways (ERA), RINF Register, abgerufen am [Datum]

## Project Implementation
- [ ] Implement project data model to models.py
  - [x] ProjectGroup
  - [x] project_to_project_group
  - [x] Budget
  - [x] FinVe
  - [x] Text
  - [x] TextType
  - [x] text_to_project
  - [x] BvwpData
  - [x] project_to_section_of_line
  - [x] project_to_operational_point
  - [x] document
  - [x] document_to_project
  - [ ] ProjectProgress
  - [ ] ProjectPhase
  - [ ] ProjectUpdateSource
- [ ] check all relationships

## Change Tracking
- [ ] Implement change tracking data model to models.py
  - [ ] ChangeLog
  - [ ] ChangeLogEntry
- [ ] Implement change tracking 
  - [ ] Create ChangeLogEntry for each change in the database
  - [ ] Create ChangeLog for each ChangeLogEntry

## Additional Features 
- [ ] Netzzustandsbericht
- [ ] Beschleunigungskommission Schiene