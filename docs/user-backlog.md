# User-Backlog

Roh-Ideen, Bugs und Wünsche — **bevor** sie strukturierte Issues werden. Einfach
als Bulletpoint anhängen (Titel reicht, ein, zwei Sätze Kontext schaden nicht).

Claude Code verarbeitet diese Einträge zu Beginn einer Sitzung oder auf Zuruf
(„arbeite den Backlog ab") zu vollwertigen GitHub-Issues und entfernt den
jeweiligen Bulletpoint dann hier. Details: `docs/github-projects.md` →
Abschnitt „User-Backlog".

Nichts wird gelöscht, ohne vorher in ein Issue überführt zu sein.

---

<!-- Neue Einträge hierunter, einer pro Bulletpoint: -->

- **VIB-PFA: Geometrie als Vorschlagssignal** (vorgemerkt 2026-10-23, `feature-vib-import.md` → Phase 8, P4): Endpunkte der PFA-Örtlichkeit („A–B“) auf Betriebsstellen abbilden (eingegrenzt auf die Bounding Box des Oberprojekts) und prüfen, ob beide nahe an der Linie eines Teilprojekts liegen — hilft, wo Teilprojekte weder Abschnittsnummer noch Ortsnamen tragen.

- **Admin-Knopf: OSM-Haltestellen einlesen** (vorgemerkt 2026-11-25, `area:ops`/`area:routing`): Der Import (`scripts/import_osm_stops.py`, #363) läuft nur per Skript im Container; im Admin-Bereich gibt es keinen Weg. Celery-Task + Endpunkt mit Berechtigung + Knopf mit Trockenlauf („nur zählen“) und Ergebnisanzeige (created/updated/unchanged je Netz), Overpass-URL aus der Konfiguration. Feature-Doc und `widerspruchs-check` zuerst; die Logik liegt schon in `services/osm_stops.py`.
- **Admin-Oberfläche für die übrigen Wartungsskripte prüfen** (vorgemerkt 2026-11-25, `area:ops`): Was heute nur als Skript im Container geht, soll wo sinnvoll über den Admin-Bereich laufen: Nutzer löschen (`delete_user.py`, Passwort ändern geht per `PATCH /users/{id}/password`), „Infraplan-Entwürfe reparieren“ (`repair_infraplan_full_stops.py`); die Neuberechnungen haben ihren Knopf schon. Zuerst klären, was davon wirklich wiederkehrend ist und was Einmalarbeit bleibt (erster Admin: `create_initial_user.py` bleibt Skript, es gibt vorher kein Login).
