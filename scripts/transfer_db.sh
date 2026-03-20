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
    ssh "$SSH_HOST" "grep -E '^DB_USER=' $REMOTE_DIR/.env | head -1 | cut -d'=' -f2- | tr -d '\"'"'"
}

confirm() {
    echo ""
    echo "WARNING: $1"
    read -r -p "Continue? [y/N] " CONFIRM
    [[ "$CONFIRM" == "y" || "$CONFIRM" == "Y" ]] || { echo "Aborted."; exit 0; }
}

mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ── dev-to-prod ───────────────────────────────────────────────────────────────

if [ "$DIRECTION" = "dev-to-prod" ]; then
    echo "=== dev → prod ==="

    LOCAL_URL="$(read_local_db_url)"
    MASKED=$(echo "$LOCAL_URL" | sed -E 's|:[^:@/]+@|:***@|')
    echo "→ Source (local):  $MASKED"
    echo "→ Target (server): raildashboard @ $SSH_HOST"

    # Plain SQL dump — version-agnostic, works across PG major versions.
    # --clean --if-exists adds DROP statements so restore is idempotent.
    DUMP_FILE="$BACKUP_DIR/dev_to_prod_${TIMESTAMP}.sql"
    echo "→ Dumping local DB (plain SQL)..."
    pg_dump --format=plain --clean --if-exists --no-owner --no-privileges \
        "$LOCAL_URL" > "$DUMP_FILE"
    echo "→ Dump: $(basename "$DUMP_FILE") ($(du -sh "$DUMP_FILE" | cut -f1))"

    echo "→ Uploading to server..."
    ssh "$SSH_HOST" "mkdir -p $REMOTE_DIR/backups"
    scp "$DUMP_FILE" "$SSH_HOST:$REMOTE_DIR/backups/"
    REMOTE_DUMP="$REMOTE_DIR/backups/$(basename "$DUMP_FILE")"

    DB_USER="$(read_prod_db_user)"
    confirm "This will OVERWRITE all data in the PRODUCTION database."

    echo "→ Restoring into production DB container..."
    # docker compose exec uses the container's local socket → no password needed.
    ssh "$SSH_HOST" "cd $REMOTE_DIR && \
        docker compose exec -T db psql -U $DB_USER raildashboard < $REMOTE_DUMP"

    echo "→ Done. Production DB updated from local dev."
    echo "→ Dump kept at: $REMOTE_DUMP"
fi

# ── prod-to-dev ───────────────────────────────────────────────────────────────

if [ "$DIRECTION" = "prod-to-dev" ]; then
    echo "=== prod → dev ==="

    LOCAL_URL="$(read_local_db_url)"
    MASKED=$(echo "$LOCAL_URL" | sed -E 's|:[^:@/]+@|:***@|')
    echo "→ Source (server): raildashboard @ $SSH_HOST"
    echo "→ Target (local):  $MASKED"

    DB_USER="$(read_prod_db_user)"

    DUMP_FILE="$BACKUP_DIR/prod_to_dev_${TIMESTAMP}.sql"
    echo "→ Dumping production DB (plain SQL)..."
    # Stream dump directly from container to local file via SSH pipe.
    ssh "$SSH_HOST" "cd $REMOTE_DIR && \
        docker compose exec -T db pg_dump \
            --format=plain --clean --if-exists --no-owner --no-privileges \
            -U $DB_USER raildashboard" > "$DUMP_FILE"
    echo "→ Dump: $(basename "$DUMP_FILE") ($(du -sh "$DUMP_FILE" | cut -f1))"

    confirm "This will OVERWRITE all data in your LOCAL dev database."

    echo "→ Restoring into local DB..."
    # Extract password from local DATABASE_URL for PGPASSWORD.
    PG_PASS=$(echo "$LOCAL_URL" | sed -E 's|.*://[^:]+:([^@]+)@.*|\1|')
    PGPASSWORD="$PG_PASS" psql "$LOCAL_URL" < "$DUMP_FILE"

    echo "→ Done. Local dev DB updated from production."
    echo "→ Dump kept at: $DUMP_FILE"
fi
