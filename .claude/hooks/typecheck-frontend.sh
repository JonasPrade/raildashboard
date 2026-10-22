#!/bin/bash
# Post-edit check: after editing a frontend .ts/.tsx file, run the TypeScript
# compiler and report type errors back to Claude.
#
# Watches:
#   apps/frontend/**/*.ts
#   apps/frontend/**/*.tsx
#
# Skips silently when node_modules is missing (fresh checkout without npm install).
# Exit 2 + stderr feeds the errors back to Claude; everything else exits 0.

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null)

if ! echo "$FILE_PATH" | grep -qE "apps/frontend/.*\.tsx?$"; then
    exit 0
fi

FRONTEND="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}/apps/frontend"

if [ ! -d "$FRONTEND/node_modules" ]; then
    exit 0
fi

OUTPUT=$(cd "$FRONTEND" && npx --no-install tsc --noEmit 2>&1)
if [ $? -ne 0 ]; then
    echo "TypeScript errors after editing $FILE_PATH:" >&2
    echo "$OUTPUT" | head -20 >&2
    exit 2
fi

exit 0
