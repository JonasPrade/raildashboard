# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Each production release is cut by tagging a commit `vX.Y.Z` (see AGENT.md → Release &
docs/production_setup.md → Deploy-Vertrag). Pushing the tag triggers the CI/CD pipeline
(`.github/workflows/deploy.yml`). Move entries from **[Unreleased]** into a dated version
section as part of the release commit, immediately before tagging.

## [Unreleased]

### Added
- "Anleitungen" guides: four new guide pages (VIB report import, media/press
  extraction, project creation wizard, geometry editor) with illustrative
  non-interactive example views ("Beispielansicht") in every guide.
- In-app guide editing: guide texts are now markdown sections that users with the
  new `guides.edit` capability (group "Inhalte"; admins implicitly) can override
  per section. Overrides live in the new `guide_section_override` table
  (migration `20260707001`) behind `GET/PUT/DELETE
  /api/v1/guides/{slug}/overrides[/{section_key}]` and can be reset to the
  bundled default at any time.
- Tag-based CI/CD pipeline (`.github/workflows/deploy.yml`): pushing a `v*` tag runs the
  quality gates (backend `pytest`, frontend `tsc` + `eslint`), builds the `backend`, `frontend`, and
  `db` images, pushes them to GHCR double-tagged `:vX.Y.Z` + `:latest`, and deploys via SSH.
- `scripts/deploy.sh` rewritten as a server-side deploy: pre-migration DB backup (aborts the
  deploy if it fails), `docker compose pull`, `up -d`, health-wait, and automatic rollback to
  the previous immutable image tag on failure.
- `docker-compose.override.yml` for local development builds, keeping the production
  `docker-compose.yml` build-free (pull-only).
- This `CHANGELOG.md`.

### Changed
- Production `docker-compose.yml` now pulls immutable images from GHCR
  (`ghcr.io/jonasprade/raildashboard-<svc>:${IMAGE_TAG}`) instead of building from a GitHub
  URL context on the server — build and run are now separate worlds.
- Renamed the release pin `APP_VERSION` → `IMAGE_TAG` in `.env.prod.example` and the compose
  file.
- `apps/backend/requirements.txt` is now pinned to exact `==` versions for reproducible builds.
- Backend runtime image upgraded to `python:3.13-slim` to match the tested interpreter.

### Fixed
- Frontend eslint errors so `eslint` can be a blocking CI gate: hoisted access-guard early
  returns below all hooks in `HaushaltsImportPage` and `VibImportPage` (react-hooks/rules-of-hooks),
  dropped an unused `_files` parameter in `ProjectTextsSection`, and replaced a ternary-as-statement
  with `if/else` in `VibStructurePreviewPage`.
- Backend test suite is now hermetic: `tests/conftest.py` provides a dummy `SESSION_SECRET_KEY`
  so `pytest` no longer depends on a developer's local `.env` (the required Settings field made
  the CI quality gate fail on a clean checkout).
