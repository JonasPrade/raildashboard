"""Recompute the planning state (Planungsstand) of every project.

Resyncs the derived observations (VIB, FinVe, Infraplan, GVFG, …), the cached
headline phase and the cached Baubeginn / Inbetriebnahme of all projects
(docs/features/feature-project-progress.md → „Alles neu berechnen“). Run it
once after a deploy that changes the derivation rules; the same job is the
button „Alle Projekte neu berechnen“ on the admin page „Planungsstand ·
Konflikte“. Idempotent.

Usage:
    python scripts/recompute_progress.py
"""

from __future__ import annotations

from dashboard_backend.crud.projects.progress import recompute_all_progress
from dashboard_backend.database import Session


def main() -> int:
    with Session() as db:
        stats = recompute_all_progress(
            db, on_batch=lambda done, total: print(f"{done}/{total}", flush=True)
        )
    print(
        f"{stats['projects']} Projekte neu berechnet: Planungsstand bekannt "
        f"{stats['known_before']} → {stats['known_after']}, "
        f"{stats['phase_changed']} Phasen geändert."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
