#!/usr/bin/env bash
# transfer_db.sh — Transfer the database between local dev and production.
#
# Usage:
#   ./scripts/transfer_db.sh dev-to-prod   # push local dev DB → production
#   ./scripts/transfer_db.sh prod-to-dev   # pull production DB → local dev
#
# Prerequisites:
#   - pg_dump / pg_restore available locally
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

read_prod_credentials() {
    DB_USER=$(ssh "$SSH_HOST" "grep -E '^DB_USER=' $REMOTE_DIR/.env | head -1 | cut -d'=' -f2- | tr -d '\"'")
    DB_PASS=$(ssh "$SSH_HOST" "grep -E '^DB_PASSWORD=' $REMOTE_DIR/.env | head -1 | cut -d'=' -f2- | tr -d '\"'")
    if [ -z "$DB_USER" ] || [ -z "$DB_PASS" ]; then
        echo "ERROR: Could not read DB_USER / DB_PASSWORD from server's .env" >&2; exit 1
    fi
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

    DUMP_FILE="$BACKUP_DIR/dev_to_prod_${TIMESTAMP}.dump"
    echo "→ Dumping local DB..."
    pg_dump -Fc "$LOCAL_URL" > "$DUMP_FILE"
    echo "→ Dump: $(basename "$DUMP_FILE") ($(du -sh "$DUMP_FILE" | cut -f1))"

    echo "→ Uploading to server..."
    ssh "$SSH_HOST" "mkdir -p $REMOTE_DIR/backups"
    scp "$DUMP_FILE" "$SSH_HOST:$REMOTE_DIR/backups/"
    REMOTE_DUMP="$REMOTE_DIR/backups/$(basename "$DUMP_FILE")"

    read_prod_credentials
    confirm "This will OVERWRITE all data in the PRODUCTION database."

    echo "→ Restoring into production DB container..."
    ssh "$SSH_HOST" "cd $REMOTE_DIR && \
        docker compose exec -T db bash -c \
        'PGPASSWORD=$DB_PASS pg_restore \
            -U $DB_USER -d raildashboard \
            --clean --if-exists --no-owner --no-privileges' \
        < $REMOTE_DUMP"

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

    read_prod_credentials

    REMOTE_DUMP="$REMOTE_DIR/backups/prod_to_dev_${TIMESTAMP}.dump"
    echo "→ Dumping production DB..."
    ssh "$SSH_HOST" "cd $REMOTE_DIR && \
        docker compose exec -T db bash -c \
        'PGPASSWORD=$DB_PASS pg_dump -Fc -U $DB_USER raildashboard' \
        > $REMOTE_DUMP"

    DUMP_FILE="$BACKUP_DIR/prod_to_dev_${TIMESTAMP}.dump"
    echo "→ Downloading dump..."
    scp "$SSH_HOST:$REMOTE_DUMP" "$DUMP_FILE"
    echo "→ Dump: $(basename "$DUMP_FILE") ($(du -sh "$DUMP_FILE" | cut -f1))"

    confirm "This will OVERWRITE all data in your LOCAL dev database."

    echo "→ Restoring into local DB..."
    pg_restore --no-owner --no-privileges --clean --if-exists -d "$LOCAL_URL" "$DUMP_FILE" || {
        STATUS=$?
        [ "$STATUS" -gt 1 ] && { echo "→ Restore failed (exit $STATUS)." >&2; exit "$STATUS"; }
        echo "→ Restore completed with non-fatal warnings."
    }

    echo "→ Done. Local dev DB updated from production."
    echo "→ Dump kept at: $DUMP_FILE"
fi
