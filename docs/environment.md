### Environment variables

Copy `.env.example` to `.env` and fill in values. Required variables:

| Variable | Used by | Notes |
|---|---|---|
| `DATABASE_URL` | Backend | `postgresql+psycopg2://user:pw@host:port/db` |
| `SESSION_SECRET_KEY` | Backend | Required. 32-byte hex string for HMAC-signing session cookies. Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `REACT_APP_TILE_LAYER_URL` | Frontend | Raster tile URL for map background |
| `VITE_API_BASE_URL` | Frontend | Defaults to `http://localhost:8000` |
| `ROUTING_BASE_URL` | Backend | GraphHopper instance URL |
| `CELERY_BROKER_URL` | Backend | Dev: `redis://:devpassword@localhost:6379/0` (password set in `docker-compose.dev.yml`) |
| `CELERY_RESULT_BACKEND` | Backend | Same as `CELERY_BROKER_URL` |
| `RINF_API_URL` / `RINF_USERNAME` / `RINF_PASSWORD` | Backend | Optional — ERA RINF API credentials; omit if RINF imports are not used |
| `LLM_BASE_URL` | Backend | Optional — OpenAI-compatible endpoint for AI extraction; leave empty to disable |
| `LLM_API_KEY` | Backend | Optional — API key for the LLM endpoint |
| `LLM_MODEL` | Backend | Optional — model name (default: `gpt-4o-mini`) |
| `ROUTING_TIMEOUT_SECONDS` | Backend | Optional — timeout in seconds for routing requests (default: `20`) |
| `GRAPH_VERSION` | Backend | Routing graph build identifier; increment after deploying a new OSM extract |
| `BACKEND_CORS_ORIGINS` | Backend | JSON array of allowed CORS origins; defaults to `["http://localhost:5173"]` — **must be set in production** |

> ⚠️ **Never modify or overwrite `.env`.** It contains personal local settings. Only read from it.

### Test environment setup

`make test-backend` sets `ENVIRONMENT=test` automatically, which tells the backend to load `.env.test` instead of `.env`. There are two files to create (both are gitignored):

| File | Loaded by | Setup |
|---|---|---|
| `.env.test` (repo root) | pydantic settings via `config.py` | `cp .env.test.example .env.test` |
| `apps/backend/env.test` (no dot!) | `tests/db_related_tests/conftest.py` directly | `cp apps/backend/env.test.example apps/backend/env.test` |

In both files, set `DATABASE_URL` to the test database connection string. The URL **must contain the word `test`** — the test suite enforces this to prevent accidental writes to a production database.

**Test database tiers:**
- `tests/api/` — SQLite in-memory, no setup needed, runs without `.env.test`
- `tests/db_related_tests/` — real PostgreSQL + PostGIS, requires both files above

---
