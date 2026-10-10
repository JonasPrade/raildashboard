#!/usr/bin/env bash
# Server-side deploy script. Lives on the Contabo host (vmd92747) as
# /srv/raildashboard/prod.sh and is called by .github/workflows/deploy.yml over
# SSH (contract and setup: DEPLOY.md). Adapted from JonasPrade/dtakt_mitglied.
#
# Flow: check SHA -> pull the four images -> IMAGE_TAG in .env -> up -d ->
# wait for "healthy" -> optional Healthchecks ping. If the backend does not
# become healthy, back to the previous SHA; its images are still local and
# bit-identical to what ran. That holds as long as migrations stay
# backward-compatible – and because the older backend's entrypoint does not try
# to migrate a database that is already ahead (apps/backend/scripts/db_ahead.py).
#
# Pull BEFORE switching .env: if the pull fails (GHCR login expired, typo), .env
# stays untouched and the previous SHA remains the way back. The other way round,
# the next attempt would take the never-deployed SHA for the previous one.
#
# Backup and migration are not in here. The one-shot `backup` service in
# compose.yaml dumps the database to backups/ before the backend starts and
# migrates; that way they also apply when someone brings the stack up by hand.
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE_PREFIX="ghcr.io/jonasprade/raildashboard"   # as in compose.yaml
SERVICES=(backend frontend db graphhopper)         # images per SHA
HEALTH_TIMEOUT=180   # seconds, incl. backup + migration before the backend starts

cd "$APP_DIR"

# --- Determine the argument and check it strictly ---------------------------
# The deploy key carries a forced command in authorized_keys WITHOUT
# interpolation. What the caller sends is in SSH_ORIGINAL_COMMAND and is checked
# here instead of landing unfiltered as an argument.
requested="${1:-}"
if [[ -z "$requested" && -n "${SSH_ORIGINAL_COMMAND:-}" ]]; then
    requested="${SSH_ORIGINAL_COMMAND##* }"
fi
if [[ ! "$requested" =~ ^[0-9a-f]{40}$ ]]; then
    echo "ERROR: '${requested}' is not a full commit SHA." >&2
    echo "Usage: prod.sh <40-character-commit-sha>" >&2
    exit 2
fi
NEW_SHA="$requested"

for f in .env compose.yaml; do
    [[ -f "$f" ]] || { echo "ERROR: $APP_DIR/$f missing." >&2; exit 1; }
done
# Compose would load an override file on top and build or change the stack.
for f in compose.override.yaml compose.override.yml docker-compose.override.yml docker-compose.override.yaml; do
    if [[ -f "$f" ]]; then
        echo "ERROR: $f present on the server – the server must not build. Remove it." >&2
        exit 1
    fi
done

old_sha="$(grep -oP '^IMAGE_TAG=\K.*' .env || true)"
old_sha="${old_sha:-none}"
echo "==> Deploy ${old_sha} -> ${NEW_SHA}"

# --- Healthchecks -------------------------------------------------------------
# Optional: without HEALTHCHECK_URL in .env nothing happens.
hc_url="$(grep -oP '^HEALTHCHECK_URL=\K.*' .env || true)"
ping_hc() {
    [[ -n "$hc_url" ]] || return 0
    curl -fsS -m 10 --retry 3 ${2:+--data-raw "$2"} "${hc_url}${1}" > /dev/null 2>&1 || true
}

set_tag() {
    if grep -q '^IMAGE_TAG=' .env; then
        sed -i "s|^IMAGE_TAG=.*|IMAGE_TAG=$1|" .env
    else
        printf '\nIMAGE_TAG=%s\n' "$1" >> .env
    fi
}

wait_healthy() {
    local deadline=$((SECONDS + HEALTH_TIMEOUT)) cid status
    while ((SECONDS < deadline)); do
        cid="$(docker compose ps -q backend 2>/dev/null || true)"
        status="$(docker inspect --format '{{.State.Health.Status}}' "$cid" 2>/dev/null || echo waiting)"
        case "$status" in
            healthy) return 0 ;;
            unhealthy) return 1 ;;
        esac
        sleep 5
    done
    return 1
}

ping_hc "/start"

# A SHA tag never changes; if the image is already local, it is the right one.
# That also keeps states reachable that are only tagged locally (DEPLOY.md, Rollback).
for svc in "${SERVICES[@]}"; do
    image="${IMAGE_PREFIX}-${svc}:${NEW_SHA}"
    if ! docker image inspect "$image" > /dev/null 2>&1 \
        && ! docker pull --quiet "$image"; then
        msg="Pull of ${image} failed (GHCR login of user $(id -un) expired?) – nothing changed, ${old_sha} keeps running."
        echo "==> ERROR: ${msg}" >&2
        ping_hc "/fail" "$msg"
        exit 1
    fi
done

set_tag "$NEW_SHA"

# `up` is part of the condition: if creating the stack already fails (backup
# failed, compose file broken), the same rollback applies instead of `set -e`
# leaving the new SHA in .env.
if docker compose up -d && wait_healthy; then
    echo "==> OK: ${NEW_SHA} is healthy."
    ping_hc ""
    exit 0
fi

echo "==> ERROR: ${NEW_SHA} did not become healthy – rolling back to ${old_sha}." >&2
docker compose logs --tail 100 backup backend >&2 || true
if [[ ! "$old_sha" =~ ^[0-9a-f]{40}$ ]]; then
    msg="CRITICAL: no previous SHA to roll back to (was '${old_sha}') – manual intervention required."
    echo "==> ${msg}" >&2
    ping_hc "/fail" "$msg"
    exit 1
fi
set_tag "$old_sha"
# No new dump on the way back: either the forward backup failed (then nothing
# was migrated) or its dump is already in backups/. A backup that keeps failing
# must not also keep the previous release down.
if BACKUP_SKIP=1 docker compose up -d && wait_healthy; then
    msg="Rolled back to ${old_sha}; ${NEW_SHA} did not become healthy."
    echo "==> ${msg} (code rollback only; restore the database from backups/ if the migration ran, see DEPLOY.md)" >&2
else
    msg="CRITICAL: neither ${NEW_SHA} nor ${old_sha} is healthy – manual intervention required."
    echo "==> ${msg}" >&2
fi
ping_hc "/fail" "$msg"
exit 1
