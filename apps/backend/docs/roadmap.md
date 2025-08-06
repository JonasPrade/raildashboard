# Roadmap

## RINF Implementation
[[RINF Railway Infrastructure Data]]

- [x] Implement RINF data model to models.py
	- [x] Use XML Schema to create the fitting models.py
- [x] Implement RINF data import
  - [x] Use the serialization possibilites of RINF 
  - [x] Add import of border points .csv (https://www.era.europa.eu/domains/registers/rinf_en)
- [ ] Add source ERA to web interface Datenquelle: European Union Agency for Railways (ERA), RINF Register, abgerufen am [Datum] -> this is something for frontend

## Routing
[[Routing]]
- [x] Routing Algorithmen
	- hier sollte ich überlegen mit PostGIS/pgRouting zu arbeiten
- [x] implementation of the pgRouting
	- Should be possible with via Routings -> in-between-stops
- [x] Implement test possibilites
- [x] add possibility for API Usage
- [x] Achte darauf dass das ein celery task sein wird

## Tests
- [x] Implement test infrastructure
- [x] create example DB-data

## DB Structure
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
	- are they unique


## Database Transfer
The aim is to transfer the existing project database to the new system.

I will transfer all data to csv and then write import skripts. So in case of a new build i have the data available.

- [ ] project data
	- [ ] project_groups
	- [ ] projectcontent_to_group
	- [ ] projectcontent_to_lines
	- [ ] projectcontent_to_railwaystations
	- [ ] project_content
		- this is the new `project` table
		- save the id as `id_old`
		- [ ] the superior project id has to be changed to the new id
			- save old id
			- after commit reconstruct to new id
		- the bvwp data gets ignored -> will be implemented later
		- [ ] some project_id are double?? -> correct that

Which data have to be transfered. It will be clustered to pragmatic usage:
- bks -> will be done later, no prority
	- bks_action
	- bks_cluster
	- bks_handlungsfeld
- finve and budgets  -> i prefer to make that complete new and import it from origin
	- budgets
	- finve
	- finve_to_projectcontent
- project data
	- project_groups
	- projectcontent_to_group
	- projectcontent_to_lines -> how can i transfer that to ERA data?
	- projectcontent_to_railwaystations -> how can i transfer that?
	- projects -> is not needed anymore
	- projects_contents -> is `projects`in the new database
		- i should keep the old id of that so i can match between the db
		- if the transfer ist completely finished, the old_id can be deleted
	- projects_content_progress -> is empty -> ignore that
- the infrastructure data will not be transfered
	- railway_lines
	- railway_nodes
	- railway_points
	- railway_route -> there I should think about
	- railway_stations
	- railway_tunnels
- all d-takt data will be ignored
- all masterarbeit staff will be ignored
- texts -> no transfer 
	- texts
	- text_types
	- texts_to_project

>[!question]
>How do i transfer the additional infrastructure that is not part of ERA data
>- all new build infrastructure for D-Takt etc.


## Change Tracking
- [ ] Implement change tracking data model to models.py
  - [ ] ChangeLog
  - [ ] ChangeLogEntry
- [ ] Implement change tracking 
  - [ ] Create ChangeLogEntry for each change in the database
  - [ ] Create ChangeLog for each ChangeLogEntry

# Additional Features 
- [ ] Netzzustandsbericht
	- PDF Verarbeitung
- [ ] Haushaltsberichte Tabelle VE
	- PDF Verarbeitung
	- Konvertierung in lesbares Format
	- will be made complete new -> for backup there is the old data available
- [ ] Beschleunigungskommission Schiene
	- the table data is available -> just needs an data transfer and ggf. update
- [ ] BVWP data
	- data is available at old database -> can be imported 
- [ ] User Verification
	- Einführung eines Authentifizierungssystems basierend auf **OAuth2 und JWT (JSON Web Tokens)**.
	- Neue Datenbanktabelle `users` zur Speicherung von Benutzerdaten (mit gehashten Passwörtern).
	- Verwendung von `passlib` für sicheres Passwort-Hashing (Bcrypt).
	- FastAPI-Abhängigkeiten (`OAuth2PasswordBearer`) zur Integration der Authentifizierung in API-Endpunkte
	- Implementierung von **Rollenmanagement** (z.B. `is_admin`) für den Zugriff auf geschützte Routen.
	- Refresh-System für Tokens
		- Einführung von **Access Tokens (kurzfristig)** und **Refresh Tokens (langfristig)** für verbesserte Sicherheit und Benutzerfreundlichkeit.
		- Neue Datenbanktabelle `refresh_tokens` zur serverseitigen Verwaltung der Refresh Tokens (für Widerruf und Einmalnutzung).
		- Implementierung eines `/refresh`-Endpunkts zur Generierung neuer Access Tokens.
- [ ] Möglichkeit für Celery Tasks entwickeln
	- könnte ggf fürs Routing Sinn machen
