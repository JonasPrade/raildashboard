## Git workflow

- **Branches:** `feature/<summary>`, `fix/<bug-id>`, `docs/<topic>`, `refactor/<area>`.
- **Strategy:** `master` stays stable and deployable. Branch directly from `master`.
- **Merges:** Squash-merge feature branches. Rebase your branch onto the latest `master` before submitting a PR.
- **Commit messages:** Follow Conventional Commits:
  - `feat(map): add project route hover effect`
  - `fix(api): correct bounding-box serialisation`
  - `docs: update OSM import instructions`
  - `chore: add Makefile`