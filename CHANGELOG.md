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
- Tag-based CI/CD pipeline (`.github/workflows/deploy.yml`): pushing a `v*` tag runs the
  quality gates (backend `pytest`, frontend `tsc`), builds the `backend`, `frontend`, and
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
