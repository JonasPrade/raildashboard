# Feature: Projekte zusammenführen (Dubletten bereinigen)

**Status: in Umsetzung (2026-10-14)** — Vorstufe zum GVFG-Import
([`feature-gvfg-import.md`](feature-gvfg-import.md)).

## Ziel

Doppelt angelegte Projekte zu **einem** Projekt zusammenführen, ohne dass dabei
Verknüpfungen, Historie oder alte Links verloren gehen. Anlass ist der GVFG-Bestand:
Aus mehreren Importwellen sind rund 48 Dubletten-Gruppen entstanden (gleicher
GVFG-Schlüssel, zwei bis drei Projekte), die vor dem GVFG-Import bereinigt werden
müssen. Die Bereinigung läuft per MCP, deshalb gibt es die Funktion zuerst als
MCP-Tool `merge_projects`.

## Designentscheidungen (mit dem Nutzer abgestimmt, 2026-10-14)

- **Ein Paar pro Aufruf:** `survivor_id` bleibt, `merged_id` geht in ihm auf.
  Keine Sammelaufrufe. Drei Dubletten = zwei Aufrufe.
- **Vorschau zuerst:** `apply=false` ist der Standard und liefert nur, was passieren
  würde (Feldänderungen, umgehängte Verknüpfungen je Tabelle, Warnungen). Erst
  `apply=true` schreibt (Muster wie `route_project_geometry`).
- **Berechtigung `project.merge`** — neu im Katalog, **keiner Systemrolle**
  zugeordnet, also nur Admins (Super-Admin) bzw. explizit vergebene Rollen. Das
  MCP-Tool ist als *destructive* annotiert.
- **Das verworfene Projekt wird gelöscht, alte Links leiten um:** Tabelle
  `project_redirect` (alte id → neue id). `GET /projects/{alte id}` liefert das
  bleibende Projekt, die Detailseite ersetzt die URL. Kein „Geister-Projekt" mit
  `merged_into_id`, das jede Liste/Karte/Suche/MCP-Abfrage ausfiltern müsste.
  Umleitungen, die auf das verworfene Projekt zeigten, werden auf das bleibende
  Projekt umgebogen — keine Ketten.
  **Ausnahme (2026-10-23):** Das Kennzeichen „Archiviert"
  ([`feature-project-archive.md`](feature-project-archive.md)) ist bewusst ein solches
  überall gefiltertes Projekt — aber für einen anderen Fall: Zusammenführen bleibt für
  **Dubletten** (ein Projekt geht im anderen auf); Archivieren ist für **ersetzte oder
  überholte** Projekte, die ihre eigene Historie behalten. `merge_projects` lässt den
  Archiv-Zustand des bleibenden Projekts unverändert.
- **Auch als API-Endpoint** (`POST /api/v1/projects/merge`), gleiche Logik, keine
  eigene Oberfläche vorerst.

## Regeln der Zusammenführung

### Felder des Projekts

- **Das bleibende Projekt gewinnt.** Leere Felder (`NULL` oder leerer Text) werden
  aus dem verworfenen Projekt gefüllt.
- **Eigenschafts-Flags** (`nbs`, `abs`, `elektrification`, …) werden mit ODER
  verknüpft.
- Nicht übernommen: `id`, `name`, `is_draft`, `is_archived`, `archived_reason`,
  `archived_at`, `old_id`, `superior_project_old_id`, `geojson_from_subprojects` — sie bleiben wie beim bleibenden Projekt.
- `superior_project_id` wird nur gefüllt, wenn das bleibende Projekt keines hat
  und die Hierarchie gültig bleibt.

### Geometrie

- `geometry_from="survivor"` (Standard): Geometrie, Länge, gebundene
  Betriebsstellen/Streckenabschnitte und gespeicherte Routen des bleibenden
  Projekts bleiben, die des verworfenen entfallen.
- `geometry_from="merged"`: diese vier Dinge kommen vom verworfenen Projekt (z. B.
  wenn dort die Linie liegt und beim bleibenden nur ein Punkt).
- Hat das bleibende Projekt **keine** Geometrie, gilt automatisch `merged`.
- Danach: Wahlkreis-Zuordnung des bleibenden Projekts neu berechnen, Geometrie der
  übergeordneten Projekte neu aggregieren.

### Verknüpfungen

Jede Tabelle mit Fremdschlüssel auf `project.id` wird behandelt — generisch über
die Metadaten, damit künftige Tabellen nicht vergessen werden:

- **Umhängen** auf das bleibende Projekt (Gruppen, Texte, Dokumente, FinVe-, VIB-,
  PFA-, Fulda-, Bauportal-, Medien-Zuordnungen, Aufgaben, Beobachtungen, Belege
  zum Planungsstand, Text-Änderungsprotokoll …).
- **Doppelte** (gleiche Zeile würde nach dem Umhängen gegen einen Unique-Schlüssel
  verstoßen, z. B. dieselbe Gruppe an beiden) werden beim verworfenen Projekt
  gelöscht.
- **Kinder** des verworfenen Projekts hängen an das bleibende.
- **Änderungsprotokoll:** Die Einträge des verworfenen Projekts wandern zum
  bleibenden (sonst löscht das `ON DELETE CASCADE` sie). Dazu kommt ein Eintrag
  `action="MERGE"` mit den Feldänderungen und `merged_project_id`.

Sonderfälle:

| Tabelle | Regel |
|---|---|
| `project_progress` (1:1) | bleibendes gewinnt; leere redaktionelle Felder/Overrides aus dem verworfenen, `has_planfeststellung` ODER |
| `progress_observation` | manuelle umhängen; abgeleitete (`is_derived`) des verworfenen löschen — sie werden aus den umgehängten Quellen neu erzeugt |
| `bvwp_project_data` | nur übernehmen, wenn das bleibende keine hat |
| `project_to_constituency` | verwerfen, wird aus der Geometrie neu berechnet |
| `project_to_operation_point`, `project_to_section_of_line`, `routes` | folgen der Geometrie-Regel |

Abschließend werden die abgeleiteten Beobachtungen und der Planungsstand des
bleibenden Projekts neu berechnet.

### Abgelehnt wird

- `survivor_id == merged_id`, eines der Projekte existiert nicht.
- Eines ist Vorfahre des anderen (die Zusammenführung würde die Hierarchie
  zerschneiden) — vorher die Hierarchie per `update_project` auflösen.

## Schnittstellen

- MCP: `merge_projects(survivor_id, merged_id, geometry_from="survivor", apply=false)`
- API: `POST /api/v1/projects/merge` mit `{survivor_id, merged_id, geometry_from, apply}`
  → gleiche Antwort wie das Tool (Vorschau bzw. Ergebnis).
- `GET /api/v1/projects/{id}` und MCP `get_project` lösen Umleitungen auf.

## Akzeptanzkriterien

- [ ] Vorschau ändert nichts in der Datenbank.
- [ ] Nach `apply` existiert das verworfene Projekt nicht mehr; alle Verknüpfungen
      hängen am bleibenden, ohne Unique-Verletzung.
- [ ] Änderungsprotokoll des verworfenen Projekts ist am bleibenden sichtbar, plus
      ein MERGE-Eintrag.
- [ ] `GET /projects/{alte id}` liefert das bleibende Projekt; die Detailseite
      springt auf die neue URL.
- [ ] Ohne `project.merge` wird das Tool/der Endpoint abgelehnt.
- [ ] Alembic-Migration nur additiv (neue Tabelle), rückwärtskompatibel.
