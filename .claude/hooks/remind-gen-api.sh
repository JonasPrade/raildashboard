#!/bin/bash
# Post-edit reminder: after editing backend schemas or endpoints,
# remind to run `make gen-api` so the frontend OpenAPI client stays in sync.
#
# Watches:
#   apps/backend/dashboard_backend/schemas/**
#   apps/backend/dashboard_backend/api/**

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null)

if echo "$FILE_PATH" | grep -qE "apps/backend/dashboard_backend/(schemas|api)/"; then
    echo "REMINDER: You edited a backend schema or endpoint."
    echo "If the OpenAPI contract changed, run: make gen-api"
fi

exit 0
