# Claude Code Permissions

`settings.local.json` lists what runs without a prompt. Everything else requires approval.

## Not auto-allowed — use these instead

| Removed | Why | Alternative |
|---|---|---|
| `curl:*` | Can exfiltrate data, pipe malicious scripts | Use the built-in **`WebFetch` tool** |
| `source:*` | Executes arbitrary shell code | Not needed — shell state doesn't persist between Bash calls; call venv Python directly via wrapper |
| `Read(//Users/jonas/**)` | Exposes SSH keys, credentials, browser data | Scoped to project + `/data/`; reading outside prompts for approval |
| `osascript:*` | Full AppleScript control (keychain, UI, messages) | Notifications work via hooks in `settings.json` — no direct Bash access needed |
| `brew upgrade:*` | System-wide package changes | Run manually: `! brew upgrade <pkg>` |
| `grep:*` | Should use dedicated tool, not Bash | Use the built-in **`Grep` tool** |

## Wrapper scripts (`.claude/bin/`)

Instead of broad `python:*` / `python3:*` wildcards, three scoped wrappers are allowed:

| Script | What it does | Replaces |
|---|---|---|
| `run-tests` | Runs pytest from `apps/backend/` with the venv | `python3:*`, `.venv/bin/python3.11:*`, all hardcoded pytest invocations |
| `run-migration` | Runs `alembic upgrade head` only | `.venv/bin/alembic upgrade:*`, ad-hoc `cd && alembic` calls |
| `run-python-script` | Runs scripts in `scripts/` only, rejects `-c` and other paths | All `python scripts/dump_*.py` invocations |

## Adding new permissions

If Claude prompts for a command you want auto-allowed:
- For a new pytest pattern: no change needed, `run-tests` passes all args through
- For a new script: put it in `apps/backend/scripts/`, then `run-python-script scripts/new_script.py`
- For a new npm package: covered by `npm:*`
- For a one-off that doesn't fit: approve once in the prompt, or add a scoped rule to `settings.local.json`
