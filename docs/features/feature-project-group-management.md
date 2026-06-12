# Feature: Projektgruppen-Verwaltung in der UI

## Ziel

Admins können Projektgruppen (`ProjectGroup`) direkt in der UI **anlegen**,
**bearbeiten** (alle Felder) und **löschen** — nicht nur, wie bisher, die zwei
Toggles `is_visible` / `is_default_selected` umschalten.

## Ausgangslage (Stand 2026-06-12)

Vorhanden:
- **Model** `project_group` (`apps/backend/dashboard_backend/models/projects/project_group.py`) mit allen Feldern: `name`, `short_name` (unique), `description`, `public`, `color`, `plot_only_superior_projects`, `is_visible`, `is_default_selected`, `id_old`.
- **M:N zu Projekten** über `project_to_project_group`; Zuweisung läuft über die Projekt-Endpoints (`project_group_ids`), **nicht** Teil dieses Features.
- **Schema** `ProjectGroupSchema` (read) in `schemas/projects/project_group_schema.py`.
- **CRUD** `crud/projects/project_groups.py`: `get_project_group_by_id`, `get_project_groups`, `update_project_group(dict)`; `create_project_group` / `delete_project_group` existieren **auskommentiert**.
- **Endpoints** `api/v1/endpoints/project_groups.py` (Prefix `/api/v1/project_groups`): `GET /`, `GET /{id}` (public), `PATCH /{id}` (admin) — Update-Schema `ProjectGroupUpdate` deckt nur `is_visible` + `is_default_selected` ab.
- **Admin-Seite** `features/admin/ProjectGroupsAdminPage.tsx` (Route `/admin/project-groups`): Liste + zwei Switches + globaler `map_group_mode`.
- **Hooks** `useProjectGroups`, `useUpdateProjectGroup` in `shared/api/queries.ts`.

Fehlt: POST (create), DELETE, PATCH für die übrigen Felder, sowie das UI.

## Scope

**In scope:**
1. **Create** — `POST /api/v1/project_groups/` (admin), neues Gruppen-Formular im Admin.
2. **Edit (alle Felder)** — `PATCH /{id}` um `name`, `short_name`, `description`, `public`, `color`, `plot_only_superior_projects` erweitern (zusätzlich zu den bestehenden zwei Toggles).
3. **Delete** — `DELETE /{id}` (admin) mit Confirm im UI.

**Out of scope:**
- Projekt-zu-Gruppe-Zuordnung (läuft bereits über die Projekt-Endpoints).
- Keine neue DB-Spalte → **keine Alembic-Migration nötig** (alle Felder existieren).
- `map_group_mode` bleibt unverändert.

## Datenmodell

Keine Änderung. `short_name` ist `unique` — Duplikate müssen abgefangen werden
(HTTP 409, klare Fehlermeldung im UI). `color` ist ein Hex-String (`#RRGGBB`).

## Backend

1. **Schema** `schemas/projects/project_group_schema.py`:
   - `ProjectGroupCreate` — `name` (required), `short_name` (required), optional `description`, `public`, `color` (default `#FF0000`), `plot_only_superior_projects`, `is_visible`, `is_default_selected`.
   - `ProjectGroupUpdate` (im Endpoint) um alle editierbaren Felder erweitern, alle `Optional`.
2. **CRUD** `crud/projects/project_groups.py`: `create_project_group(db, data)` und `delete_project_group(db, group_id)` aktivieren/ausimplementieren.
3. **Endpoints** `api/v1/endpoints/project_groups.py`:
   - `POST /` → `require_roles(UserRole.admin)`, Body `ProjectGroupCreate`, Response `ProjectGroupSchema`. Bei `short_name`-Kollision **409**.
   - `PATCH /{id}` → erweitertes `ProjectGroupUpdate`; `short_name`-Kollision **409**.
   - `DELETE /{id}` → `require_roles(UserRole.admin)`, 204; 404 wenn nicht vorhanden.
4. **`make gen-api`** nach den Endpoint-Änderungen.
5. **Tests** `apps/backend/tests/api/test_project_groups.py`: Create (201 + Felder), Create mit dupliziertem `short_name` (409), Edit aller Felder, Delete (204 + danach 404), Rollen-Check (viewer/editor → 403 bei POST/PATCH/DELETE).

## Frontend

1. **queries.ts**: `useCreateProjectGroup`, `useDeleteProjectGroup`, `useUpdateProjectGroup` um alle Felder erweitern; Typen `ProjectGroupCreatePayload` / `ProjectGroupUpdatePayload`. Nach Mutation `invalidateQueries(["projectGroups"])`.
2. **ProjectGroupsAdminPage.tsx**:
   - „Neue Gruppe anlegen"-Button → Formular (Mantine `useForm`): `name`, `short_name`, `description`, `color` (ColorInput), `public`, `plot_only_superior_projects`, `is_visible`, `is_default_selected`.
   - Pro Gruppe: „Bearbeiten" (gleiches Formular, vorbefüllt) und „Löschen" (Confirm-Modal).
   - Direction-F-Komponenten (`ChronicleCard`/`ChronicleButton`), Erfolgs-/Fehler-Toast via `@mantine/notifications`; 409 als verständliche Meldung („Kürzel bereits vergeben").
   - UI-Strings auf Deutsch.

## Akzeptanzkriterien

- [ ] Admin legt auf `/admin/project-groups` eine neue Gruppe an; sie erscheint sofort in der Liste und im `?group=`-Selektor der Startseite.
- [ ] `short_name`-Duplikat wird mit verständlicher Meldung abgelehnt (kein 500).
- [ ] Admin bearbeitet alle Felder (inkl. Farbe/Name) und sieht die Änderung in Karte/Liste.
- [ ] Admin löscht eine Gruppe (mit Confirm); Projekte bleiben erhalten, nur die Zuordnung verschwindet.
- [ ] viewer/editor sehen die Admin-Aktionen nicht und werden vom Backend mit 403 abgewiesen.
- [ ] Backend-Tests (`test_project_groups.py`) grün; `make gen-api` lief.

## Konzept-Verweis

Verwandt: Admin-konfigurierbare Sichtbarkeit/`map_group_mode` (bereits umgesetzt,
siehe `roadmap.md` → Finished/UI). Dieses Feature ergänzt CRUD auf Gruppen-Ebene.
