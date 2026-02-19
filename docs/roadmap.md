# Roadmap
Goal look at `architecture.md`

## Short-Term-Features
Frontend-Fix:
- [ ] Don't forget the selected Groups when changig to Projects. Speichere die gesuchten Projektgruppen im local Storage des Browers und greife immer darauf zurück, sobald Gruppen gesucht werden
- [ ] Mache Karte und Projekte als Kippschalter in der UI, sodass ich immer zwischen Karte oder Liste wählen. Benenne dafür die "Projekte" zu "Liste" um. 
- [ ] Zwischen den einzelnen Abschnitten werden dünne Lücken angezeigt. Diese sollen möglichst verbunden werden, da das die Darstellung stört.
- [ ] Füge eine Option bei Karte und Liste ein. Diese soll auswählbar machen, ob nur ranghöchste Projekte angezeigt werden. Das sind Projekte, die keine superior projects haben.

## Mid-Termin Features
- [ ] Use the service in backend for routing with GrassHopper to generate Routes. The Routes should be suggested in frontend. If accepted the should be added to the specific Project
- [ ]  

## Backend

### RINF Implementation

> **Note:** ERA data has no geo data → project geometries are less complete than initially expected.

See `apps/backend/docs/RINF Railway Infrastructure Data.md` for import details.

- [x] Implement RINF data model to models.py
    - [x] Use XML Schema to create the fitting models.py
- [x] Implement RINF data import
    - [x] Use the serialization possibilities of RINF
    - [x] Add import of border points .csv

### Routing

See `apps/backend/docs/Routing.md` for implementation details.

- [x] Routing algorithm
- [x] Implementation of pgRouting
- [x] Implement test possibilities
- [x] Add possibility for API usage

### Testsq

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
- [ ] Benutzer mit verschiedenen Arbeitsrechten -> Bearbeitung nur nach Login und wenn Bearbeitungsrechte vorliegen

---

## Frontend



## Finished
Frontend-Fix

- [x] Dicke der Linien auf Karte einstellbar machen und standardmäßig dicker
- [x] In Projektansicht oben neben Button "Zur Projektübersicht" einen Button einfügen, der zurück zur Karte führt
