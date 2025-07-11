# Architecture

## Backend Structure

The backend of the rail dashboard is modular and follows a classical layered architecture to separate responsibilities. Its core function is to provide structured information about rail projects through a REST API.

### 1. API Layer (`api/`)
- Provides endpoints using FastAPI
- Versioned under `/api/v1`
- Endpoints grouped by topics (e.g., projects, documents, filters)

### 2. Schema Layer (`schemas/`)
- Defines input and output models for the API using Pydantic
- Decouples API data representation from the database structure
- Uses typing, validation, and auto-documentation

### 3. CRUD Layer (`crud/`)
- Contains read and write database operations (e.g., `get_project`, `create_project`)
- Provides a clean abstraction layer between API and database

### 4. Database Layer (`models/`)
- SQLAlchemy models for all core entities (projects, geometries, etc.)
- Uses `geoalchemy2` for geodata (PostGIS)

### 5. Configuration & Infrastructure (`core/`)
- Database connection (SQLAlchemy engine, session)
- Environment variables (via `.env`)
- Initialization routines (e.g., `init_db`)

### 6. Service Layer (`services/`)
- Contains parser-related tasks
- E.g., processing PDF documents, RailML import, raw data transformation

### 7. Entry Point (`main.py`)
- Initializes the FastAPI app
- Registers the API routers
- Configures global middleware (e.g., CORS, logging)

This layered model allows each component to be tested, adapted, and extended independently. It promotes maintainability, reusability, and clear responsibilities in the project.

## Data
Alle changable data is in a separate folder ("data")