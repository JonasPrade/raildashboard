#!/bin/bash
# Post-edit reminder: after editing backend models,
# remind to create an Alembic migration.
#
# Watches:
#   apps/backend/dashboard_backend/models/**

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null)

if echo "$FILE_PATH" | grep -qE "apps/backend/dashboard_backend/models/"; then
    echo "REMINDER: You edited a backend model."
    echo "If the database schema changed, create an Alembic migration:"
    echo "  make migrate-create MSG=\"describe your change\""
fi

exit 0
