#!/usr/bin/env bash
# backup_db.sh — erstellt einen pg_dump der konfigurierten PostgreSQL-Datenbank
#
# Verwendung:
#   ./scripts/backup_db.sh                              # DATABASE_URL aus .env
#   DB_URL="postgresql://..." ./scripts/backup_db.sh   # direkter Override
#   ENV_FILE=.env.prod ./scripts/backup_db.sh          # alternative .env-Datei
#
# Via Makefile:
#   make backup-db
#   make backup-db DB_URL="postgresql://..."
#   make backup-db ENV_FILE=.env.prod

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="$REPO_ROOT/backups"
RETENTION_DAYS=14

# ── Determine env file ────────────────────────────────────────────────────────

ENV_FILE="${ENV_FILE:-.env}"
ENV_PATH="$REPO_ROOT/$ENV_FILE"

# ── Resolve DATABASE_URL ──────────────────────────────────────────────────────

if [ -n "${DB_URL:-}" ]; then
    DATABASE_URL="$DB_URL"
elif [ -f "$ENV_PATH" ]; then
    # Strip surrounding quotes if present, ignore commented lines
    DATABASE_URL="$(grep -E '^DATABASE_URL=' "$ENV_PATH" | head -1 | cut -d'=' -f2- | tr -d '"'"'")"
else
    echo "Fehler: Keine .env-Datei unter $ENV_PATH gefunden und DB_URL ist nicht gesetzt." >&2
    exit 1
fi

if [ -z "$DATABASE_URL" ]; then
    echo "Fehler: DATABASE_URL ist leer. Bitte in $ENV_PATH setzen oder DB_URL übergeben." >&2
    exit 1
fi

# pg_dump versteht keinen SQLAlchemy-Treiber-Qualifier wie +psycopg2 oder +asyncpg.
# Entferne ihn, falls vorhanden: postgresql+psycopg2://... → postgresql://...
PG_URL=$(echo "$DATABASE_URL" | sed -E 's|^postgresql\+[a-z0-9]+://|postgresql://|')

# ── Mask password for display ─────────────────────────────────────────────────

MASKED_URL=$(echo "$PG_URL" | sed -E 's|:[^:@/]+@|:***@|')
echo "→ Zieldatenbank: $MASKED_URL"

# ── Ensure backup directory exists ───────────────────────────────────────────

mkdir -p "$BACKUP_DIR"

# ── Create dump ───────────────────────────────────────────────────────────────

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="$BACKUP_DIR/raildashboard_${TIMESTAMP}.dump"

echo "→ Schreibe Dump: $(basename "$DUMP_FILE")"
pg_dump -Fc "$PG_URL" > "$DUMP_FILE"

DUMP_SIZE=$(du -sh "$DUMP_FILE" | cut -f1)
echo "→ Fertig. Größe: $DUMP_SIZE"

# ── Rotate old backups ────────────────────────────────────────────────────────

DELETED=$(find "$BACKUP_DIR" -maxdepth 1 -name "raildashboard_*.dump" -mtime "+$RETENTION_DAYS" -print -delete | wc -l | tr -d ' ')
if [ "$DELETED" -gt 0 ]; then
    echo "→ $DELETED alte(r) Dump(s) (>${RETENTION_DAYS} Tage) gelöscht."
fi

REMAINING=$(find "$BACKUP_DIR" -maxdepth 1 -name "raildashboard_*.dump" | wc -l | tr -d ' ')
echo "→ Gespeicherte Backups: $REMAINING"
