#!/usr/bin/env bash
# Runs on WorktreeCreate — symlinks apps/backend/.venv into the new worktree.
set -euo pipefail

REPO=/Users/jonas/Documents/coding/raildashboard
INPUT=$(cat)

# Try common field names for the worktree path
WORKTREE=$(echo "$INPUT" | jq -r '.worktree_path // .path // .tool_input.worktree_path // empty' 2>/dev/null || true)

if [ -z "$WORKTREE" ]; then
  exit 0
fi

SRC="$REPO/apps/backend/.venv"
DST="$WORKTREE/apps/backend/.venv"

if [ -e "$SRC" ] && [ ! -e "$DST" ]; then
  mkdir -p "$(dirname "$DST")"
  ln -s "$SRC" "$DST"
fi
