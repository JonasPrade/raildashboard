---
description: Conventional Commit helper — proposes a commit message in type(scope): description format
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git add:*), Bash(git commit:*)
argument-hint: [optional message hint]
---

## Context

- Staged and unstaged changes: !`git diff HEAD`
- Current git status: !`git status`
- Recent commits (for style reference): !`git log --oneline -8`

## Your task

Create a conventional commit for the staged changes. If nothing is staged yet, stage all modified tracked files first.

**Step 1 — Analyse the diff**

Read the diff above and determine:
- **type**: `feat` | `fix` | `docs` | `refactor` | `test` | `chore` | `style` | `perf`
- **scope**: the affected area, e.g. `backend`, `frontend`, `haushalt`, `auth`, `map`, `hooks`, `ci`
- **description**: one short imperative sentence (max 72 chars total for the header)

> **Language rule (AGENT.md):** commit message header, body, and all bullet points must be in **English** — even if the conversation is in German.

Optional hint from user: $ARGUMENTS

**Step 2 — Propose the message**

Show the proposed commit in this format and ask for confirmation:

```
type(scope): description

[optional body if the change is non-obvious]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

Wait for the user to confirm or provide corrections before committing.

**Step 3 — Commit**

After confirmation, stage any unstaged changes for modified tracked files (never stage `.env*` files) and create the commit with the agreed message.
