# Architecture

## Overview

Schienendashboard is a full-stack web application with a FastAPI backend and a React frontend, both living in the `apps/` directory of the monorepo.

```
apps/
├── backend/   # FastAPI + SQLAlchemy + PostGIS (Python)
└── frontend/  # React + Vite + Mantine + MapLibre (TypeScript)
```

The frontend communicates with the backend exclusively via the REST API. Types are generated automatically from the OpenAPI schema (`make gen-api`).

---

## Backend Structure

The backend follows a classical layered architecture to separate responsibilities.

### 1. API Layer (`api/`)
- Provides endpoints using FastAPI
- Versioned under `/api/v1`
- Endpoints grouped by topic (projects, documents, routing, etc.)

### 2. Schema Layer (`schemas/`)
- Defines input and output models using Pydantic
- Decouples API data representation from database structure
- Provides typing, validation, and auto-documentation

### 3. CRUD Layer (`crud/`)
- Contains read and write database operations (e.g. `get_project`, `create_project`)
- Clean abstraction layer between API and database

### 4. Database Layer (`models/`)
- SQLAlchemy ORM models for all core entities
- Uses `geoalchemy2` for geodata (PostGIS)

### 5. Configuration & Infrastructure (`core/`)
- Database connection (SQLAlchemy engine, session)
- Environment variables loaded via Pydantic Settings from the repo-root `.env`

### 6. Service Layer (`services/`)
- Parser-related tasks and raw data transformation
- e.g. PDF processing, RailML import

### 7. Entry Point (`main.py`)
- Initialises the FastAPI app
- Registers API routers
- Configures global middleware (CORS, logging)

### Data folder
All changeable runtime data lives in `apps/backend/data/`.

---

## Frontend Structure

The frontend is a feature-oriented React application.

```
src/
├── features/     # Domain-specific modules (map, projects, documentation …)
├── components/   # Shared UI building blocks (header, error boundary)
├── shared/       # Cross-feature utilities and generated API client
├── lib/          # Infrastructure (API client config, React Query setup, auth)
├── theme.ts      # Mantine theme configuration
└── router.tsx    # Central route definitions
```

### Key technology choices
| Concern | Library |
|---|---|
| UI framework | Mantine |
| Map rendering | MapLibre GL |
| Server state | TanStack React Query |
| Routing | React Router |
| Build tool | Vite |
| Type safety | TypeScript strict mode |

New functional areas go into `src/features/<name>/`. Shared UI components used by two or more features go into `src/components/`.
