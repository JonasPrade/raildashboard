"""Restore the full stops of Infraplan drafts read as "�" (U+FFFD).

Drafts parsed before the fix (and the years confirmed from them) are repaired
in place from the stored row texts — assignments and KPI values stay, nothing
is uploaded or parsed again. Without ``--apply`` the changes are only shown.

Usage:
    python -m scripts.repair_infraplan_full_stops           # dry run
    python -m scripts.repair_infraplan_full_stops --apply
"""

from __future__ import annotations

import argparse

from dashboard_backend.crud.infraplan_import import repair_full_stops
from dashboard_backend.database import Session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair Infraplan full stops read as U+FFFD")
    parser.add_argument("--apply", action="store_true", help="Write the changes (default: dry run)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with Session() as db:
        summaries = repair_full_stops(db, apply=args.apply)
        if not summaries:
            print("Nothing to repair.")
            return 0
        for s in summaries:
            print(
                f"Draft {s['parse_result_id']} (Infraplan {s['year']}): "
                f"{s['rows_changed']} rows, {s['entries_changed']} entries, "
                f"{s['projects_updated']} projects re-materialised"
            )
            for message in s["warnings"]:
                print(f"  warning: {message}")
        print("Applied." if args.apply else "Dry run — nothing written. Run again with --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
