#!/bin/bash
# docker-entrypoint.sh
# Waits for the database, optionally runs Alembic migrations, then exec()s the
# command passed by docker (Dockerfile CMD or compose `command:`).
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
else
    echo "[entrypoint] Running Alembic migrations..."
    alembic upgrade head
fi

echo "[entrypoint] exec: $*"
exec "$@"
