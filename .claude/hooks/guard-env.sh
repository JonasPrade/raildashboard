#!/bin/bash
# Pre-edit guard: blocks Claude from editing .env and .env.test files.
# These files contain secrets and must only be changed manually.
#
# Claude passes the tool input as JSON on stdin:
# { "tool_name": "Edit"|"Write", "tool_input": { "file_path": "..." } }

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null)

BASENAME=$(basename "$FILE_PATH")

if [[ "$BASENAME" == ".env" ]] || [[ "$BASENAME" == ".env.test" ]]; then
    echo "BLOCKED: Editing '$FILE_PATH' is not allowed." >&2
    echo ".env and .env.test contain secrets and must never be modified by Claude." >&2
    echo "Make any necessary changes manually." >&2
    exit 2
fi

exit 0
