#!/usr/bin/env bash
# Drives deploy/prod.sh against a stubbed `docker` and checks what it does to
# .env and which docker calls it makes. Part of `make test`.
#
# The stub reads its behaviour from files in $STUB:
#   local      image references that `docker image inspect` finds
#   pull_fail  image references whose `docker pull` fails
#   up_fail    IMAGE_TAG values for which `docker compose up -d` fails
#   unhealthy  IMAGE_TAG values for which the backend reports "unhealthy"
# and logs every call to $STUB/calls.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OLD=1111111111111111111111111111111111111111
NEW=2222222222222222222222222222222222222222
IMG=ghcr.io/jonasprade/raildashboard
failures=0

setup() {
    WORK="$(mktemp -d)"
    STUB="$WORK/stub"
    mkdir -p "$STUB/bin" "$WORK/srv"
    cp "$HERE/prod.sh" "$WORK/srv/prod.sh"
    touch "$WORK/srv/compose.yaml" "$STUB/local" "$STUB/pull_fail" "$STUB/up_fail" "$STUB/unhealthy" "$STUB/calls"
    printf 'DB_USER=raildashboard\nIMAGE_TAG=%s\n' "$OLD" > "$WORK/srv/.env"
    cat > "$STUB/bin/docker" <<'EOF'
#!/usr/bin/env bash
echo "${BACKUP_SKIP:+BACKUP_SKIP=$BACKUP_SKIP }docker $*" >> "$STUB/calls"
tag="$(grep -oP '^IMAGE_TAG=\K.*' .env 2>/dev/null || true)"
case "$1 ${2:-}" in
    "image inspect") grep -qxF "$3" "$STUB/local" ;;
    "pull --quiet")  ! grep -qxF "$3" "$STUB/pull_fail" ;;
    "compose up")    ! grep -qxF "$tag" "$STUB/up_fail" ;;
    "compose ps")    echo "cid-backend" ;;
    "compose logs")  exit 0 ;;
    "inspect --format")
        if grep -qxF "$tag" "$STUB/unhealthy"; then echo unhealthy; else echo healthy; fi ;;
    *) echo "unexpected docker call: $*" >&2; exit 99 ;;
esac
EOF
    chmod +x "$STUB/bin/docker"
}

run() {  # run prod.sh with the stub; sets RC and OUT
    set +e
    OUT="$(cd /; PATH="$STUB/bin:$PATH" STUB="$STUB" "$@" 2>&1)"
    RC=$?
    set -e
}

check() {  # check <description> <condition...>
    local what="$1"; shift
    if "$@"; then
        echo "  ok   $what"
    else
        echo "  FAIL $what"
        echo "$OUT" | sed 's/^/       | /'
        failures=$((failures + 1))
    fi
}

tag_is() { grep -qx "IMAGE_TAG=$1" "$WORK/srv/.env"; }
pulls() { grep -c '^docker pull' "$STUB/calls" || true; }

echo "prod.sh: invalid SHA via SSH_ORIGINAL_COMMAND"
setup
run env SSH_ORIGINAL_COMMAND='x kaputt' "$WORK/srv/prod.sh"
check "exit 2" test "$RC" -eq 2
check "no docker call" test ! -s "$STUB/calls"
check ".env unchanged" tag_is "$OLD"

echo "prod.sh: injection attempt is cut to the last word and rejected"
setup
run env SSH_ORIGINAL_COMMAND="/srv/raildashboard/prod.sh $NEW; rm -rf /" "$WORK/srv/prod.sh"
check "exit 2" test "$RC" -eq 2
check "no docker call" test ! -s "$STUB/calls"

echo "prod.sh: short SHA as argument"
setup
run "$WORK/srv/prod.sh" "${NEW:0:7}"
check "exit 2" test "$RC" -eq 2

echo "prod.sh: normal case via SSH_ORIGINAL_COMMAND"
setup
run env SSH_ORIGINAL_COMMAND="/srv/raildashboard/prod.sh $NEW" "$WORK/srv/prod.sh"
check "exit 0" test "$RC" -eq 0
check "log line names old and new SHA" grep -qF "==> Deploy $OLD -> $NEW" <<< "$OUT"
check "all four images pulled" test "$(pulls)" -eq 4
check "pulled before up" bash -c "grep -n '' '$STUB/calls' | grep -m1 'pull' | cut -d: -f1 | { read p; u=\$(grep -n 'compose up' '$STUB/calls' | head -1 | cut -d: -f1); test \"\$p\" -lt \"\$u\"; }"
check ".env on new SHA" tag_is "$NEW"

echo "prod.sh: pull fails"
setup
echo "$IMG-frontend:$NEW" > "$STUB/pull_fail"
run "$WORK/srv/prod.sh" "$NEW"
check "exit 1" test "$RC" -eq 1
check ".env unchanged" tag_is "$OLD"
check "no compose up" bash -c "! grep -q 'compose up' '$STUB/calls'"

echo "prod.sh: up fails for the new SHA -> rollback"
setup
echo "$NEW" > "$STUB/up_fail"
run "$WORK/srv/prod.sh" "$NEW"
check "exit 1" test "$RC" -eq 1
check ".env back on old SHA" tag_is "$OLD"
check "up called twice (new, then rollback)" test "$(grep -c 'compose up' "$STUB/calls")" -eq 2
check "reports rollback" grep -qF "Rolled back to $OLD" <<< "$OUT"
check "forward up takes a backup" bash -c "grep 'compose up' '$STUB/calls' | head -1 | grep -q '^docker compose up'"
check "rollback up skips the backup" bash -c "grep 'compose up' '$STUB/calls' | tail -1 | grep -q '^BACKUP_SKIP=1 docker compose up'"

echo "prod.sh: new SHA unhealthy -> rollback"
setup
echo "$NEW" > "$STUB/unhealthy"
run "$WORK/srv/prod.sh" "$NEW"
check "exit 1" test "$RC" -eq 1
check ".env back on old SHA" tag_is "$OLD"

echo "prod.sh: images already local -> no pull"
setup
for s in backend frontend db graphhopper; do echo "$IMG-$s:$NEW"; done > "$STUB/local"
run "$WORK/srv/prod.sh" "$NEW"
check "exit 0" test "$RC" -eq 0
check "no pull" test "$(pulls)" -eq 0
check ".env on new SHA" tag_is "$NEW"

echo "prod.sh: previous tag is not a SHA -> no blind rollback"
setup
sed -i "s|^IMAGE_TAG=.*|IMAGE_TAG=v0.0.14|" "$WORK/srv/.env"
echo "$NEW" > "$STUB/up_fail"
run "$WORK/srv/prod.sh" "$NEW"
check "exit 1" test "$RC" -eq 1
check "says CRITICAL" grep -qF "CRITICAL: no previous SHA" <<< "$OUT"

echo "prod.sh: override file present"
setup
touch "$WORK/srv/compose.override.yaml"
run "$WORK/srv/prod.sh" "$NEW"
check "exit 1" test "$RC" -eq 1
check "no docker call" test ! -s "$STUB/calls"
check ".env unchanged" tag_is "$OLD"

if ((failures)); then
    echo "prod.sh: $failures check(s) failed" >&2
    exit 1
fi
echo "prod.sh: all checks passed"
