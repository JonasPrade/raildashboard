#!/bin/bash
# Post-edit reminder: after editing feature files or API endpoints,
# remind to update docs/roadmap.md if the change affects a feature.
#
# Watches:
#   apps/frontend/src/features/**
#   apps/backend/dashboard_backend/api/**

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null)

if echo "$FILE_PATH" | grep -qE "apps/(frontend/src/features|backend/dashboard_backend/api)/"; then
    echo "REMINDER: You edited a feature or API endpoint."
    echo "If this completes or changes a roadmap item, update docs/roadmap.md."
fi

exit 0
