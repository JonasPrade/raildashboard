#!/usr/bin/env bash
# restore_db.sh — stellt einen pg_dump in die konfigurierte PostgreSQL-Datenbank wieder her
#
# Verwendung:
#   ./scripts/restore_db.sh backups/raildashboard_20260101_020000.dump
#   DB_URL="postgresql://..." ./scripts/restore_db.sh backups/file.dump
#   ENV_FILE=.env.prod ./scripts/restore_db.sh backups/file.dump
#
# Via Makefile:
#   make restore-db BACKUP=backups/raildashboard_20260101_020000.dump
#   make restore-db BACKUP=backups/file.dump DB_URL="postgresql://..."
#   make restore-db BACKUP=backups/file.dump ENV_FILE=.env.prod

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Require backup file argument ──────────────────────────────────────────────

BACKUP_FILE="${1:-}"
if [ -z "$BACKUP_FILE" ]; then
    echo "Verwendung: $0 <backup-datei>" >&2
    echo "Beispiel:   $0 backups/raildashboard_20260101_020000.dump" >&2
    exit 1
fi

# Resolve relative paths from repo root
if [[ "$BACKUP_FILE" != /* ]]; then
    BACKUP_FILE="$REPO_ROOT/$BACKUP_FILE"
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Fehler: Backup-Datei nicht gefunden: $BACKUP_FILE" >&2
    exit 1
fi

# ── Determine env file ────────────────────────────────────────────────────────

ENV_FILE="${ENV_FILE:-.env}"
ENV_PATH="$REPO_ROOT/$ENV_FILE"

# ── Resolve DATABASE_URL ──────────────────────────────────────────────────────

if [ -n "${DB_URL:-}" ]; then
    DATABASE_URL="$DB_URL"
elif [ -f "$ENV_PATH" ]; then
    DATABASE_URL="$(grep -E '^DATABASE_URL=' "$ENV_PATH" | head -1 | cut -d'=' -f2- | tr -d '"'"'")"
else
    echo "Fehler: Keine .env-Datei unter $ENV_PATH gefunden und DB_URL ist nicht gesetzt." >&2
    exit 1
fi

if [ -z "$DATABASE_URL" ]; then
    echo "Fehler: DATABASE_URL ist leer. Bitte in $ENV_PATH setzen oder DB_URL übergeben." >&2
    exit 1
fi

# Strip SQLAlchemy driver qualifier (e.g. +psycopg2) — not understood by pg_restore
PG_URL=$(echo "$DATABASE_URL" | sed -E 's|^postgresql\+[a-z0-9]+://|postgresql://|')

# ── Mask password for display ─────────────────────────────────────────────────

MASKED_URL=$(echo "$PG_URL" | sed -E 's|:[^:@/]+@|:***@|')
BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)

echo "→ Zieldatenbank: $MASKED_URL"
echo "→ Backup-Datei:  $(basename "$BACKUP_FILE") ($BACKUP_SIZE)"
echo ""
echo "ACHTUNG: Der Restore überschreibt alle vorhandenen Daten in der Zieldatenbank."
echo "         Bei Produktions-DBs immer sicherstellen, dass DB_URL korrekt gesetzt ist."
echo ""
read -r -p "Fortfahren? [j/N] " CONFIRM
if [[ "$CONFIRM" != "j" && "$CONFIRM" != "J" ]]; then
    echo "Abgebrochen."
    exit 0
fi

# ── Restore ───────────────────────────────────────────────────────────────────

echo "→ Stelle wieder her..."
pg_restore --clean --if-exists --no-owner --no-privileges -d "$PG_URL" "$BACKUP_FILE"
echo "→ Restore abgeschlossen."
