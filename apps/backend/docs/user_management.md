# Benutzerverwaltung und Rollen

Die API verwendet HTTP Basic Authentication. Für alle HTTP-Methoden außer `GET`
ist eine gültige Anmeldung erforderlich. Abhängig von der Rolle des angemeldeten
Kontos werden zusätzliche Berechtigungen überprüft.

## Rollenübersicht

| Rolle  | Beschreibung | Zugriffsrechte |
|--------|--------------|----------------|
| viewer | Lesender Zugriff auf veröffentlichte Daten. | Darf alle `GET`-Endpunkte aufrufen sowie berechnete Antworten (z. B. Routing) abrufen, sofern die Anfrage keine Änderungen an Daten auslöst. |
| editor | Erweiterter Zugriff für redaktionelle Änderungen. | Darf zusätzliche schreibende Endpunkte (z. B. zum Pflegen von Projektdaten) verwenden. |
| admin  | Vollzugriff inklusive Benutzerverwaltung. | Darf Benutzer anlegen, Rollen vergeben und sämtliche Endpunkte nutzen. |

Nicht-`GET`-Endpunkte prüfen automatisch, ob eine Authentifizierung vorhanden ist.
Spezielle Endpunkte (z. B. die Benutzerverwaltung) fordern darüber hinaus eine
konkrete Rolle an.

## Benutzer anlegen

Für den initialen Aufbau steht das Skript `scripts/create_initial_user.py`
zur Verfügung. Es legt per Kommandozeile einen neuen Benutzer an. Typische
Verwendung zum Erstellen eines Administrators:

```bash
python scripts/create_initial_user.py --username admin --role admin
```

Das Skript fragt das Passwort interaktiv ab. Weitere Benutzer lassen sich
anschließend über den geschützten API-Endpunkt `/api/v1/users/` anlegen
(nur für Administratoren).

## Authentifizierung in Anfragen

* Für Tests oder Skripte kann das Authorization-Header-Feld im Basic-Format
  verwendet werden: `Authorization: Basic <base64(username:password)>`.
* API-Clients sollten Passwörter sicher speichern und nur TLS-gesicherte
  Verbindungen verwenden.

Weitere Details zur Einbindung in Tests und Services finden sich in den
API-spezifischen Modulen (`dashboard_backend/core/security.py`).

