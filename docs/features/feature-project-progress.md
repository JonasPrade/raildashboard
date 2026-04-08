# Feature: ProjectProgress

## Ziel

Fortschrittsstand eines Projekts (Planungs-, Genehmigungs-, Bauphase) strukturiert speichern und in der Projektdetailseite als Zeitleiste anzeigen. Mehrere Quellen (VIB, Pressemitteilungen, manuelle Eingabe) schreiben in dasselbe Modell.

## Scope

- Backend: `ProjectProgress`-Datenmodell mit Status, Datum, Quelle, Kommentar
- Frontend: Zeitleiste / Meilenstein-Ansicht in `ProjectDetail`
- Schreibzugriff für editor / admin (manueller Eintrag)
- VIB-LLM-Extraktion schreibt in dieses Modell (sobald beide implementiert sind)

## Nicht im Scope

- Automatische Extraktion aus Pressemitteilungen (eigenes Feature)
- Konfliktauflösung zwischen Quellen (zunächst: alle Einträge sichtbar, keine Deduplizierung)

## Verhalten

- Zeitleiste zeigt alle Progress-Einträge eines Projekts chronologisch
- Quelle ist immer sichtbar (z.B. "VIB 2024", "Manuell")
- Nur editor / admin kann Einträge anlegen oder löschen

## Akzeptanzkriterien

- Eintrag kann mit Status, Datum, Quelle und Kommentar angelegt werden
- Zeitleiste wird in ProjectDetail angezeigt
- Mehrere Einträge aus unterschiedlichen Quellen sind korrekt sortiert
- VIB-Extraktion kann `source="vib_{year}"` schreiben

## Technische Hinweise

### Datenmodell

```python
class ProjectProgress(Base):
    __tablename__ = "project_progress"
    id: int
    project_id: int             # FK → projects.id
    status: str                 # z.B. "Planung", "Genehmigung", "Bau", "Inbetrieb"
    date: date | None           # Datum des Meilensteins
    source: str                 # z.B. "vib_2024", "manual", "press"
    comment: str | None
    created_at: datetime
    created_by_user_id: int | None  # FK → users.id
```

Alembic-Migration erforderlich.

### Backend

- Schema: `schemas/project_progress.py` — `ProjectProgressCreate`, `ProjectProgressRead`
- CRUD: `crud/project_progress.py` — `get_for_project`, `create`, `delete`
- Endpoint: `api/v1/endpoints/project_progress.py`
  - `GET /api/v1/projects/{id}/progress` — public
  - `POST /api/v1/projects/{id}/progress` — editor/admin
  - `DELETE /api/v1/projects/{id}/progress/{entry_id}` — editor/admin
- `make gen-api` nach Endpoint-Erstellung

### Frontend

- Query: `useProjectProgress(projectId)` in `queries.ts`
- Mutation: `useCreateProjectProgress()`, `useDeleteProjectProgress()`
- Komponente: `features/projects/components/ProjectProgressSection.tsx`
  - Zeitleiste mit Mantine `Timeline` oder ähnlich
  - Formular zum Anlegen (editor/admin only)

## Implementierungsreihenfolge

1. [ ] DB-Modell + Alembic-Migration
2. [ ] Pydantic-Schema + CRUD
3. [ ] API-Endpoints + `make gen-api`
4. [ ] Frontend: `ProjectProgressSection.tsx` + Queries
