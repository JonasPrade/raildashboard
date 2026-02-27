# Contributor Guide – Schienendashboard

## Important Rules

This file applies to the entire repository. Read it before making any substantial change.

> **Default language:** English. Write code, comments, documentation, commit messages, and PR descriptions in English. UI strings displayed to end users are in German.

Coding rules:

- Always verify the full roundtrip works before opening a PR.



## How to approach tasks

Before writing any code:
1. **Read the relevant existing layer** (endpoint, CRUD function, component) — understand the pattern before adding to it.
2. **New API route checklist:** router endpoint + Pydantic schema + CRUD function + test + `make gen-api` to sync the frontend client.
3. **New frontend feature checklist:** component in `src/features/<name>/` + query/mutation hook in `queries.ts` + route in `router.tsx` if it's a page.
4. **Never add a dependency** without first checking whether an existing library already covers the need.

## Where to find more information
- Structure of project in `docs/architecture.md`
- The command of makefiles in `MAKEFILE`
- the setup of env variables in `docs/environment.md`
- architecture in `docs/architecture.md`
- Git Worfklow in `git_workflow.md`
- Testing in `docs/testing.md`


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





