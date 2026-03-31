---
description: Clean up changed code, commit (conventional), and push
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git add:*), Bash(git commit:*), Bash(git push:*)
argument-hint: [optional commit message hint]
---

## Context

- Staged and unstaged changes: !`git diff HEAD`
- Current git status: !`git status`
- Current branch: !`git branch --show-current`
- Recent commits (for style reference): !`git log --oneline -8`

## Your task

Execute the following three steps in order. Do not skip any step.

---

### Step 1 — Clean up the changed code

Use the Agent tool (subagent_type: general-purpose) to clean up the modified files.
Pass the agent the full list of changed files from the diff above and these instructions:

> Review the changed code for reuse, clarity, and quality. Apply the following:
> - Remove unnecessary complexity, nesting, or redundant code
> - Follow project conventions from CLAUDE.md (ES modules, explicit return types, explicit React Props types, no nested ternaries)
> - Never change what the code does — only how it reads
> - Do not add docstrings, comments, or type annotations to code you didn't change
> - Do not add error handling for scenarios that can't happen
> - Only touch files that were already modified

Wait for the agent to finish before proceeding.

---

### Step 2 — Propose a conventional commit message

Read the final diff (after cleanup) and determine:
- **type**: `feat` | `fix` | `docs` | `refactor` | `test` | `chore` | `style` | `perf`
- **scope**: the affected area, e.g. `backend`, `frontend`, `haushalt`, `auth`, `map`
- **description**: one short imperative sentence (max 72 chars total for the header)

**Language rule (AGENT.md):** commit message header, body, and all bullet points must be in **English**.

Optional hint from user: $ARGUMENTS

Show the proposed commit message and ask the user for confirmation before proceeding:

```
type(scope): description

[optional body if the change is non-obvious]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

---

### Step 3 — Commit and push

After the user confirms, stage all modified tracked files (never stage `.env*` files), create the commit with the agreed message, then push to origin with `git push`.
