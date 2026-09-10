"""Dump a HaushaltsParseResult for debugging.

Usage:
    # List all parse results
    python scripts/dump_parse_result.py

    # Summary of one run — how the PDF was read, per table (start here)
    python scripts/dump_parse_result.py <id> --summary

    # Dump the full result_json for a specific ID
    python scripts/dump_parse_result.py <id>

    # Write to file
    python scripts/dump_parse_result.py <id> > /tmp/parse_result.json
"""
import json
import sys

from dashboard_backend.database import Session
from dashboard_backend.models.haushalt.haushalts_parse_result import HaushaltsParseResult



def print_summary(result: dict, record=None) -> None:
    """How the PDF was read — the numbers a review of an import turns on.

    Kept separate from the DB lookup so the same summary can be produced from a
    result_json dumped elsewhere.
    """
    if record is not None:
        confirmed = record.confirmed_at.strftime("%Y-%m-%d %H:%M") if record.confirmed_at else "nein"
        print(f"Lauf {record.id}: {record.pdf_filename}")
        print(f"  Haushaltsjahr:   {record.haushalt_year}")
        print(f"  Status:          {record.status}   importiert: {confirmed}")
        print(f"  Textquelle:      {record.ocr_model or '?'} ({record.ocr_status or '?'})")
        print(f"  Spaltenzuordnung:{record.column_map_source or '?'}")
        if record.error_message:
            print(f"  Fehler:          {record.error_message}")
        print()

    rows = result.get("rows", [])
    sections = result.get("sections", [])
    column_map = result.get("column_map") or {}

    print(f"Werte aus:  {result.get('extraction_source', '?')}")
    if column_map:
        missing = column_map.get("missing") or []
        print(f"Spalten:    {column_map.get('source')} — {len(column_map.get('columns', [])) - len(missing)}"
              f" von {len(column_map.get('columns', []))} zugeordnet"
              + (f", fehlend: {', '.join(missing)}" if missing else ""))

    print(f"\nTabellen ({len(sections)}):")
    for section in sections:
        print(
            f"  Tabelle {section.get('number') or '?':<2} {str(section.get('title'))[:44]:<44}"
            f" S.{section.get('page_from')}–{section.get('page_to'):<4}"
            f" {section.get('row_count', 0):>4} Zeilen  map={section.get('column_map_source')}"
        )

    by_status: dict[str, int] = {}
    by_table: dict[object, int] = {}
    for row in rows:
        by_status[row.get("status")] = by_status.get(row.get("status"), 0) + 1
        by_table[row.get("table_number")] = by_table.get(row.get("table_number"), 0) + 1
    keyed = [row for row in rows if row.get("finve_key")]

    print(f"\nZeilen:     {len(rows)} gesamt, {len(result.get('unmatched_rows', []))} unmatched")
    print(f"  nach Status:  {by_status}")
    print(f"  nach Tabelle: {dict(sorted(by_table.items(), key=lambda kv: (kv[0] is None, kv[0])))}")
    print(f"  mit finve_key (ohne gedruckte FinVe-Nummer): {len(keyed)}")
    if keyed:
        print("  Beispiele:   " + ", ".join(row["finve_key"] for row in keyed[:4]))

    comparison = result.get("extraction_comparison")
    if comparison:
        print("\nTexterkennung im Vergleich:")
        print(f"  OCR:        {comparison.get('ocr_model')} ({comparison.get('ocr_status')})")
        if comparison.get("error"):
            print(f"  Fehler:     {comparison['error']}")
        print(f"  Zeilen:     pdfplumber {comparison.get('rows_pdfplumber')}"
              f" / OCR {comparison.get('rows_ocr')} / gemeinsam {comparison.get('rows_matched')}")
        print(f"  Abweichende Werte: {comparison.get('value_differences_total')}"
              f"   identisch: {comparison.get('identical')}")
        for difference in (comparison.get("value_differences") or [])[:10]:
            print(f"    {difference['row_key']:<38} {difference['field']:<26}"
                  f" pdfplumber={difference['pdfplumber']!r} ocr={difference['ocr']!r}")
    else:
        print("\nTexterkennung im Vergleich: nicht gelaufen (HAUSHALT_EXTRACTION=pdfplumber)")


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

        if "--summary" in sys.argv:
            print_summary(record.result_json or {}, record)
        else:
            print(json.dumps(record.result_json, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
