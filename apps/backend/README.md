## Backend Schienendashboard



# Schienendashboard – Backend

Dies ist das Backend des Schienendashboards. Es stellt eine REST-API zur Verfügung, über die laufende Schienenprojekte in Deutschland abgerufen werden können.

## Features

- FastAPI-basierte Web-API
- PostgreSQL + PostGIS für Geodaten
- Strukturierte Projekt- und Geometrieverwaltung
- Erweiterbar für RailML-Parser, Dokumente, Metadaten
- HTTP-Basic-Authentifizierung mit Rollenmodell (viewer, editor, admin)

## Additional Files for Using the API

## Authentifizierung und Benutzer

Alle nicht-`GET`-Endpunkte der API verlangen eine HTTP-Basic-Authentifizierung.
Die hinterlegte Rollenlogik unterscheidet zwischen `viewer`, `editor` und
`admin`. Administratoren können neue Benutzer über den Endpunkt
`/api/v1/users/` anlegen.

Für die initiale Einrichtung steht ein Hilfsskript zur Verfügung:

```bash
python scripts/create_initial_user.py --username admin --role admin
```

Das Skript fragt das Passwort interaktiv ab und legt den Benutzer direkt in der
konfigurierten Datenbank an.
