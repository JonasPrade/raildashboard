#!/usr/bin/env bash
# deploy.sh — server-side production deploy for the tag-based CI/CD pipeline.
#
# Runs ON THE SERVER in the compose directory (default /srv/raildashboard). The GitHub
# Actions `deploy` job uploads this script + docker-compose.yml, then invokes:
#
#   GHCR_USER=<actor> GHCR_TOKEN=<pat> ./deploy.sh v1.2.0
#
# It can also be run by hand for a manual deploy or rollback:
#
#   cd /srv/raildashboard && ./deploy.sh v1.1.0
#
# Sequence (Manual §"Backup vor Migration" + health-wait + rollback):
#   1. Capture the currently running IMAGE_TAG (rollback anchor).
#   2. Back up the database BEFORE anything changes. Backup fails ⇒ deploy aborts.
#      (Migrations run inside the backend entrypoint on `up -d`; an image rollback does
#       NOT undo a schema/data migration — the pre-deploy dump is the only way back.)
#   3. Point IMAGE_TAG at the new release, `docker compose pull`, `docker compose up -d`.
#   4. Wait for the backend healthcheck to report `healthy`.
#   5. On health failure, roll IMAGE_TAG back to the previous version and bring it up again.
#
# Requires on the server: docker + docker compose v2, a filled-in .env, and (for private
# GHCR packages) either GHCR_TOKEN in the environment or a prior `docker login ghcr.io`.

set -euo pipefail

# ── Arguments & environment ───────────────────────────────────────────────────

TARGET_TAG="${1:-}"
if [ -z "$TARGET_TAG" ]; then
    echo "Usage: ./deploy.sh <IMAGE_TAG>   (e.g. ./deploy.sh v1.2.0)" >&2
    exit 2
fi

REMOTE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REMOTE_DIR"

ENV_FILE=".env"
COMPOSE_FILE="docker-compose.yml"
BACKUP_DIR="backups"
HEALTH_TIMEOUT=180        # seconds to wait for the backend to become healthy
RETENTION_DAYS=14

if [ ! -f "$ENV_FILE" ]; then
    echo "✗ $ENV_FILE not found in $REMOTE_DIR — cannot deploy." >&2
    exit 1
fi
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "✗ $COMPOSE_FILE not found in $REMOTE_DIR — cannot deploy." >&2
    exit 1
fi

# Never let a local docker-compose.override.yml (build blocks) sneak in on the server.
if [ -f docker-compose.override.yml ]; then
    echo "✗ docker-compose.override.yml present on the server — the server must not build." >&2
    echo "  Remove it; production pulls GHCR images only." >&2
    exit 1
fi

read_env() { grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d'=' -f2- | tr -d '"'"'" || true; }

PREVIOUS_TAG="$(read_env IMAGE_TAG)"
DB_USER="$(read_env DB_USER)"; DB_USER="${DB_USER:-raildashboard}"

echo "→ Deploying raildashboard $TARGET_TAG (previous: ${PREVIOUS_TAG:-none})"

# ── Optional GHCR login so the server can pull private images ──────────────────

if [ -n "${GHCR_TOKEN:-}" ]; then
    echo "→ Logging in to GHCR as ${GHCR_USER:-token}"
    echo "$GHCR_TOKEN" | docker login ghcr.io -u "${GHCR_USER:-x}" --password-stdin
fi

# ── Helper: set IMAGE_TAG in .env (replace or append) ─────────────────────────

set_image_tag() {
    local tag="$1"
    if grep -qE '^IMAGE_TAG=' "$ENV_FILE"; then
        sed -i -E "s|^IMAGE_TAG=.*|IMAGE_TAG=$tag|" "$ENV_FILE"
    else
        printf '\nIMAGE_TAG=%s\n' "$tag" >> "$ENV_FILE"
    fi
}

# ── Step 1+2: DB backup BEFORE migrations (gate — no backup, no update) ────────

mkdir -p "$BACKUP_DIR"
DB_CID="$(docker compose ps -q db 2>/dev/null || true)"

if [ -n "$DB_CID" ] && [ -n "$(docker ps -q --filter "id=$DB_CID")" ]; then
    TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
    PRE_DUMP="$BACKUP_DIR/pre-deploy_${TARGET_TAG}_${TIMESTAMP}.dump"
    echo "→ Backing up database before migration: $PRE_DUMP"
    if ! docker compose exec -T db pg_dump -U "$DB_USER" -Fc raildashboard > "$PRE_DUMP"; then
        echo "✗ pg_dump failed — aborting deploy (no backup, no update)." >&2
        rm -f "$PRE_DUMP"
        exit 1
    fi
    if [ ! -s "$PRE_DUMP" ]; then
        echo "✗ Backup file is empty — aborting deploy (no backup, no update)." >&2
        rm -f "$PRE_DUMP"
        exit 1
    fi
    echo "→ Backup OK ($(du -h "$PRE_DUMP" | cut -f1))."
    # Prune pre-deploy dumps older than the retention window.
    find "$BACKUP_DIR" -maxdepth 1 -name 'pre-deploy_*.dump' -mtime "+$RETENTION_DAYS" -delete 2>/dev/null || true
else
    echo "→ No running database container found — treating this as a first bootstrap."
    echo "  Skipping the pre-deploy backup (there is no existing data to protect)."
fi

# ── Step 3: switch tag, pull, start ───────────────────────────────────────────

echo "→ Setting IMAGE_TAG=$TARGET_TAG in $ENV_FILE"
set_image_tag "$TARGET_TAG"

echo "→ Pulling images for $TARGET_TAG ..."
docker compose pull

echo "→ Starting stack ..."
docker compose up -d

# ── Step 4: wait for the backend to become healthy ────────────────────────────

wait_healthy() {
    local cid status deadline
    cid="$(docker compose ps -q backend)"
    if [ -z "$cid" ]; then
        echo "✗ backend container not found after up -d." >&2
        return 1
    fi
    deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
    while [ "$(date +%s)" -lt "$deadline" ]; do
        status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null || echo unknown)"
        case "$status" in
            healthy) echo "→ backend healthy."; return 0 ;;
            unhealthy) echo "✗ backend reported unhealthy." >&2; return 1 ;;
        esac
        sleep 5
    done
    echo "✗ backend did not become healthy within ${HEALTH_TIMEOUT}s." >&2
    return 1
}

if wait_healthy; then
    echo "✓ Deploy of $TARGET_TAG succeeded."
    exit 0
fi

# ── Step 5: rollback to the previous immutable tag ────────────────────────────

echo "✗ Health check failed — rolling back." >&2
docker compose logs --tail=50 backend >&2 || true

if [ -z "$PREVIOUS_TAG" ] || [ "$PREVIOUS_TAG" = "$TARGET_TAG" ]; then
    echo "✗ No distinct previous tag to roll back to (was '$PREVIOUS_TAG')." >&2
    echo "  Stack left running on $TARGET_TAG — investigate manually." >&2
    exit 1
fi

echo "→ Restoring IMAGE_TAG=$PREVIOUS_TAG and restarting ..."
set_image_tag "$PREVIOUS_TAG"
docker compose pull
docker compose up -d

if wait_healthy; then
    echo "✓ Rolled back to $PREVIOUS_TAG successfully. The $TARGET_TAG release was NOT deployed." >&2
else
    echo "✗ Rollback to $PREVIOUS_TAG also unhealthy — manual intervention required." >&2
fi
exit 1
