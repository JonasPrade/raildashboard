#!/bin/sh
# Database backup before the migration. Runs as the one-shot `backup` service in
# compose.yaml; the backend (whose entrypoint runs `alembic upgrade head`) only
# starts after this exited 0. No backup, no update (DEPLOY.md).
#
# It lives in the db image so pg_dump matches the server version exactly, and in
# the stack rather than in deploy/prod.sh so it also applies when someone brings
# the stack up by hand.
set -eu

# prod.sh sets this on its rollback only. The rollback needs no new dump: either
# the forward backup failed (then nothing was migrated) or its dump is already
# in backups/. Without the skip, a backup that keeps failing (disk full) would
# also keep the previous release from coming back up.
if [ "${BACKUP_SKIP:-0}" = "1" ]; then
    echo "[backup] BACKUP_SKIP=1 (rollback) – no dump."
    exit 0
fi

dir="${BACKUP_DIR:-/backups}"
keep="${BACKUP_KEEP:-10}"
tag="$(printf '%s' "${IMAGE_TAG:-untagged}" | cut -c1-12)"
target="${dir}/pre-migrate_$(date +%Y%m%d_%H%M%S)_${tag}.dump"

mkdir -p "$dir"
export PGPASSWORD="${DB_PASSWORD:?DB_PASSWORD missing}"
if ! pg_dump -h "${DB_HOST:-db}" -U "${DB_USER:?DB_USER missing}" -Fc raildashboard > "${target}.part"; then
    rm -f "${target}.part"
    echo "[backup] ERROR: pg_dump failed. Aborting before the migration." >&2
    exit 1
fi
if [ ! -s "${target}.part" ]; then
    rm -f "${target}.part"
    echo "[backup] ERROR: dump is empty. Aborting before the migration." >&2
    exit 1
fi
mv "${target}.part" "$target"
echo "[backup] ${target} ($(du -h "$target" | cut -f1))"

# Retention: the newest $keep pre-migrate dumps. Other files in the directory
# (pre-deploy_* from the old deploy.sh, manual dumps) are left alone.
ls -1t "$dir"/pre-migrate_*.dump 2>/dev/null | tail -n +"$((keep + 1))" | while read -r old; do
    rm -f -- "$old"
    echo "[backup] removed old backup ${old}"
done
