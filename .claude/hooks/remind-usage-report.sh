#!/bin/bash
# Stop hook: Remind to run the usage-data report every 7 days.
# Tracks last reminder in ~/.claude/usage-report-last-reminder

STAMP_FILE="$HOME/.claude/usage-report-last-reminder"
INTERVAL_DAYS=7

now=$(date +%s)

if [ -f "$STAMP_FILE" ]; then
    last=$(cat "$STAMP_FILE")
    diff=$(( (now - last) / 86400 ))
else
    diff=$INTERVAL_DAYS
fi

if [ "$diff" -ge "$INTERVAL_DAYS" ]; then
    echo "---"
    echo "REMINDER: It has been ${diff} day(s) since the last usage-data report."
    echo "Ask Claude to generate the usage-data report for this project."
    echo "---"
    echo "$now" > "$STAMP_FILE"
fi

exit 0
