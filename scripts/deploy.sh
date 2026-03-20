#!/bin/bash
# deploy.sh — Upload production files to the server and restart the stack.
#
# Usage:
#   ./scripts/deploy.sh           # upload + restart
#   ./scripts/deploy.sh --upload  # upload only (no restart)
#
# Prerequisites:
#   - SSH alias "contabo" configured in ~/.ssh/config
#   - .env.prod exists locally (copy from .env.prod.example and fill in values)

set -e

SSH_HOST="contabo"
REMOTE_DIR="/srv/raildashboard"
RESTART=true

if [ "${1:-}" = "--upload" ]; then
  RESTART=false
fi

# Pick env file: prefer .env.prod, fall back to .env.prod.example
if [ -f .env.prod ]; then
  ENV_FILE=".env.prod"
elif [ -f .env.prod.example ]; then
  ENV_FILE=".env.prod.example"
  echo "WARNING: .env.prod not found, using .env.prod.example (fill in real values before deploying to production)."
else
  echo "ERROR: Neither .env.prod nor .env.prod.example found." >&2
  exit 1
fi

echo "→ Creating remote directory $REMOTE_DIR ..."
ssh "$SSH_HOST" "mkdir -p $REMOTE_DIR"

echo "→ Uploading files (env: $ENV_FILE) ..."
scp docker-compose.yml "$SSH_HOST:$REMOTE_DIR/docker-compose.yml"
# Upload as both .env.prod and .env so plain "docker compose up -d" works without --env-file.
scp "$ENV_FILE" "$SSH_HOST:$REMOTE_DIR/.env.prod"
scp "$ENV_FILE" "$SSH_HOST:$REMOTE_DIR/.env"

echo "→ Upload complete."

if [ "$RESTART" = true ]; then
  echo "→ Restarting stack on server ..."
  ssh "$SSH_HOST" "cd $REMOTE_DIR && docker compose --env-file .env.prod up --build -d"
  echo "→ Done. Logs: ssh $SSH_HOST 'cd $REMOTE_DIR && docker compose --env-file .env.prod logs -f'"
else
  echo "→ Skipped restart (--upload only)."
fi
