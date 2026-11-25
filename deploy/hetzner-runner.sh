#!/usr/bin/env bash
# One-time setup of a GitHub Actions self-hosted runner on a Hetzner server
# (Ubuntu/Debian, linux/amd64). Run as root; steps: docs/ci-runner-hetzner.md.
#
#   RUNNER_TOKEN=<registration token> bash hetzner-runner.sh
#
# The token comes from GitHub (Settings -> Actions -> Runners -> New self-hosted
# runner) and is valid for one hour. It is read from the environment, never
# stored on disk. Re-running is safe: an installed runner is left alone.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/JonasPrade/raildashboard}"
RUNNER_USER="${RUNNER_USER:-gh-runner}"
RUNNER_DIR="${RUNNER_DIR:-/opt/actions-runner}"
RUNNER_LABELS="${RUNNER_LABELS:-hetzner}"
RUNNER_NAME="${RUNNER_NAME:-$(hostname)-ci}"
RUNNER_VERSION="${RUNNER_VERSION:-2.329.0}"

[ "$(id -u)" -eq 0 ] || { echo "run as root" >&2; exit 1; }
[ "$(uname -m)" = "x86_64" ] || {
  echo "linux/amd64 required: release.yml builds amd64 images for the amd64 prod host" >&2
  exit 1
}
command -v docker >/dev/null || { echo "install docker (with buildx) first" >&2; exit 1; }
docker buildx version >/dev/null || { echo "docker buildx plugin missing" >&2; exit 1; }

id "$RUNNER_USER" >/dev/null 2>&1 || useradd --create-home --shell /bin/bash "$RUNNER_USER"
# Group docker is root-equivalent on this host: the runner user must not hold
# anything but this repo's CI (private repo, no fork PRs).
usermod -aG docker "$RUNNER_USER"

if [ ! -x "$RUNNER_DIR/svc.sh" ]; then
  [ -n "${RUNNER_TOKEN:-}" ] || { echo "set RUNNER_TOKEN" >&2; exit 1; }
  mkdir -p "$RUNNER_DIR"
  curl -fsSL --retry 5 -o /tmp/actions-runner.tar.gz \
    "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
  tar -xzf /tmp/actions-runner.tar.gz -C "$RUNNER_DIR"
  rm -f /tmp/actions-runner.tar.gz
  chown -R "$RUNNER_USER":"$RUNNER_USER" "$RUNNER_DIR"
  "$RUNNER_DIR/bin/installdependencies.sh"
  sudo -u "$RUNNER_USER" "$RUNNER_DIR/config.sh" --unattended \
    --url "$REPO_URL" --token "$RUNNER_TOKEN" \
    --name "$RUNNER_NAME" --labels "$RUNNER_LABELS" --work _work
  (cd "$RUNNER_DIR" && ./svc.sh install "$RUNNER_USER" && ./svc.sh start)
fi

# Docker keeps every layer the CI builds; without a prune the disk fills up.
cat >/etc/cron.daily/ci-docker-prune <<'EOF'
#!/bin/sh
docker builder prune -f --filter until=168h >/dev/null
docker image prune -f --filter until=168h >/dev/null
EOF
chmod +x /etc/cron.daily/ci-docker-prune

echo "Runner '$RUNNER_NAME' installed with label '$RUNNER_LABELS'."
echo "Next: set the repo variable CI_RUNNER=$RUNNER_LABELS (docs/ci-runner-hetzner.md)."
