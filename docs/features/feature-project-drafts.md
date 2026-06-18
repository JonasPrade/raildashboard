# Feature: Projekt-Entwürfe (Drafts)

## Ziel

Das Anlegen neuer Projekte über den Wizard soll **zwischengespeichert** werden
können. Ein Projekt, das im Wizard begonnen, aber noch nicht abgeschlossen wurde,
ist ein **Entwurf** und bleibt es, bis es bewusst **finalisiert** wird. Entwürfe
sind nicht öffentlich sichtbar, sondern werden im Adminboard verwaltet und dort
fertiggestellt.

## Hintergrund

Ein Projekt entsteht bereits in **Wizard-Schritt 1 (Stammdaten)** in der Datenbank
(`POST /api/v1/projects/`); die Folgeschritte (Geometrie, Eigenschaften, FinVes,
VIB) patchen dieses Projekt. „Zwischenspeichern" passiert dadurch faktisch schon
serverseitig — es fehlte bislang nur:

1. eine Markierung „noch nicht fertig" (Entwurf),
2. das Ausblenden unfertiger Projekte aus der öffentlichen Liste/Karte
   (bisher liefert `GET /projects/` **alle** Projekte ohne Filter),
3. eine Admin-Ansicht zum Weiterbearbeiten/Finalisieren/Verwerfen.

## Designentscheidungen

- **Statusmodell:** Boolean `is_draft` auf dem `Project`-Modell.
  - Neue Projekte aus dem Wizard werden mit `is_draft = true` angelegt.
  - **Finalisieren = expliziter Schritt** (`is_draft = false`) über einen
    „Projekt fertigstellen"-Button (im Wizard-Footer oder im Adminboard).
  - Bestehende Projekte (Migration) werden auf `is_draft = false` gesetzt, damit
    sie sichtbar bleiben.
- **Sichtbarkeit:** Entwürfe werden aus der öffentlichen Projektliste/Karte
  (`GET /projects/`) **ausgeblendet** und sind nur im Adminboard sichtbar.
  `GET /projects/{id}` liefert weiterhin auch Entwürfe (zum Weiterbearbeiten).
- **Verwaltung:** Eigene Seite `/admin/drafts`, verlinkt aus der Admin-Übersicht
  (mit Anzahl-Badge). Aktionen je Entwurf: **Weiter bearbeiten**,
  **Fertigstellen**, **Verwerfen**.

## Umfang

### Backend
- `Project.is_draft` (Boolean, NOT NULL, default `false`) + Migration
  (bestehende Zeilen → `false`).
- `is_draft` in `ProjectFieldsBase` (Create/Update) und `ProjectSchema` (Output).
- CRUD:
  - `get_projects(db)` → nur finalisierte (`is_draft == false`).
  - `get_draft_projects(db)` → nur Entwürfe.
  - `finalize_project(db, id)` → setzt `is_draft = false`.
  - `delete_project(db, id)` → löscht ein Projekt (für „Verwerfen").
- Endpunkte:
  - `GET /projects/` — nur finalisierte (unverändert öffentlich).
  - `GET /projects/drafts` — Entwurfsliste (`project.create`).
  - `POST /projects/{id}/finalize` — finalisieren (`project.create`).
  - `DELETE /projects/{id}` — verwerfen/löschen (`project.delete`).

### Frontend
- `ProjectCreatePayload.is_draft`, `ProjectUpdatePayload.is_draft`.
- Wizard Schritt 1 legt Projekte mit `is_draft: true` an; unterstützt zusätzlich
  einen **Resume-Modus** (vorhandenen Entwurf bearbeiten → PATCH statt POST).
- Wizard-Footer: „Als Entwurf speichern" (verlassen, bleibt Entwurf) und
  „Projekt fertigstellen" (finalisieren + zur Projektdetailseite).
- Neue Seite `features/admin/drafts/DraftsPage.tsx` unter `/admin/drafts`
  (Weiter bearbeiten / Fertigstellen / Verwerfen).
- Admin-Übersicht: Karte „Projekt-Entwürfe" mit Anzahl-Badge.
- Resume-Route: `/admin/projects/new/:projectId`.

## Akzeptanzkriterien

- [ ] Ein im Wizard begonnenes Projekt ist ein Entwurf (`is_draft = true`) und
      erscheint **nicht** in der öffentlichen Liste/Karte.
- [ ] Entwürfe erscheinen unter `/admin/drafts` und in der Admin-Übersicht (Badge).
- [ ] „Weiter bearbeiten" öffnet den Wizard mit dem geladenen Entwurf.
- [ ] „Projekt fertigstellen" setzt `is_draft = false`; das Projekt erscheint
      danach in der öffentlichen Liste und nicht mehr unter Entwürfen.
- [ ] „Verwerfen" löscht den Entwurf.
- [ ] Bestehende Projekte bleiben nach der Migration sichtbar (`is_draft = false`).
- [ ] Backend-Tests grün, `tsc`/`eslint` sauber.

## Konzept-Verweis

Dieses Dokument. Bereich `area:projects`.
