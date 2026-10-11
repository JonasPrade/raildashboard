#!/bin/bash
# docker-entrypoint.sh
# Waits for the database, optionally runs Alembic migrations, then exec()s the
# command passed by docker (Dockerfile CMD or compose `command:`).
#
# The database backup before the migration is NOT taken here: the backend image
# has no pg_dump matching the server. The one-shot `backup` service in
# compose.yaml dumps the database with the db image's own pg_dump, and the
# backend only starts once that backup completed successfully (DEPLOY.md).
#
# SKIP_MIGRATIONS=1 disables the Alembic step — used by the worker container so
# only the backend service runs `alembic upgrade head`. Without this, both
# containers race on the same migration and one crashes with
# `psycopg2.errors.UniqueViolation: pg_class_relname_nsp_index`.
set -e

echo "[entrypoint] Waiting for database..."

python - <<'EOF'
import time, sys, os
from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
for attempt in range(30):
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[entrypoint] Database is ready.")
        break
    except Exception as exc:
        print(f"[entrypoint] Attempt {attempt + 1}/30 – not ready: {exc}")
        time.sleep(2)
else:
    print("[entrypoint] Database did not become ready in time. Aborting.")
    sys.exit(1)
EOF

if [ "${SKIP_MIGRATIONS:-0}" = "1" ]; then
    echo "[entrypoint] SKIP_MIGRATIONS=1 — Alembic step übersprungen."
elif python scripts/db_ahead.py; then
    # The database is on a revision this code does not know: a rollback after a
    # migration. Start without touching the schema, otherwise `upgrade head`
    # aborts and the rollback never comes up (scripts/db_ahead.py, DEPLOY.md).
    :
else
    echo "[entrypoint] Running Alembic migrations..."
    alembic upgrade head
fi

echo "[entrypoint] exec: $*"
exec "$@"
