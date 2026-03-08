"""Dump a HaushaltsParseResult to JSON for debugging.

Usage:
    # List all parse results
    python scripts/dump_parse_result.py

    # Dump result_json for a specific ID
    python scripts/dump_parse_result.py <id>

    # Write to file
    python scripts/dump_parse_result.py <id> > /tmp/parse_result.json
"""
import json
import sys

from dashboard_backend.database import Session
from dashboard_backend.models.haushalt.haushalts_parse_result import HaushaltsParseResult


def main():
    db = Session()
    try:
        if len(sys.argv) < 2:
            # List all parse results without the big JSON
            rows = (
                db.query(HaushaltsParseResult)
                .order_by(HaushaltsParseResult.id.desc())
                .all()
            )
            if not rows:
                print("Keine Parse-Ergebnisse vorhanden.")
                return
            print(f"{'ID':>4}  {'Jahr':>6}  {'Status':<10}  {'Importiert':<12}  Dateiname")
            print("-" * 70)
            for r in rows:
                imported = r.confirmed_at.strftime("%Y-%m-%d") if r.confirmed_at else "–"
                print(f"{r.id:>4}  {r.haushalt_year:>6}  {r.status:<10}  {imported:<12}  {r.pdf_filename}")
            return

        record_id = int(sys.argv[1])
        record = db.query(HaushaltsParseResult).filter(HaushaltsParseResult.id == record_id).first()
        if not record:
            print(f"Kein Ergebnis mit ID {record_id} gefunden.", file=sys.stderr)
            sys.exit(1)

        print(json.dumps(record.result_json, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
