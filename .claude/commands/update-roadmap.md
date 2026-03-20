---
description: Mark a completed feature in docs/roadmap.md and check documentation
allowed-tools: Read, Edit, Grep, Glob
argument-hint: [feature-description]
---

## Context

Current open roadmap items:
!`grep -n "\[ \]" docs/roadmap.md | head -40`

## Your task

The user has completed a feature. Your argument (if provided): $ARGUMENTS

**Step 1 — Identify the completed item**

If `$ARGUMENTS` is provided, find the best-matching `[ ]` entry in `docs/roadmap.md` and confirm it with the user before changing anything.
If no argument is given, ask the user which item they completed (show the list of open `[ ]` items from the roadmap).

**Step 2 — Mark it done**

Change the matching `[ ]` to `[x]` in `docs/roadmap.md`. Edit only that line — do not reformat or reorder anything else.

**Step 3 — Check documentation coverage**

After marking the item, check whether the completed feature is already documented in all relevant places. There are three levels of documentation in this project:

| Level | File |
|---|---|
| Project-wide | `README.md` (root) |
| Backend-specific | `apps/backend/README.md` |
| Frontend-specific | `apps/frontend/README.md` |

For each file, briefly check whether it already mentions the feature. Use `Grep` to search for key terms from the feature description.

**Step 4 — Handle `@AI` annotations**

Scan `docs/roadmap.md` for any lines containing `@AI`. Each such line is an inline task left for you to complete. The text after `@AI -` describes what to do (e.g. `@AI - finished, move it to finished section`).

For each `@AI` annotation found:
1. Read the instruction and carry it out (e.g. move a completed item to the finished/done section, reformat an entry, delete obsolete text, etc.).
2. Remove the `@AI` annotation from the line once the task is done.

If no `@AI` annotations exist, skip this step silently.

**Step 5 — Report**

Summarise what you changed and list which documentation files still need updating (if any). Do not edit the README files yourself — just report what is missing so the user can decide.
