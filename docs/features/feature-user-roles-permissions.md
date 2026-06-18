# Feature: Konfigurierbare Benutzerrollen & Berechtigungen

GitHub-Issue: [#36 „Benutzerverwaltung"](https://github.com/JonasPrade/raildashboard/issues/36)

**Status: implementiert (2026-06-17)** — alle 5 Phasen umgesetzt; Backend-/Frontend-Tests grün.

## Ziel

Admins können **eigene Rollen anlegen** und jeder Rolle **granulare
Bearbeitungsrechte** (Capabilities) zuweisen — statt des bisherigen festen
3-Rollen-Modells. Die Backend-Gates und die Frontend-Sichtbarkeiten richten sich
nach diesen Rechten, nicht mehr nach festen Rollennamen.

## Designentscheidungen (mit dem Nutzer abgestimmt, 2026-06-17)

- **Rechte nur pro Rolle** — keine Overrides pro Nutzer.
- **Genau eine Rolle pro Nutzer** (wie heute).
- **`admin` ist impliziter Super-Admin** — umgeht die Permission-Prüfung (Schutz
  vor Aussperren).
- **viewer/editor/admin werden vorgeseedet** (System-Rollen) und reproduzieren
  das heutige Verhalten 1:1; zusätzlich frei anlegbare Rollen.

## Ausgangslage (Stand 2026-06-17)

Festes RBAC:
- **Rollen-Enum** `UserRole = viewer | editor | admin`
  (`apps/backend/dashboard_backend/schemas/users.py`).
- **User-Modell** `users` mit einer String-Spalte `role`
  (`models/users.py`, `String(20)`, default `viewer`).
- **Backend-Gates** über `require_roles(*roles)` in
  `core/security.py` (prüft `user.role in allowed_roles`, sonst 403) an **~30
  Stellen**, grobgranular:
  - `editor|admin`: `projects.py`, `project_routes.py`, `haushalt_import.py`,
    `vib_import.py`, `project_texts.py`, `admin_assignments.py`
  - `admin`: `users.py`, `project_groups.py`, `settings.py`
  - `require_roles()` ohne Argument = nur eingeloggt (`tasks.py`,
    einzelne Routen in `projects.py`)
- **Frontend** spiegelt das mit hartcodierten Checks `user.role === "editor" |
  "admin"` in `components/Header.tsx`, `features/projects/ProjectDetail.tsx`,
  `features/projects/components/VibSection.tsx`,
  `features/admin/new-project/NewProjectPage.tsx`,
  `features/admin/AdminOverviewPage.tsx`, `features/admin/UsersPage.tsx`.
- **User-Bearbeitung** existiert bereits (`EditUserModal`, `PATCH /users/{id}`
  mit `username` + `role`), Rollen-Select ist aber eine feste Enum.

## Scope

**In scope:**
1. Datenmodell für Rollen + Rechte (DB) inkl. Migration & Seed.
2. Capability-basierte Backend-Gates (`require_permission`) statt `require_roles`.
3. API: Rollen-CRUD + Capability-Katalog + `permissions` in `/users/me`.
4. Admin-UI: Rollen-/Rechte-Verwaltung; dynamischer Rollen-Select bei Nutzern.
5. Frontend-`can()`-Helper ersetzt die hartcodierten Rollen-Checks.
6. Tests, `make gen-api`, Doku.

**Out of scope:**
- Pro-Nutzer-Rechte-Overrides.
- Mehrere Rollen pro Nutzer.
- Objekt-/zeilenbasierte ACLs (nur globale Capabilities).

## Datenmodell

Neue Tabellen:
- **`roles`**: `id`, `name` (unique), `description` (nullable),
  `is_system` (bool, default false — schützt viewer/editor/admin vor
  Löschen/Umbenennen), `created_at`.
- **`role_permissions`**: `role_id` (FK → roles, cascade delete),
  `permission_key` (String). Composite-PK `(role_id, permission_key)`.

Änderung an `users`:
- `role` (String) → **`role_id`** (FK → `roles`, NOT NULL). Relationship
  `User.role` → `Role`.

**Capability-Katalog im Code** (nicht in der DB): Konstante/Enum, z. B.
`core/permissions.py`. `role_permissions.permission_key` referenziert diese
Keys. Neue Capabilities kommen per Code dazu, ohne Daten-Migration. Unbekannte
Keys in der DB werden beim Laden ignoriert.

Initialer Katalog (aus den heutigen Gates abgeleitet):

| Key | Beschreibung | heute |
|---|---|---|
| `project.create` | Projekte anlegen | editor, admin |
| `project.edit` | Projekte bearbeiten | editor, admin |
| `project.delete` | Projekte löschen | editor, admin |
| `projectgroup.create` | Projektgruppen anlegen | admin |
| `projectgroup.edit` | Projektgruppen bearbeiten/löschen | admin |
| `haushalt.import` | Haushaltsberichte importieren | editor, admin |
| `vib.import` | VIB importieren | editor, admin |
| `finve.edit` | Finanzierungsvereinbarungen einarbeiten | editor, admin |
| `projecttext.edit` | Projekttexte bearbeiten | editor, admin |
| `assignment.manage` | Offene Zuordnungen verwalten | editor, admin |
| `user.manage` | Nutzer verwalten | admin |
| `role.manage` | Rollen & Rechte verwalten | admin |
| `settings.manage` | App-Einstellungen | admin |

UI-Gruppierung der Capabilities: **Projekte** (project.*), **Projektgruppen**
(projectgroup.*), **Finanzierung** (haushalt.import, vib.import, finve.edit),
**Administration** (user.manage, role.manage, settings.manage),
**Inhalte** (projecttext.edit, assignment.manage).

### Seed (abwärtskompatibel)

- **viewer** (`is_system`): keine Capabilities (nur lesen).
- **editor** (`is_system`): `project.create`, `project.edit`, `project.delete`,
  `haushalt.import`, `vib.import`, `finve.edit`, `projecttext.edit`,
  `assignment.manage`. **Kein** projectgroup/admin.
- **admin** (`is_system`): Super-Admin (implizit alle Capabilities).

`effective_permissions(user)` = wenn Rolle `admin` → alle Keys des Katalogs,
sonst die `role_permissions` der Rolle.

## Backend

1. **`core/permissions.py`** (neu): `Permission`-Katalog (Keys + Labels +
   Gruppe), Helper `all_permission_keys()`.
2. **Modelle** `models/roles.py` (neu): `Role`, `role_permissions`-Assoziation;
   `User.role_id` + Relationship; Property `User.effective_permissions` /
   `User.has_permission(key)` (admin-Bypass über `role.name == "admin"` **oder**
   ein `is_superadmin`-Flag auf der Rolle — Entscheidung: über System-Rolle
   `admin`).
3. **`core/security.py`**: neue Dependency **`require_permission(*keys)`** —
   lädt den User (Session **oder** Basic, wie `require_auth`), prüft
   `user.has_permission(key)` (admin-Bypass), sonst 403; nicht eingeloggt → 401.
   `require_roles` bleibt vorerst bestehen, wird aber an allen Gates ersetzt.
4. **Gates migrieren** (~30 Stellen): Mapping
   - `require_roles(editor, admin)` → passende `require_permission("…")`
     (projects → `project.edit`/`project.create`; haushalt → `haushalt.import`;
     vib → `vib.import`; project_texts → `projecttext.edit`; assignments →
     `assignment.manage`).
   - `require_roles(admin)` → `user.manage` / `projectgroup.*` / `settings.manage`.
   - `require_roles()` (nur Login) bleibt `require_auth()`.
5. **Schemas** `schemas/roles.py` (neu): `RoleRead` (id, name, description,
   is_system, permissions: list[str]), `RoleCreate`, `RoleUpdate`
   (name?, description?, permissions?). `UserRead` um `role: str` (Name) +
   `permissions: list[str]` (effektiv) erweitern; `UserCreate`/`UserUpdate`
   nutzen `role_id` (oder Rollenname) statt Enum.
6. **CRUD** `crud/roles.py` (neu): list/get/create/update/delete (System-Rollen:
   Umbenennen/Löschen verbieten → 400; Rechte editierbar). Beim Löschen einer
   Rolle, die Nutzern zugewiesen ist → 409.
7. **Endpoints** `api/v1/endpoints/roles.py` (neu, Prefix `/api/v1/roles`):
   - `GET /` (role.manage), `POST /` (role.manage), `PATCH /{id}`,
     `DELETE /{id}`.
   - `GET /api/v1/permissions` — Capability-Katalog (Keys + Labels + Gruppen)
     für die UI.
   - `users.py`: `/me` + Liste liefern `role` + `permissions`; Anlegen/Ändern
     mit `role_id`/Rollenname; „letzter Admin"-Schutz beim Rollenwechsel.
8. **Migration** (`make migrate-create MSG="add roles and permissions"`):
   Tabellen anlegen, 3 System-Rollen + deren `role_permissions` seeden,
   `users.role_id` ergänzen, aus `users.role` backfillen
   (viewer/editor/admin → role_id), Spalte `users.role` droppen. **Daten-sicher**:
   bestehende Nutzer behalten ihr Verhalten.
9. **`make gen-api`** — aber Achtung: das Skript zeigt fest auf
   `127.0.0.1:8000`; im aktuellen Dev-Setup läuft das Backend auf **8001**.
   Entweder vor `gen-api` die Ports angleichen oder direkt gegen `:8001`
   generieren.

## Frontend

1. **Auth-Context** (`lib/auth`): `me` enthält jetzt `permissions: string[]`;
   Helper **`can(key)`** bereitstellen (admin → immer true, da Backend bereits
   alle Keys liefert).
2. **Rollen-/Rechte-Checks ersetzen**: alle `user.role === "editor"/"admin"`
   (Header, ProjectDetail, VibSection, NewProjectPage, AdminOverviewPage,
   UsersPage) → `can("project.edit")` etc.
3. **queries.ts**: `useRoles`, `useCreateRole`, `useUpdateRole`, `useDeleteRole`,
   `usePermissions` (Katalog). `User`-Typ um `role`/`permissions` erweitern.
4. **CreateUserModal / EditUserModal**: Rollen-Select wird **dynamisch** aus
   `useRoles()` befüllt (kein festes `ROLE_OPTIONS` mehr).
5. **Neue Admin-Seite** `features/admin/RolesAdminPage.tsx` (Route
   `/admin/roles`, gated `role.manage`): Liste der Rollen; Anlegen/Bearbeiten in
   einem `RoleFormModal` mit **Rechte-Checkboxen**, gruppiert nach Capability-
   Gruppe; System-Rollen: Name/Description gesperrt, Rechte editierbar, kein
   Löschen. Direction-F-Komponenten (`ChronicleCard`/`ChronicleButton`),
   deutsche UI-Strings, Toasts via `@mantine/notifications`.
6. **AdminOverviewPage**: neue Karte „Rollen & Berechtigungen" → `/admin/roles`
   (sichtbar bei `can("role.manage")`).
7. **router.tsx**: Route `admin/roles`.

## Tests

- **Backend** `tests/api/test_roles.py`: Rollen-CRUD (Create/Update/Delete),
  System-Rolle nicht löschbar/umbenennbar (400), Löschen zugewiesener Rolle
  (409), Capability-Katalog-Endpoint.
- **Backend** `tests/api/test_permissions_gating.py`: pro Capability ein
  positiver/negativer Fall (Rolle mit/ohne Recht → 200/403); admin-Bypass;
  nicht eingeloggt → 401. Die bestehenden rollenbasierten Tests
  (`test_users.py`, `test_project_groups.py` etc.) auf das neue Modell
  anpassen.
- **Migration**: Backfill-Test (vorhandene viewer/editor/admin → korrekte
  role_id + Rechte).
- **Frontend**: `tsc` grün; ggf. Test für `can()`-Helper.

## Phasen (jede für sich mergebar)

1. **Datenmodell & Migration** — Tabellen, Seed, `users.role_id`, Backfill,
   `effective_permissions`. Kein sichtbarer Verhaltenswechsel.
2. **Backend-Gates & API** — `require_permission`, Gate-Migration, Rollen-CRUD,
   `permissions` in `/me`, `gen-api`.
3. **Frontend-Berechtigungslogik** — `can()`-Helper, Rollen-Checks ersetzen,
   dynamischer Rollen-Select.
4. **Admin-UI** — `RolesAdminPage` + Hub-Karte (nach API/Phase 3).
5. **Tests, Doku, Cleanup** — `UserRole`-Enum-Restnutzung entfernen.

## Risiken / Leitplanken

- **Kein Lockout**: admin-Bypass + „mindestens ein Admin"-Schutz beim
  Rollenwechsel/Löschen.
- **Abwärtskompatibel**: Seeds reproduzieren heutiges Verhalten; Phase 1–2
  ändern nichts Sichtbares.
- **Reihenfolge**: UI (Phase 4) erst nach API (Phase 2/3).
- **`gen-api`-Port** (8000 vs. 8001) beachten (s. o.).
