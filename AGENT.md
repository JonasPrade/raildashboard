# Contributor Guide – Schienendashboard

## Important Rules

This file applies to the entire repository. Read it before making any substantial change.

-  **Default language:** English. Write code, comments, documentation, commit messages, and PR descriptions in English. UI strings displayed to end users are in German.
-  **Commit messages must always be in English** — no exceptions, even if the conversation is in German.
- When asked to update or edit the roadmap, modify roadmap.md directly. Do NOT implement features unless explicitly asked to implement them.
- Never attempt roadmap items explicitly marked as **human task** — skip them entirely.
- When updating documentation, update ALL documentation layers (README, AGENT.md, roadmap.md, frontend docs, etc.) — not just a single file. Look also at the section ## Keep documentation in this file
- **Roadmap Style**: if a task is marked with [p] it means that it has to be planned first. If user asks for doing - create a plan and notice the whole plan in the roadmap.md - substitute the open task with a section started by a header with ###
 
## Feature Development Workflow

Features are documented in two layers:

- **`docs/roadmap.md`** — coarse overview: order, priority, high-level dependencies. No deep technical detail.
- **`docs/features/feature-<name>.md`** — one file per larger topic: goal, scope, desired behavior, acceptance criteria, technical notes.

**Rule of thumb:** if a topic fits in a few sentences → keep it in the roadmap. If it needs multiple sections → give it its own feature file and link it from the roadmap (`See: docs/features/feature-<name>.md`).

**Do NOT create `docs/superpowers/` or any other tool-internal subfolders under `docs/`.** All documentation and implementation plans belong in `docs/roadmap.md` or `docs/features/feature-<name>.md` — never in folders created by agentic tooling.

**Order of work:**
1. Feature file is written/updated first.
2. Code is written only after the feature file exists.
3. When the feature is done, mark it `[x]` in the roadmap.

## Review Checklist

After every **substantial** change — new endpoints, new UI, schema/migration changes, new features — rewrite `docs/review-checklist.md` from scratch. The file tells the user exactly what they must verify manually.

**Scope:**
- **Include:** concrete click paths and checks the user must perform (e.g. "open `/finves`, confirm SV-FinVes appear in their own section").
- **Exclude:** blockers on the agent's side (API keys, credentials) and open questions / risks — those belong in `docs/roadmap.md` or `docs/features/feature-<name>.md`.

**Format:** Written in German. Every item is an actionable checkbox (`- [ ]`) — never "check that everything works." File layout:

```markdown
# Review-Checkliste: <short task title>

_Stand: YYYY-MM-DD_

## Was du prüfen musst

- [ ] <concrete click path / check>
- [ ] <next check>
```

**Skip** the checklist for docs-only edits, typo fixes, comment/formatting changes, or anything that does not change behavior, UI, or data.

## Python Environment

- Always use the project virtualenv: `apps/backend/.venv/bin/python` (Python 3.13)
- Run tests with: `cd apps/backend && .venv/bin/python -m pytest`
- Never use system Python or `python3.11` directly

## How to approach tasks

Before writing any code:
1. **Read the relevant existing layer** (endpoint, CRUD function, component) — understand the pattern before adding to it.
2. **New API route checklist:** router endpoint + Pydantic schema + CRUD function + test + `make gen-api` to sync the frontend client.
3. **New frontend feature checklist:** component in `src/features/<name>/` + query/mutation hook in `queries.ts` + route in `router.tsx` if it's a page.
4. **Never add a dependency** without first checking whether an existing library already covers the need.

## Where to find more information
- Architecture & project structure: `docs/architecture.md`
- Makefile commands: `Makefile`
- Environment variables: `docs/environment.md`
- Git workflow: `docs/git_workflow.md`
- Testing: `docs/testing.md`


## Keep documentation

- Keep the documentation up to date
  - Keep `README.md` (root) up to date for project-wide setup and workflow changes.
  - Keep `apps/backend/README.md` up to date for backend-specific setup, routing API, and data imports.
  - Keep `apps/frontend/README.md` up to date for frontend-specific setup and project structure.
  - Keep `docs/production_setup.md` up to date for production deployment, backup system, and server configuration.
  - Update `apps/frontend/src/features/documentation/DocumentationPage.tsx` (the in-app docs) whenever the user-facing feature scope changes.
  - Project-wide architecture, data models, and the roadmap live in `docs/` (repo root).
  - Backend-specific implementation details live in `apps/backend/docs/`.
  - **Update `docs/roadmap.md`** whenever a feature is completed (mark `[ ]` → `[x]`) or a new planned feature is added. Keep it in sync with the actual state of the codebase.

