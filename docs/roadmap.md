# Roadmap

## Backend

### RINF Implementation

> **Note:** ERA data has no geo data → project geometries are less complete than initially expected.

See `apps/backend/docs/RINF Railway Infrastructure Data.md` for import details.

- [x] Implement RINF data model to models.py
    - [x] Use XML Schema to create the fitting models.py
- [x] Implement RINF data import
    - [x] Use the serialization possibilities of RINF
    - [x] Add import of border points .csv
- [ ] The RINF Data should be removed completely from project -> not needed anymore

### Routing

See `apps/backend/docs/Routing.md` for implementation details.

- [x] Routing algorithm
- [x] Implementation of pgRouting
- [x] Implement test possibilities
- [x] Add possibility for API usage

### Tests

- [x] Implement test infrastructure
- [x] Create example DB data

### DB Structure

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
- [ ] Check all relationships (uniqueness)

### Database Transfer

Transfer of existing project database to the new system via CSV export + import scripts.

See `apps/backend/docs/Transfer DB for Project.md` and `apps/backend/docs/Connection between DB Open Data and ERA Rinf.md`.

Data to transfer (prioritised):
- **bks** – lower priority
- **finve and budgets** – rebuild from scratch via original source
- **project data** – primary transfer target
- **infrastructure data** – not transferred (railway_lines, railway_nodes, etc.)
- **d-takt data** – ignored
- **texts** – no transfer

### Change Tracking

- [ ] Implement change tracking data model
    - [ ] ChangeLog
    - [ ] ChangeLogEntry
- [ ] Implement change tracking logic (per-field change entries)

### Additional Backend Features

- [ ] Netzzustandsbericht (PDF processing)
- [ ] Haushaltsberichte Tabelle VE (PDF processing + conversion)
- [ ] Beschleunigungskommission Schiene (data transfer + update)
- [ ] BVWP data import from legacy database
- [x] User authentication (HTTP Basic Auth, PBKDF2, roles: viewer / editor / admin)
- [ ] Celery task queue (potentially for routing)
- [ ] OpenStreetMap data connection (broad coverage, but complex for routing queries)
- [ ] DB OpenData connection (https://www.govdata.de/suche/daten/schienennetz-deutsche-bahnddea3)

---

## Frontend

- [ ] Add ERA data source attribution to web interface:
  *Datenquelle: European Union Agency for Railways (ERA), RINF Register, abgerufen am [Datum]*
