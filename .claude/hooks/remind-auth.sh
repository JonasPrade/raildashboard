#!/bin/bash
# Post-edit reminder: after editing backend endpoints,
# remind to verify authentication dependencies on new/changed routes.
#
# Watches:
#   apps/backend/dashboard_backend/api/v1/endpoints/**
#   apps/backend/dashboard_backend/routing/**

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null)

if echo "$FILE_PATH" | grep -qE "apps/backend/dashboard_backend/(api/v1/endpoints|routing)/"; then
    echo "REMINDER: You edited a backend endpoint."
    echo "Ensure every new route has the correct auth dependency (require_editor, require_admin, etc.)."
    echo "Run /audit-auth to get a full endpoint security report."
fi

exit 0
