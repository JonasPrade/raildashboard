"""Import stops of S-Bahn/Stadtbahn, U-Bahn and tram networks from OSM.

Fetches the stops for Germany from the Overpass API and writes them into
``operational_point`` (``source = "osm"``, ``network`` = light_rail | subway | tram),
so that the waypoint search of the routing finds them. Rules (which OSM objects,
merging, skipping S-Bahn stations already in RINF): dashboard_backend/services/osm_stops.py
and docs/features/feature-routing.md → "Gleisarten (S-Bahn, U-Bahn, Straßenbahn,
Schmalspur)".

Usage:
    make import-osm-stops                      # local
    make docker-import-osm-stops               # inside the running backend container
    python scripts/import_osm_stops.py --dry-run
    python scripts/import_osm_stops.py --from-file overpass.json

Rerunning is safe: stops are matched on ``op_id`` (``OSM-<n|w|r><id>``) and updated.
Stops that disappeared from OSM are kept — projects may point at them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

import requests

from dashboard_backend.database import Session
from dashboard_backend.models.railway_infrastructure.operational_point import OperationalPoint
from dashboard_backend.services.osm_stops import (
    OVERPASS_QUERY,
    KnownPoint,
    OsmStop,
    stops_from_overpass,
)

DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "raildashboard-osm-stops-import"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import OSM stops of S-Bahn, U-Bahn and tram")
    parser.add_argument(
        "--overpass-url",
        default=os.environ.get("OVERPASS_URL", DEFAULT_OVERPASS_URL),
        help="Overpass API endpoint (default: %(default)s, env OVERPASS_URL)",
    )
    parser.add_argument(
        "--from-file", help="Read an Overpass JSON answer from this file instead of fetching"
    )
    parser.add_argument("--dry-run", action="store_true", help="Report only, write nothing")
    return parser.parse_args()


def fetch_elements(url: str) -> list[dict]:
    response = requests.post(
        url,
        data={"data": OVERPASS_QUERY},
        headers={"User-Agent": USER_AGENT},
        timeout=1000,
    )
    response.raise_for_status()
    return response.json().get("elements", [])


def upsert(db, stops: list[OsmStop]) -> Counter:
    counts: Counter = Counter()
    existing = {
        op.op_id: op
        for op in db.query(OperationalPoint).filter(OperationalPoint.source == "osm").all()
    }
    for stop in stops:
        op = existing.get(stop.op_id)
        if op is None:
            op = OperationalPoint(op_id=stop.op_id, source="osm", country_code="DE")
            db.add(op)
            counts["created"] += 1
        elif (op.name, op.network, op.type, op.latitude, op.longitude) != (
            stop.name,
            stop.network,
            stop.type,
            stop.latitude,
            stop.longitude,
        ):
            counts["updated"] += 1
        else:
            counts["unchanged"] += 1
        op.name = stop.name
        op.network = stop.network
        op.type = stop.type
        op.latitude = stop.latitude
        op.longitude = stop.longitude
    return counts


def main() -> int:
    args = parse_args()
    if args.from_file:
        with open(args.from_file, encoding="utf-8") as handle:
            elements = json.load(handle).get("elements", [])
    else:
        print(f"Fetching stops from {args.overpass_url} (this takes a few minutes) ...")
        elements = fetch_elements(args.overpass_url)
    print(f"{len(elements)} OSM elements")

    db = Session()
    try:
        known = [
            KnownPoint(op.name or "", op.latitude, op.longitude)
            for op in db.query(OperationalPoint)
            .filter(OperationalPoint.source == "rinf")
            .filter(OperationalPoint.latitude.isnot(None), OperationalPoint.longitude.isnot(None))
            .all()
        ]
        stops = stops_from_overpass(elements, known)
        per_network = Counter(stop.network for stop in stops)
        print("Stops after merging: " + ", ".join(f"{k} {v}" for k, v in sorted(per_network.items())))
        if args.dry_run:
            print("Dry run — nothing written.")
            return 0
        counts = upsert(db, stops)
        db.commit()
        print(
            f"created {counts['created']}, updated {counts['updated']}, "
            f"unchanged {counts['unchanged']}"
        )
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
