#!/usr/bin/env bash
# restore_db.sh — stellt einen pg_dump in die konfigurierte PostgreSQL-Datenbank wieder her
#                und restored optional das paarige uploads_<ts>.tar.gz ins Docker-Volume.
#
# Paarung: zu raildashboard_20260101_020000.dump wird automatisch
#          uploads_20260101_020000.tar.gz im selben Verzeichnis gesucht und mit-restored.
#          Mit UPLOADS=<pfad> kann ein anderes Tar gewählt werden, UPLOADS=none unterdrückt.
#
# Verwendung:
#   ./scripts/restore_db.sh backups/raildashboard_20260101_020000.dump
#   DB_URL="postgresql://..." ./scripts/restore_db.sh backups/file.dump
#   ENV_FILE=.env ./scripts/restore_db.sh backups/file.dump
#   UPLOADS=none ./scripts/restore_db.sh backups/file.dump      # nur DB, ohne Uploads
#   UPLOADS=backups/uploads_other.tar.gz ./scripts/restore_db.sh backups/file.dump
#
# Via Makefile:
#   make restore-db BACKUP=backups/raildashboard_20260101_020000.dump
#   make restore-db BACKUP=backups/file.dump DB_URL="postgresql://..."
#   make restore-db BACKUP=backups/file.dump ENV_FILE=.env

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
UPLOADS_VOLUME="${UPLOADS_VOLUME:-raildashboard_uploads}"

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

# ── Locate paired uploads tar ─────────────────────────────────────────────────
# Derive uploads_<ts>.tar.gz from raildashboard_<ts>.dump in the same directory.
# UPLOADS=<path> overrides; UPLOADS=none disables.

UPLOADS_FILE=""
if [ "${UPLOADS:-}" = "none" ]; then
    :
elif [ -n "${UPLOADS:-}" ]; then
    UPLOADS_FILE="$UPLOADS"
    if [[ "$UPLOADS_FILE" != /* ]]; then
        UPLOADS_FILE="$REPO_ROOT/$UPLOADS_FILE"
    fi
    if [ ! -f "$UPLOADS_FILE" ]; then
        echo "Fehler: Uploads-Tar nicht gefunden: $UPLOADS_FILE" >&2
        exit 1
    fi
else
    BACKUP_BASENAME=$(basename "$BACKUP_FILE")
    if [[ "$BACKUP_BASENAME" =~ ^raildashboard_([0-9]{8}_[0-9]{6})\.dump$ ]]; then
        CANDIDATE="$(dirname "$BACKUP_FILE")/uploads_${BASH_REMATCH[1]}.tar.gz"
        [ -f "$CANDIDATE" ] && UPLOADS_FILE="$CANDIDATE"
    fi
fi

echo "→ Zieldatenbank: $MASKED_URL"
echo "→ Backup-Datei:  $(basename "$BACKUP_FILE") ($BACKUP_SIZE)"
if [ -n "$UPLOADS_FILE" ]; then
    UPLOADS_SIZE=$(du -sh "$UPLOADS_FILE" | cut -f1)
    echo "→ Uploads-Tar:   $(basename "$UPLOADS_FILE") ($UPLOADS_SIZE) → Volume '$UPLOADS_VOLUME'"
else
    echo "→ Uploads-Tar:   keines (DB-only Restore)"
fi
echo ""
echo "ACHTUNG: Der Restore überschreibt alle vorhandenen Daten in der Zieldatenbank."
if [ -n "$UPLOADS_FILE" ]; then
    echo "         Außerdem wird der Inhalt des Volumes '$UPLOADS_VOLUME' überschrieben."
fi
echo "         Bei Produktions-DBs immer sicherstellen, dass DB_URL korrekt gesetzt ist."
echo ""
read -r -p "Fortfahren? [j/N] " CONFIRM
if [[ "$CONFIRM" != "j" && "$CONFIRM" != "J" ]]; then
    echo "Abgebrochen."
    exit 0
fi

# ── Restore ───────────────────────────────────────────────────────────────────
# Strategy: drop and recreate the database for a completely clean slate.
# This avoids --clean conflicts with Docker-pre-created extensions (postgis_topology etc.)
# and is the standard way to do a reliable restore.

# Extract database name and build connection URL to the template1 maintenance database.
DBNAME=$(echo "$PG_URL" | sed -E 's|.*/([^/?]+).*|\1|')
TEMPLATE_URL=$(echo "$PG_URL" | sed -E "s|/[^/]+$|/template1|")

echo "→ Beende aktive Verbindungen und lösche Datenbank '$DBNAME'..."
psql "$TEMPLATE_URL" <<SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '$DBNAME' AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS "$DBNAME";
CREATE DATABASE "$DBNAME";
SQL

echo "→ Stelle wieder her..."
pg_restore --no-owner --no-privileges -d "$PG_URL" "$BACKUP_FILE" || {
    STATUS=$?
    # pg_restore exits with 1 for non-fatal warnings (e.g. unknown SET parameters from a
    # newer PostgreSQL version such as "transaction_timeout" in PG17 vs. PG16 target).
    # Only abort on codes > 1 which indicate a fatal error.
    if [ "$STATUS" -gt 1 ]; then
        echo "→ Restore fehlgeschlagen (Exit-Code $STATUS)." >&2
        exit "$STATUS"
    fi
    echo "→ DB-Restore mit Warnungen abgeschlossen (nicht-fatale Fehler wurden ignoriert)."
}
echo "→ DB-Restore abgeschlossen."

# ── Restore uploads volume ────────────────────────────────────────────────────

if [ -n "$UPLOADS_FILE" ]; then
    if ! command -v docker >/dev/null 2>&1; then
        echo "→ Uploads-Restore übersprungen: docker nicht installiert." >&2
        exit 1
    fi
    if ! docker volume inspect "$UPLOADS_VOLUME" >/dev/null 2>&1; then
        echo "→ Volume '$UPLOADS_VOLUME' existiert nicht — wird angelegt."
        docker volume create "$UPLOADS_VOLUME" >/dev/null
    fi
    echo "→ Stelle Uploads-Volume wieder her..."
    # Wipe before extract so deleted files don't survive the restore.
    docker run --rm \
        -v "$UPLOADS_VOLUME":/data \
        -v "$(dirname "$UPLOADS_FILE")":/in:ro \
        alpine sh -c "rm -rf /data/* /data/.[!.]* /data/..?* 2>/dev/null; tar xzf /in/$(basename "$UPLOADS_FILE") -C /data"
    echo "→ Uploads-Restore abgeschlossen."
fi
