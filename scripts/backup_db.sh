#!/usr/bin/env bash
# backup_db.sh — erstellt einen pg_dump der DB *und* ein tar.gz des uploads-Volumes
#
# Pro Lauf entstehen zwei Dateien mit identischem Timestamp:
#   backups/raildashboard_<ts>.dump      (pg_dump -Fc)
#   backups/uploads_<ts>.tar.gz          (Inhalt des Docker-Volumes raildashboard_uploads)
#
# Beide unterliegen derselben Retention (14 Tage lokal).
#
# Verwendung:
#   ./scripts/backup_db.sh                              # DATABASE_URL aus .env
#   DB_URL="postgresql://..." ./scripts/backup_db.sh   # direkter Override
#   ENV_FILE=.env ./scripts/backup_db.sh          # alternative .env-Datei
#   SKIP_UPLOADS_BACKUP=1 ./scripts/backup_db.sh  # nur DB sichern (z. B. ohne Docker)
#   UPLOADS_VOLUME=other_name ./scripts/backup_db.sh
#
# Via Makefile:
#   make backup-db
#   make backup-db DB_URL="postgresql://..."
#   make backup-db ENV_FILE=.env

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="$REPO_ROOT/backups"
RETENTION_DAYS=14
UPLOADS_VOLUME="${UPLOADS_VOLUME:-raildashboard_uploads}"

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

# ── Back up uploads Docker volume ─────────────────────────────────────────────
# Same timestamp as the DB dump so the two files form a pair.
# Skipped silently with a notice if Docker isn't reachable or the volume is missing —
# `backup_db.sh` is also called on dev machines without Docker.

UPLOADS_FILE="$BACKUP_DIR/uploads_${TIMESTAMP}.tar.gz"

if [ "${SKIP_UPLOADS_BACKUP:-0}" = "1" ]; then
    echo "→ Uploads-Backup übersprungen (SKIP_UPLOADS_BACKUP=1)."
elif ! command -v docker >/dev/null 2>&1; then
    echo "→ Uploads-Backup übersprungen: docker nicht installiert."
elif ! docker volume inspect "$UPLOADS_VOLUME" >/dev/null 2>&1; then
    echo "→ Uploads-Backup übersprungen: Volume '$UPLOADS_VOLUME' existiert nicht."
else
    echo "→ Schreibe Uploads-Tar: $(basename "$UPLOADS_FILE")"
    docker run --rm \
        -v "$UPLOADS_VOLUME":/data:ro \
        -v "$BACKUP_DIR":/out \
        alpine tar czf "/out/$(basename "$UPLOADS_FILE")" -C /data .
    UPLOADS_SIZE=$(du -sh "$UPLOADS_FILE" | cut -f1)
    echo "→ Fertig. Größe: $UPLOADS_SIZE"
fi

# ── Rotate old backups ────────────────────────────────────────────────────────

DELETED=$(find "$BACKUP_DIR" -maxdepth 1 -name "raildashboard_*.dump" -mtime "+$RETENTION_DAYS" -print -delete | wc -l | tr -d ' ')
if [ "$DELETED" -gt 0 ]; then
    echo "→ $DELETED alte(r) Dump(s) (>${RETENTION_DAYS} Tage) gelöscht."
fi

DELETED_UPLOADS=$(find "$BACKUP_DIR" -maxdepth 1 -name "uploads_*.tar.gz" -mtime "+$RETENTION_DAYS" -print -delete | wc -l | tr -d ' ')
if [ "$DELETED_UPLOADS" -gt 0 ]; then
    echo "→ $DELETED_UPLOADS alte(s) Uploads-Tar(s) (>${RETENTION_DAYS} Tage) gelöscht."
fi

REMAINING=$(find "$BACKUP_DIR" -maxdepth 1 -name "raildashboard_*.dump" | wc -l | tr -d ' ')
REMAINING_UPLOADS=$(find "$BACKUP_DIR" -maxdepth 1 -name "uploads_*.tar.gz" | wc -l | tr -d ' ')
echo "→ Gespeicherte Backups: $REMAINING Dumps, $REMAINING_UPLOADS Uploads-Tars."
