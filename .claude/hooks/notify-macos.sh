#!/bin/bash
# Stop hook: send a macOS notification when Claude finishes responding
# and is waiting for user input.

INPUT=$(cat)

# Extract the last assistant message for the notification body (first 80 chars)
LAST_MSG=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
msg = data.get('last_assistant_message', '').strip()
# Truncate to ~80 chars for the notification subtitle
print(msg[:80] + ('…' if len(msg) > 80 else ''))
" 2>/dev/null)

if [ -z "$LAST_MSG" ]; then
    LAST_MSG="Fertig – brauchst du noch etwas?"
fi

osascript -e "display notification \"$LAST_MSG\" with title \"Claude Code\" subtitle \"Fertig – deine Eingabe ist gefragt\""

exit 0
