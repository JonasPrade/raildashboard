"""Import the Bundestag constituency outlines from a GeoJSON file.

The outlines change once per election, so this is a script and not a button:
downloading the file is a manual step anyway.

Source: Die Bundeswahlleiterin, © GeoBasis-DE / BKG. If the original is
unreachable there is an open mirror:
https://github.com/ZeitOnline/bundestagswahl-historische-wahlkreis-daten
(``shapes_2025/wkr2025.geojson``).

Usage:
    python scripts/import_constituencies.py wkr2025.geojson \
        --period 161 --election-year 2025

Needs PostGIS — the geometry is handed to ``ST_GeomFromGeoJSON``. Rerunning is
safe: constituencies are matched on ``(parliament_period, number)``.
"""

from __future__ import annotations

import argparse
import json
import sys

from dashboard_backend.database import Session
from dashboard_backend.services.constituency_matching import recompute_all_links
from dashboard_backend.services.parliament_import import import_constituency_geometries

DEFAULT_SOURCE = "Die Bundeswahlleiterin, © GeoBasis-DE / BKG"
# abgeordnetenwatch parliament-period id of "Bundestag 2025 - 2029".
DEFAULT_PERIOD = 161


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import constituency outlines")
    parser.add_argument("geojson", help="Path to the constituency GeoJSON file")
    parser.add_argument(
        "--period",
        type=int,
        default=DEFAULT_PERIOD,
        help="abgeordnetenwatch parliament_period id (default: %(default)s)",
    )
    parser.add_argument("--election-year", type=int, default=2025)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument(
        "--skip-recompute",
        action="store_true",
        help="Do not rebuild project_to_constituency afterwards",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with open(args.geojson, encoding="utf-8") as handle:
        payload = json.load(handle)
    features = payload.get("features") if isinstance(payload, dict) else None
    if not features:
        print("No features found in the GeoJSON file.", file=sys.stderr)
        return 1

    db = Session()
    try:
        run = import_constituency_geometries(
            db,
            features,
            period_external_id=args.period,
            election_year=args.election_year,
            source=args.source,
        )
        print(f"Constituencies imported: {run.stats}")
        if not args.skip_recompute:
            # New outlines invalidate every existing link.
            stats = recompute_all_links(db)
            print(f"Project links rebuilt: {stats.as_dict()}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
