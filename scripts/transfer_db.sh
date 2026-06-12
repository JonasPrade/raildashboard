#!/usr/bin/env bash
# transfer_db.sh — Transfer the database between local dev and production.
#
# Uses plain SQL dumps (pg_dump -Fp) so there are no pg_dump/pg_restore version
# mismatches between local Postgres and the production Docker container.
#
# Usage:
#   ./scripts/transfer_db.sh dev-to-prod   # push local dev DB → production
#   ./scripts/transfer_db.sh prod-to-dev   # pull production DB → local dev
#
# Prerequisites:
#   - pg_dump / psql available locally
#   - SSH alias "contabo" configured in ~/.ssh/config
#   - Production stack running on the server (db container must be healthy)
#   - .env readable locally (for local DATABASE_URL)
#
# Safety rails (added 2026-05-21 after v0.0.4 silent-failure rollout):
#   - Non-empty dump verification (local + remote upload).
#   - Pre-restore safety dump of prod kept in backups/ (rollback artefact).
#   - Backend + worker stopped on server before restore; restarted afterwards
#     even if restore failed.
#   - pg_terminate_backend on any remaining DB connections.
#   - Filter `SET transaction_timeout` lines (PG17 → PG16 incompatibility).
#   - psql -v ON_ERROR_STOP=1 --single-transaction so a failure rolls back
#     atomically and never leaves a half-restored DB.
#   - COUNT(*) verification on key tables — exits non-zero if counts differ.

set -euo pipefail

SSH_HOST="contabo"
REMOTE_DIR="/srv/raildashboard"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="$REPO_ROOT/backups"

DIRECTION="${1:-}"
if [[ "$DIRECTION" != "dev-to-prod" && "$DIRECTION" != "prod-to-dev" ]]; then
    echo "Usage: $0 <dev-to-prod|prod-to-dev>" >&2
    echo "  dev-to-prod  Push local dev DB to production" >&2
    echo "  prod-to-dev  Pull production DB to local dev" >&2
    exit 1
fi

# ── Helpers ───────────────────────────────────────────────────────────────────

read_local_db_url() {
    local env="$REPO_ROOT/.env"
    if [ ! -f "$env" ]; then echo "ERROR: .env not found" >&2; exit 1; fi
    local url; url="$(grep -E '^DATABASE_URL=' "$env" | head -1 | cut -d'=' -f2- | tr -d '"'"'")"
    if [ -z "$url" ]; then echo "ERROR: DATABASE_URL not set in .env" >&2; exit 1; fi
    echo "$url" | sed -E 's|^postgresql\+[a-z0-9]+://|postgresql://|'
}

read_prod_db_user() {
    ssh "$SSH_HOST" "grep -E '^DB_USER=' $REMOTE_DIR/.env" | head -1 | cut -d= -f2- | tr -d "'\""
}

confirm() {
    echo ""
    echo "WARNING: $1"
    read -r -p "Continue? [y/N] " CONFIRM
    [[ "$CONFIRM" == "y" || "$CONFIRM" == "Y" ]] || { echo "Aborted."; exit 0; }
}

# Run psql against the prod DB container and return its single-column output.
# Strips CR from the SSH terminal and trims trailing whitespace.
prod_psql() {
    ssh "$SSH_HOST" "cd $REMOTE_DIR && docker compose exec -T db psql -At -U $DB_USER -d raildashboard -c \"$1\"" \
        | tr -d '\r'
}

local_psql() {
    psql -At "$LOCAL_URL" -c "$1"
}

# Three tables that are load-bearing for the app — used as a post-restore sanity check.
COUNT_QUERY="
SELECT 'project='||COUNT(*) FROM project
UNION ALL SELECT 'finve='||COUNT(*) FROM finve
UNION ALL SELECT 'change_log='||COUNT(*) FROM change_log;
"

mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ── dev-to-prod ───────────────────────────────────────────────────────────────

if [ "$DIRECTION" = "dev-to-prod" ]; then
    echo "=== dev → prod ==="

    LOCAL_URL="$(read_local_db_url)"
    MASKED=$(echo "$LOCAL_URL" | sed -E 's|:[^:@/]+@|:***@|')
    echo "→ Source (local):  $MASKED"
    echo "→ Target (server): raildashboard @ $SSH_HOST"

    DB_USER="$(read_prod_db_user)"
    if [ -z "$DB_USER" ]; then
        echo "ERROR: Could not read DB_USER from $SSH_HOST:$REMOTE_DIR/.env" >&2
        exit 1
    fi

    # Plain SQL dump — version-agnostic, works across PG major versions.
    # --clean --if-exists adds DROP statements so restore is idempotent.
    DUMP_FILE="$BACKUP_DIR/dev_to_prod_${TIMESTAMP}.sql"
    echo "→ Dumping local DB (plain SQL)..."
    pg_dump --format=plain --clean --if-exists --no-owner --no-privileges \
        "$LOCAL_URL" > "$DUMP_FILE"

    if [ ! -s "$DUMP_FILE" ] || ! grep -q -E '^(CREATE|INSERT|COPY)' "$DUMP_FILE"; then
        echo "ERROR: Dump file appears empty or invalid: $DUMP_FILE" >&2
        exit 1
    fi
    echo "→ Dump: $(basename "$DUMP_FILE") ($(du -sh "$DUMP_FILE" | cut -f1))"

    # Safety net: pull a binary backup of prod BEFORE touching it.
    PROD_BACKUP="$BACKUP_DIR/prod_BEFORE_dev_overwrite_${TIMESTAMP}.dump"
    echo "→ Pre-restore safety dump of prod → $(basename "$PROD_BACKUP") ..."
    ssh "$SSH_HOST" "cd $REMOTE_DIR && docker compose exec -T db pg_dump -U $DB_USER -Fc raildashboard" \
        > "$PROD_BACKUP"
    if [ ! -s "$PROD_BACKUP" ]; then
        echo "ERROR: Prod pre-backup is empty — aborting before any destructive step." >&2
        exit 1
    fi
    echo "→ Prod safety backup: $(du -sh "$PROD_BACKUP" | cut -f1)"

    echo "→ Uploading dump to server..."
    ssh "$SSH_HOST" "mkdir -p $REMOTE_DIR/backups"
    scp "$DUMP_FILE" "$SSH_HOST:$REMOTE_DIR/backups/"
    REMOTE_DUMP="$REMOTE_DIR/backups/$(basename "$DUMP_FILE")"

    REMOTE_SIZE=$(ssh "$SSH_HOST" "stat -c '%s' $REMOTE_DUMP 2>/dev/null || echo 0")
    if [ "$REMOTE_SIZE" -eq 0 ]; then
        echo "ERROR: Remote dump file is missing or empty after scp." >&2
        exit 1
    fi
    echo "→ Remote dump verified: $REMOTE_SIZE bytes."

    confirm "This will OVERWRITE all data in the PRODUCTION database."

    echo "→ Stopping backend + worker on server (free DB connections)..."
    ssh "$SSH_HOST" "cd $REMOTE_DIR && docker compose stop backend worker"

    echo "→ Terminating remaining DB connections..."
    ssh "$SSH_HOST" "cd $REMOTE_DIR && docker compose exec -T db psql -U $DB_USER -d postgres -c \"
        SELECT pg_terminate_backend(pid) FROM pg_stat_activity
        WHERE datname = 'raildashboard' AND pid <> pg_backend_pid();
    \"" >/dev/null

    echo "→ Restoring into prod (ON_ERROR_STOP, single-transaction, transaction_timeout filtered)..."
    # transaction_timeout is a PG17 SET that pg_dump 17 writes into the header.
    # The prod container runs an older Postgres that doesn't know it — filter out.
    # --single-transaction means any failure rolls back atomically; prod stays
    # in its pre-restore state if anything goes wrong.
    set +e
    ssh "$SSH_HOST" "cd $REMOTE_DIR && \
        grep -v '^SET transaction_timeout' $REMOTE_DUMP | \
        docker compose exec -T db psql -U $DB_USER -d raildashboard \
            -v ON_ERROR_STOP=1 --single-transaction"
    RESTORE_STATUS=$?
    set -e

    # ALWAYS restart backend+worker, regardless of restore outcome.
    echo "→ Restarting backend + worker..."
    ssh "$SSH_HOST" "cd $REMOTE_DIR && docker compose up -d backend worker"

    if [ "$RESTORE_STATUS" -ne 0 ]; then
        echo "" >&2
        echo "ERROR: Restore failed (exit $RESTORE_STATUS)." >&2
        echo "       Prod was rolled back automatically by --single-transaction." >&2
        echo "       Local dump kept at:               $DUMP_FILE" >&2
        echo "       Pre-restore prod backup kept at:  $PROD_BACKUP" >&2
        exit "$RESTORE_STATUS"
    fi

    echo "→ Verifying row counts on key tables..."
    LOCAL_COUNTS=$(local_psql "$COUNT_QUERY" | sort)
    PROD_COUNTS=$(prod_psql "$COUNT_QUERY" | sort)

    echo "  local:  $(echo "$LOCAL_COUNTS" | tr '\n' ' ')"
    echo "  prod:   $(echo "$PROD_COUNTS" | tr '\n' ' ')"

    if [ "$LOCAL_COUNTS" != "$PROD_COUNTS" ]; then
        echo "" >&2
        echo "ERROR: Row counts differ between local and prod after restore — investigate!" >&2
        echo "       Local dump kept at:               $DUMP_FILE" >&2
        echo "       Pre-restore prod backup kept at:  $PROD_BACKUP" >&2
        exit 1
    fi

    echo ""
    echo "✓ Done. Production DB updated from local dev — row counts match."
    echo "  Dump on server:                  $REMOTE_DUMP"
    echo "  Pre-restore prod backup (local): $PROD_BACKUP"
fi

# ── prod-to-dev ───────────────────────────────────────────────────────────────

if [ "$DIRECTION" = "prod-to-dev" ]; then
    echo "=== prod → dev ==="

    LOCAL_URL="$(read_local_db_url)"
    MASKED=$(echo "$LOCAL_URL" | sed -E 's|:[^:@/]+@|:***@|')
    echo "→ Source (server): raildashboard @ $SSH_HOST"
    echo "→ Target (local):  $MASKED"

    DB_USER="$(read_prod_db_user)"
    if [ -z "$DB_USER" ]; then
        echo "ERROR: Could not read DB_USER from $SSH_HOST:$REMOTE_DIR/.env" >&2
        exit 1
    fi

    DUMP_FILE="$BACKUP_DIR/prod_to_dev_${TIMESTAMP}.sql"
    echo "→ Dumping production DB (plain SQL)..."
    # Stream dump directly from container to local file via SSH pipe.
    # set -o pipefail (active from `set -euo pipefail`) makes this fail loudly
    # if either ssh or pg_dump exits non-zero.
    ssh "$SSH_HOST" "cd $REMOTE_DIR && \
        docker compose exec -T db pg_dump \
            --format=plain --clean --if-exists --no-owner --no-privileges \
            -U $DB_USER raildashboard" > "$DUMP_FILE"

    if [ ! -s "$DUMP_FILE" ] || ! grep -q -E '^(CREATE|INSERT|COPY)' "$DUMP_FILE"; then
        echo "ERROR: Dump file appears empty or invalid: $DUMP_FILE" >&2
        exit 1
    fi
    echo "→ Dump: $(basename "$DUMP_FILE") ($(du -sh "$DUMP_FILE" | cut -f1))"

    confirm "This will OVERWRITE all data in your LOCAL dev database."

    echo "→ Restoring into local DB (ON_ERROR_STOP, single-transaction, transaction_timeout filtered)..."
    PG_PASS=$(echo "$LOCAL_URL" | sed -E 's|.*://[^:]+:([^@]+)@.*|\1|')
    set +e
    grep -v '^SET transaction_timeout' "$DUMP_FILE" | \
        PGPASSWORD="$PG_PASS" psql "$LOCAL_URL" \
            -v ON_ERROR_STOP=1 --single-transaction
    RESTORE_STATUS=$?
    set -e

    if [ "$RESTORE_STATUS" -ne 0 ]; then
        echo "" >&2
        echo "ERROR: Restore failed (exit $RESTORE_STATUS)." >&2
        echo "       Local DB rolled back atomically by --single-transaction." >&2
        echo "       Dump kept at: $DUMP_FILE" >&2
        exit "$RESTORE_STATUS"
    fi

    echo "→ Verifying row counts on key tables..."
    PROD_COUNTS=$(prod_psql "$COUNT_QUERY" | sort)
    LOCAL_COUNTS=$(local_psql "$COUNT_QUERY" | sort)

    echo "  prod:   $(echo "$PROD_COUNTS" | tr '\n' ' ')"
    echo "  local:  $(echo "$LOCAL_COUNTS" | tr '\n' ' ')"

    if [ "$LOCAL_COUNTS" != "$PROD_COUNTS" ]; then
        echo "" >&2
        echo "ERROR: Row counts differ between prod and local after restore — investigate!" >&2
        echo "       Dump kept at: $DUMP_FILE" >&2
        exit 1
    fi

    echo ""
    echo "✓ Done. Local dev DB updated from production — row counts match."
    echo "  Dump kept at: $DUMP_FILE"
fi
