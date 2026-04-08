#!/usr/bin/env python3.11
"""Dump a VIB PDF parse result to stdout without Celery or DB.

Usage:
    python3.11 scripts/dump_vib_parse_result.py path/to/vib.pdf [year]

Output: structured summary of each detected Vorhaben block.
"""
import sys
import os

# Allow running from apps/backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Minimal env so config doesn't fail
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("RINF_API_URL", "https://example.invalid")
os.environ.setdefault("RINF_USERNAME", "x")
os.environ.setdefault("RINF_PASSWORD", "x")

from dashboard_backend.tasks.vib import _parse_vib_pdf  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3.11 scripts/dump_vib_parse_result.py <path_to_vib.pdf> [year]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    year = int(sys.argv[2]) if len(sys.argv) > 2 else 2023

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    parse_result, _full_text, ocr_model, ocr_status, _images = _parse_vib_pdf(pdf_bytes, year)

    print(f"Year: {parse_result.year}")
    print(f"Drucksache: {parse_result.drucksache_nr}")
    print(f"Report date: {parse_result.report_date}")
    print(f"OCR: {ocr_status} / {ocr_model}")
    print(f"Entries found: {len(parse_result.entries)}")
    print("=" * 70)

    # Optional filter: show only a specific section (e.g. "B.4.1.1")
    section_filter = sys.argv[3] if len(sys.argv) > 3 else None

    for e in parse_result.entries:
        if section_filter and e.vib_section != section_filter:
            continue
        print(f"\n[{e.vib_section}] {e.vib_name_raw[:80]}")
        print(f"  category:       {e.category}")
        flags = " ".join(f for f, v in [("Planung", e.status_planung), ("Bau", e.status_bau), ("Abgeschlossen", e.status_abgeschlossen)] if v) or "–"
        print(f"  status_flags:   {flags}")
        print(f"  strecklaenge:   {e.strecklaenge_km} km")
        print(f"  gesamtkosten:   {e.gesamtkosten_mio_eur} Mio €")
        print(f"  PFA entries:    {len(e.pfa_entries)}")

        fields = [
            ("bauaktivitaeten", e.bauaktivitaeten),
            ("planungsstand", e.planungsstand),
            ("verkehrliche_zielsetzung", e.verkehrliche_zielsetzung),
            ("sonstiges", e.sonstiges),
        ]
        for label, val in fields:
            preview = (val or "–")[:120].replace("\n", " ")
            print(f"  {label}: {preview}")

        if e.pfa_entries:
            print("  PFA rows:")
            for pfa in e.pfa_entries:
                abschnitt = f" [{pfa.abschnitt_label}]" if pfa.abschnitt_label else ""
                print(f"    {pfa.nr_pfa}{abschnitt} | {pfa.oertlichkeit} | {pfa.entwurfsplanung} | IBN: {pfa.inbetriebnahme}")


if __name__ == "__main__":
    main()
