#!/bin/bash
# docker-entrypoint.sh
# Waits for the database to be ready, runs Alembic migrations, then starts uvicorn.
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

echo "[entrypoint] Running Alembic migrations..."
alembic upgrade head

echo "[entrypoint] Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
