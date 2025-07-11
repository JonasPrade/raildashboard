# Roadmap

## RINF Implementation
[[RINF Railway Infrastructure Data]]


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

## Database Transfer
The aim is to transfer the existing project database to the new system
- [ ] find solution

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
- [ ] Beschleunigungskommission Schiene
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
	- wird später fürs Routing benötigt
- [ ] Routing Algorithmen
	- hier sollte ich überlegen mit PostGIS/pgRouting zu arbeiten