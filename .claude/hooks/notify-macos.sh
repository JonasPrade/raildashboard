#!/bin/bash
# Hook: send a macOS notification when Claude finishes or needs user input.
# Works for both Stop and Notification hook events.

INPUT=$(cat)

# Determine event type and extract message
python3 - "$INPUT" <<'PYEOF'
import sys, json, subprocess

raw = sys.argv[1]
try:
    data = json.loads(raw)
except Exception:
    data = {}

hook_event = data.get("hook_event_name", "Stop")

if hook_event == "Notification":
    # Claude needs user input mid-task
    title = "Claude Code – Eingabe erforderlich"
    msg = data.get("message", "Claude wartet auf deine Antwort.")
else:
    # Stop – Claude finished responding
    title = "Claude Code – Fertig"
    msg = data.get("last_assistant_message", "Fertig – brauchst du noch etwas?").strip()

# Truncate safely
msg = msg[:120] + ("…" if len(msg) > 120 else "")

# Build AppleScript safely without shell interpolation
import shutil
if shutil.which("terminal-notifier"):
    subprocess.run(["terminal-notifier", "-title", title, "-message", msg, "-sound", "default"])
else:
    script = (
        'display notification '
        + json.dumps(msg, ensure_ascii=False)
        + ' with title '
        + json.dumps(title, ensure_ascii=False)
    )
    subprocess.run(["osascript", "-e", script])
PYEOF

exit 0
