"""Dump a completed VIB parse task result from the Celery/Redis result backend.

Usage:
    # List all confirmed VIB reports in the database
    python3.11 scripts/dump_vib_parse_result.py

    # Dump the parse result for a specific Celery task_id
    python3.11 scripts/dump_vib_parse_result.py <task_id>

    # Write to file
    python3.11 scripts/dump_vib_parse_result.py <task_id> > /tmp/vib_result.json

    # Diagnose raw PDF text extraction (shows TOC vs content structure)
    python3.11 scripts/dump_vib_parse_result.py --raw /path/to/vib.pdf
    python3.11 scripts/dump_vib_parse_result.py --raw /path/to/vib.pdf > /tmp/vib_raw.txt

Run from apps/backend/:
    cd apps/backend && python3.11 scripts/dump_vib_parse_result.py
"""
import io
import json
import re
import sys


def _dump_raw(pdf_path: str) -> None:
    """Extract raw text from a VIB PDF and print diagnostics about key patterns."""
    import pdfplumber

    _SECTION_START_RE = re.compile(r"^\s*B\s+Schienenwege", re.IGNORECASE | re.MULTILINE)
    _SECTION_END_RE = re.compile(r"^\s*C\s+Bundesfernstra", re.IGNORECASE | re.MULTILINE)
    _VORHABEN_HEADING_RE = re.compile(r"^(B\.\d+\.\d+(?:\.\d+)?)\s{1,8}(.+)$", re.MULTILINE)

    print(f"Reading PDF: {pdf_path}", file=sys.stderr)
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    all_pages_text: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        total_pages = len(pdf.pages)
        print(f"Total pages: {total_pages}", file=sys.stderr)
        for page in pdf.pages:
            all_pages_text.append(page.extract_text() or "")

    full_text = "\n".join(all_pages_text)

    # Show all occurrences of "B Schienenwege" with context
    print("\n" + "=" * 80)
    print("ALL OCCURRENCES OF 'B Schienenwege' (with 3 lines context each):")
    print("=" * 80)
    for m in _SECTION_START_RE.finditer(full_text):
        char_pos = m.start()
        snippet_start = max(0, char_pos - 100)
        snippet_end = min(len(full_text), char_pos + 300)
        print(f"\n--- at char {char_pos} ---")
        print(repr(full_text[snippet_start:snippet_end]))

    # Show all occurrences of "C Bundesfernstraßen" with context
    print("\n" + "=" * 80)
    print("ALL OCCURRENCES OF 'C Bundesfernstra' (with 3 lines context each):")
    print("=" * 80)
    for m in _SECTION_END_RE.finditer(full_text):
        char_pos = m.start()
        snippet_start = max(0, char_pos - 100)
        snippet_end = min(len(full_text), char_pos + 300)
        print(f"\n--- at char {char_pos} ---")
        print(repr(full_text[snippet_start:snippet_end]))

    # Show the sliced rail section
    start_match = _SECTION_START_RE.search(full_text)
    end_match = _SECTION_END_RE.search(full_text)
    if start_match:
        rail_start = start_match.start()
        rail_end = end_match.start() if end_match else len(full_text)
        rail_text = full_text[rail_start:rail_end]
        print(f"\n{'=' * 80}")
        print(f"SLICED RAIL SECTION: chars {rail_start}–{rail_end} ({rail_end - rail_start} chars)")
        print("=" * 80)
        print("FIRST 2000 chars of rail section:")
        print(rail_text[:2000])

        heading_matches = list(_VORHABEN_HEADING_RE.finditer(rail_text))
        print(f"\n{'=' * 80}")
        print(f"VORHABEN HEADINGS FOUND IN RAIL SECTION: {len(heading_matches)}")
        print("=" * 80)
        for i, hm in enumerate(heading_matches[:30]):
            # Show how many chars of content follow this heading before the next
            block_start = hm.start()
            block_end = heading_matches[i + 1].start() if i + 1 < len(heading_matches) else len(rail_text)
            block_len = block_end - block_start
            print(f"  {hm.group(1):>12}  {hm.group(2)[:60]:<60}  block_len={block_len}")
    else:
        print("\nWARNING: 'B Schienenwege' section start NOT FOUND in document!")

    # Write full text to stdout for further inspection
    print("\n" + "=" * 80)
    print("FULL EXTRACTED TEXT (stdout):")
    print("=" * 80)
    sys.stdout.write(full_text)


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--raw":
        if len(sys.argv) < 3:
            print("Usage: python3.11 scripts/dump_vib_parse_result.py --raw /path/to/vib.pdf", file=sys.stderr)
            sys.exit(1)
        _dump_raw(sys.argv[2])
        return

    from dashboard_backend.celery_app import celery_app
    from dashboard_backend.database import Session
    from dashboard_backend.models.vib.vib_report import VibReport

    if len(sys.argv) < 2:
        # List all confirmed VIB reports from the database
        db = Session()
        try:
            reports = (
                db.query(VibReport)
                .order_by(VibReport.year.desc())
                .all()
            )
            if not reports:
                print("Keine VIB-Berichte in der Datenbank vorhanden.")
                return
            print(f"{'ID':>4}  {'Jahr':>6}  {'Drucksache':<20}  {'Datum':<12}  {'Einträge':>8}")
            print("-" * 60)
            for r in reports:
                datum = r.report_date.isoformat() if r.report_date else "–"
                n_entries = len(r.entries)
                print(
                    f"{r.id:>4}  {r.year:>6}  {r.drucksache_nr or '–':<20}  "
                    f"{datum:<12}  {n_entries:>8}"
                )
        finally:
            db.close()
        return

    task_id = sys.argv[1]
    async_result = celery_app.AsyncResult(task_id)

    print(f"Task ID   : {task_id}", file=sys.stderr)
    print(f"State     : {async_result.state}", file=sys.stderr)

    if async_result.state == "PENDING":
        print("Task is still pending or does not exist.", file=sys.stderr)
        sys.exit(1)

    if async_result.state == "FAILURE":
        print(f"Task failed: {async_result.result}", file=sys.stderr)
        sys.exit(1)

    if async_result.state != "SUCCESS":
        print(f"Unexpected state: {async_result.state}", file=sys.stderr)
        sys.exit(1)

    result = async_result.result
    if not isinstance(result, dict):
        print(f"Unexpected result type: {type(result)}", file=sys.stderr)
        sys.exit(1)

    entries = result.get("entries", [])
    print(f"Jahr      : {result.get('year')}", file=sys.stderr)
    print(f"Einträge  : {len(entries)}", file=sys.stderr)
    print(f"Drucksache: {result.get('drucksache_nr', '–')}", file=sys.stderr)
    print("-" * 80, file=sys.stderr)
    for i, e in enumerate(entries):
        proj_id = e.get("project_id")
        suggestions = e.get("suggested_project_ids", [])
        print(
            f"  [{i + 1:>3}] {e.get('vib_section', '?'):>10}  "
            f"{e.get('vib_name_raw', '')[:55]:<55}  "
            f"project_id={proj_id}  suggestions={suggestions}",
            file=sys.stderr,
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
