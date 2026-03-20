#!/usr/bin/env bash
# transfer_db.sh — Dump local dev DB and restore it into the production Docker stack.
#
# Usage:
#   ./scripts/transfer_db.sh
#
# Prerequisites:
#   - pg_dump available locally
#   - SSH alias "contabo" configured in ~/.ssh/config
#   - Production stack running on the server (db container must be healthy)
#   - .env readable locally (for DATABASE_URL)

set -euo pipefail

SSH_HOST="contabo"
REMOTE_DIR="/srv/raildashboard"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="$REPO_ROOT/backups"

# ── Read local DATABASE_URL ───────────────────────────────────────────────────

ENV_PATH="$REPO_ROOT/.env"
if [ ! -f "$ENV_PATH" ]; then
    echo "ERROR: .env not found at $REPO_ROOT/.env" >&2
    exit 1
fi

DATABASE_URL="$(grep -E '^DATABASE_URL=' "$ENV_PATH" | head -1 | cut -d'=' -f2- | tr -d '"'"'")"
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL not set in .env" >&2
    exit 1
fi
PG_URL=$(echo "$DATABASE_URL" | sed -E 's|^postgresql\+[a-z0-9]+://|postgresql://|')

# ── Read production DB credentials from server's .env ─────────────────────────

echo "→ Reading production credentials from server..."
PROD_DB_USER=$(ssh "$SSH_HOST" "grep -E '^DB_USER=' $REMOTE_DIR/.env | head -1 | cut -d'=' -f2- | tr -d '\"'"'" 2>/dev/null || echo '')
PROD_DB_PASS=$(ssh "$SSH_HOST" "grep -E '^DB_PASSWORD=' $REMOTE_DIR/.env | head -1 | cut -d'=' -f2- | tr -d '\"'"'" 2>/dev/null || echo '')

if [ -z "$PROD_DB_USER" ] || [ -z "$PROD_DB_PASS" ]; then
    echo "ERROR: Could not read DB_USER / DB_PASSWORD from server's .env" >&2
    exit 1
fi

# ── Dump local DB ────────────────────────────────────────────────────────────

mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="$BACKUP_DIR/transfer_${TIMESTAMP}.dump"

MASKED=$(echo "$PG_URL" | sed -E 's|:[^:@/]+@|:***@|')
echo "→ Dumping local DB: $MASKED"
pg_dump -Fc "$PG_URL" > "$DUMP_FILE"
echo "→ Dump: $(basename "$DUMP_FILE") ($(du -sh "$DUMP_FILE" | cut -f1))"

# ── Upload to server ──────────────────────────────────────────────────────────

echo "→ Uploading dump to server..."
ssh "$SSH_HOST" "mkdir -p $REMOTE_DIR/backups"
scp "$DUMP_FILE" "$SSH_HOST:$REMOTE_DIR/backups/"
REMOTE_DUMP="$REMOTE_DIR/backups/$(basename "$DUMP_FILE")"

# ── Restore into production DB container ─────────────────────────────────────

echo ""
echo "WARNING: This will overwrite all data in the production database."
read -r -p "Continue? [y/N] " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "Aborted. Dump is still on the server at: $REMOTE_DUMP"
    exit 0
fi

echo "→ Restoring into production DB container..."
ssh "$SSH_HOST" "cd $REMOTE_DIR && \
    docker compose exec -T db bash -c \
    'PGPASSWORD=$PROD_DB_PASS pg_restore \
        -U $PROD_DB_USER \
        -d raildashboard \
        --clean --if-exists \
        --no-owner --no-privileges' \
    < $REMOTE_DUMP"

echo "→ Done. Production DB has been updated."
echo "→ Dump kept at: $REMOTE_DUMP"
