# Contributor Guidance for Schienendashboard Backend

These guidelines apply to the entire repository and are intended for all future changes.

## Code & Architecture
- Prefer type hints in new or modified Python functions.
- Maintain the separation of concerns between `api`, `schemas`, `crud`, and `models`. New endpoints require matching schema and CRUD updates.
- Create a dedicated Alembic migration for every database model change.
- When introducing a new group of related database tables, place the models inside a new subdirectory (e.g. `osmr`, `eba_data`, `project_data`) so that domain boundaries stay clear.

## Documentation
- Update the README and relevant files under `docs/` whenever setup steps, import flows, or domain models change.
- Provide examples and background information in English going forward.

## Tests & Quality Assurance
- Run `pytest` whenever Python code changes. Pure documentation or text-only changes are exempt.
- Summarize in the PR or commit message which tests were executed and highlight any manual steps.
- Extend or adjust the tests in `tests/api/` immediately whenever you add or modify API routes.

## Data Imports
- Add new import scripts under `scripts/` and expose a CLI via `argparse`.
- Document new import paths in `docs/` and include a short example in the README.

## DB Connection
- there is a DB which is Postgres with Postgis extension enabled.
- Use SQLAlchemy ORM for all DB interactions.
- Use only Postgres and no SQLite for develompenet

Thank you for contributing to the project!
