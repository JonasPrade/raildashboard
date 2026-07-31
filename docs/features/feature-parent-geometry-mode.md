# Feature: Geometrie-Modus für Überprojekte (selbst gepflegt vs. aus Unterprojekten)

## Ziel

Ein Überprojekt (ein Projekt mit mindestens einem Unterprojekt) soll seine Geodaten auf der
Karte auf **zwei** Wegen bekommen können — umschaltbar über einen Kippschalter in der
Geometrie-Verwaltung:

1. **Automatisch aus den Unterprojekten** — heutiges Verhalten: die
   `geojson_representation` des Überprojekts wird aus den Geometrien seiner direkten
   Unterprojekte zusammengesetzt (`docs/features/feature-parent-geojson-merge.md`).
2. **Selbst gepflegt** — das Überprojekt hat eine eigene Geometrie (gezeichnet, geroutet,
   hochgeladen), die von Änderungen an den Unterprojekten **nicht** überschrieben wird.

Es geht ausschließlich um die Geometrie des Projekts selbst (Kartendarstellung). Die
Darstellung der Unterprojekte auf der Detailkarte („Karte – Unterprojekte") bleibt unverändert.

## Kontext

Heute ist die Aggregation bedingungslos: sobald ein Unterprojekt seine Geometrie ändert oder
im Baum verschoben wird, überschreibt `recompute_geojson_for_parent()` die Geometrie **jedes**
Vorfahren. Ein Überprojekt kann daher keine eigene, gröbere oder abweichende Linie tragen
(z. B. ein Korridor als durchgehende Strecke, während die Unterprojekte nur einzelne
Ausbauabschnitte abbilden).

## Scope

- Neues Projekt-Feld `geojson_from_subprojects` (Boolean, Default `true` → heutiges Verhalten).
- Aggregations-Kaskade respektiert das Feld.
- Kippschalter in der Geometrie-Verwaltung, sichtbar **nur** wenn das Projekt Unterprojekte hat.
- API lehnt ein direktes Schreiben der Geometrie ab, solange das Projekt im Automatik-Modus
  Unterprojekte hat — sonst würde die nächste Kind-Änderung die Eingabe stillschweigend
  verwerfen.

## Nicht im Scope

- Mischform (eigene Geometrie *zusätzlich* zu der aus den Unterprojekten).
- Änderung der Unterprojekt-Darstellung in der Detailansicht.
- Rückwirkende Migration bestehender Daten: alle Projekte starten im Automatik-Modus.

## Gewünschtes Verhalten

### Feldsemantik

`geojson_from_subprojects` ist nur für Projekte **mit** Unterprojekten wirksam. Für ein
Projekt ohne Unterprojekte bleibt der Wert folgenlos (nichts aggregiert dorthin), er wird aber
mitgeführt, damit ein später hinzugefügtes Unterprojekt sofort den gewünschten Modus vorfindet.

| Wert | Verhalten |
|---|---|
| `true` (Default) | Geometrie wird bei jeder Änderung eines Unterprojekts neu aus dessen Features zusammengesetzt. Direktes Setzen der Geometrie ist gesperrt. |
| `false` | Geometrie gehört dem Projekt selbst. Änderungen an Unterprojekten lassen sie unangetastet; der volle Geometrie-Editor ist verfügbar. |

### Kaskade

Die Aufwärts-Kaskade (`recompute_geojson_for_parent`) **stoppt** an einem Vorfahren mit
`geojson_from_subprojects = false`: dessen Geometrie ändert sich nicht, also ändert sich auch
die daraus abgeleitete Geometrie seiner eigenen Vorfahren nicht.

### Umschalten

- **Automatik → selbst gepflegt:** Die zuletzt aggregierte Geometrie bleibt als Startpunkt
  stehen und kann ab sofort bearbeitet werden. Nichts geht verloren.
- **Selbst gepflegt → Automatik:** Die Geometrie wird sofort aus den Unterprojekten neu
  berechnet (die selbst gepflegte Geometrie wird dabei ersetzt) und die Kaskade läuft nach
  oben weiter. Das Frontend warnt vorher.

### UI

In „Geometrie verwalten" steht bei einem Überprojekt ganz oben der Schalter
**„Geometrie automatisch aus Unterprojekten zusammensetzen"**. Ist er aktiv, treten an die
Stelle aller Bearbeitungs-Bereiche (Löschen, Zeichnen, Route, Betriebsstellen, Upload) ein
erklärender Hinweis; der Speichern-Button entfällt. Die Karte zeigt weiterhin die
zusammengesetzte Geometrie. Ist der Schalter aus, verhält sich der Editor wie bei jedem
anderen Projekt.

## Akzeptanzkriterien

- [ ] Ein Projekt ohne Unterprojekte zeigt den Schalter nicht und verhält sich unverändert.
- [ ] Bei einem Überprojekt im Automatik-Modus sind alle Editor-Bereiche durch den Hinweis ersetzt.
- [ ] Schalter aus → Editor nutzbar; gespeicherte Geometrie überlebt eine Änderung an einem
      Unterprojekt.
- [ ] Schalter wieder an → Geometrie entspricht sofort wieder der Vereinigung der
      Unterprojekt-Features.
- [ ] `PATCH /api/v1/projects/{id}` mit `geojson_representation` auf einem Überprojekt im
      Automatik-Modus antwortet mit HTTP 400.
- [ ] Die Kaskade eines Enkel-Projekts stoppt an einem selbst gepflegten Zwischen-Projekt.

## Technische Notizen

### Betroffene Dateien

| Datei | Änderung |
|---|---|
| `models/projects/project.py` | Spalte `geojson_from_subprojects` (Boolean, `NOT NULL`, Default `true`) |
| `alembic/versions/…_add_geojson_from_subprojects.py` | Migration mit `server_default="true"` |
| `schemas/projects/project_fields_base.py` | `geojson_from_subprojects: Optional[bool]` (Create/Update) |
| `schemas/projects/project_schema.py` | `geojson_from_subprojects: bool = True` (Read) |
| `crud/projects/projects.py` | Kaskade stoppt im Manuell-Modus; Moduswechsel löst Neuberechnung aus; `has_subprojects()` |
| `api/v1/endpoints/projects.py` | HTTP 400 beim direkten Geometrie-Schreiben im Automatik-Modus |
| `shared/api/queries.ts` | `useUpdateProjectGeojsonSource(projectId)` |
| `features/routing/GeometryEditor.tsx` | Schalter + Sperre aller Editier-Bereiche |
| `features/routing/GeometryManagementModal.tsx` | reicht `subProjectCount` durch |
| `features/projects/ProjectDetail.tsx` | übergibt `subProjects.length` |
| `features/changelog/ProjectHistorySection.tsx` | Feld-Label für die Versionshistorie |

### Migration

Additive Spalte mit `server_default="true"` — bestehende Zeilen behalten damit exakt das
heutige Verhalten. Kein Backfill nötig.

## Verifikation

- `cd apps/backend && .venv/bin/python -m pytest tests/unit/test_parent_geometry_mode.py tests/api/test_projects.py`
- `cd apps/frontend && npm run lint && npm run build && npm test`
- Manuell: Überprojekt öffnen → „Geometrie verwalten" → Schalter umlegen, Unterprojekt-Geometrie
  ändern, Ergebnis auf der Karte prüfen.
