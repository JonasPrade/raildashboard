#!/bin/bash
# deploy.sh — Upload production files to the server and restart the stack.
#
# Usage:
#   ./scripts/deploy.sh            # upload .env + docker-compose.yml, then restart
#   ./scripts/deploy.sh --upload   # upload only (no restart)
#   ./scripts/deploy.sh --no-env   # skip env upload, only push docker-compose.yml + restart
#
# Prerequisites:
#   - SSH alias "contabo" configured in ~/.ssh/config
#   - .env exists locally (copy from .env.prod.example and fill in values)

set -e

SSH_HOST="contabo"
REMOTE_DIR="/srv/raildashboard"
RESTART=true
UPLOAD_ENV=true

for arg in "$@"; do
  case "$arg" in
    --upload) RESTART=false ;;
    --no-env) UPLOAD_ENV=false ;;
  esac
done

echo "→ Creating remote directory $REMOTE_DIR ..."
ssh "$SSH_HOST" "mkdir -p $REMOTE_DIR"

echo "→ Uploading docker-compose.yml ..."
scp docker-compose.yml "$SSH_HOST:$REMOTE_DIR/docker-compose.yml"

if [ "$UPLOAD_ENV" = true ]; then
  # Pick env file: prefer .env, fall back to .env.prod.example
  if [ -f .env ]; then
    ENV_FILE=".env"
  elif [ -f .env.prod.example ]; then
    ENV_FILE=".env.prod.example"
    echo "WARNING: .env not found, using .env.prod.example (fill in real values before deploying to production)."
  else
    echo "ERROR: Neither .env nor .env.prod.example found." >&2
    exit 1
  fi
  echo "→ Uploading env ($ENV_FILE → .env) ..."
  scp "$ENV_FILE" "$SSH_HOST:$REMOTE_DIR/.env"
else
  echo "→ Skipping env upload (--no-env)."
fi

echo "→ Upload complete."

if [ "$RESTART" = true ]; then
  echo "→ Restarting stack on server ..."
  ssh "$SSH_HOST" "cd $REMOTE_DIR && docker compose up --build -d"
  echo "→ Done. Logs: ssh $SSH_HOST 'cd $REMOTE_DIR && docker compose logs -f'"
else
  echo "→ Skipped restart (--upload only)."
fi
