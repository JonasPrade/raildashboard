"""Run both Haushalt extraction paths on one PDF and report the differences.

This is the golden comparison the staged plan in
`docs/features/feature-pdf-import-unification.md` asks for before the OCR stage
may supply the values: the same PDF through pdfplumber and through Mistral OCR,
row for row and number for number.  It touches no database and imports nothing.

Usage (from apps/backend, with OCR_API_KEY set):

    .venv/bin/python scripts/compare_haushalt_extraction.py EP12_Teil_B.pdf 2027
    .venv/bin/python scripts/compare_haushalt_extraction.py report.pdf 2027 --json > diff.json

Exit code 0 means the two paths agree — the condition for switching
`HAUSHALT_EXTRACTION` to `ocr`.  Exit code 1 means they do not, and the report
names every row and field that differs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard_backend.core.config import settings  # noqa: E402
from dashboard_backend.services.document_ocr import extract_document_text  # noqa: E402
from dashboard_backend.tasks.haushalt import (  # noqa: E402
    _compare_extractions,
    _extract_pages,
    _extract_pages_from_ocr,
    _parse_extracted_pages,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", help="Path to the Anlage VWIB, Teil B PDF")
    parser.add_argument("year", type=int, help="Haushaltsjahr of the report")
    parser.add_argument("--json", action="store_true", help="Print the raw comparison as JSON")
    parser.add_argument(
        "--max-differences",
        type=int,
        default=40,
        help="How many differing values to print (default: 40)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    if not settings.ocr_api_key:
        print(
            "OCR_API_KEY is not set — the OCR path would silently degrade to pymupdf,\n"
            "which recognises no table structure and would make the comparison meaningless.",
            file=sys.stderr,
        )
        return 2

    with open(args.pdf, "rb") as handle:
        pdf_bytes = handle.read()

    print(f"Reading {args.pdf} with pdfplumber …", file=sys.stderr)
    from_pdfplumber = _parse_extracted_pages(
        _extract_pages(pdf_bytes), args.year, known_finve_ids=set()
    )

    print(f"Reading {args.pdf} with {settings.ocr_model} …", file=sys.stderr)
    ocr = extract_document_text(pdf_bytes, table_format="html")
    if ocr.status != "done":
        print(
            f"\nOCR did not run ({ocr.status}, {ocr.model}). The service degraded to a text\n"
            "extractor that recognises no table structure, so any diff below would only\n"
            "measure that degradation. Fix the OCR credentials and run again.",
            file=sys.stderr,
        )
        return 2

    from_ocr = _parse_extracted_pages(
        _extract_pages_from_ocr(ocr), args.year, known_finve_ids=set()
    )

    comparison = _compare_extractions(from_pdfplumber, from_ocr, ocr)

    if args.json:
        print(json.dumps(comparison.model_dump(), ensure_ascii=False, indent=1))
        return 0 if comparison.identical else 1

    print()
    print(f"OCR:            {comparison.ocr_model} ({comparison.ocr_status})")
    print(f"Rows pdfplumber: {comparison.rows_pdfplumber}")
    print(f"Rows OCR:        {comparison.rows_ocr}")
    print(f"Rows in both:    {comparison.rows_matched}")

    if comparison.rows_only_pdfplumber:
        print(f"\nOnly pdfplumber found ({len(comparison.rows_only_pdfplumber)}):")
        for row_key in comparison.rows_only_pdfplumber:
            print(f"  - {row_key}")
    if comparison.rows_only_ocr:
        print(f"\nOnly OCR found ({len(comparison.rows_only_ocr)}):")
        for row_key in comparison.rows_only_ocr:
            print(f"  + {row_key}")

    if comparison.value_differences_total:
        print(f"\nValue differences: {comparison.value_differences_total}")
        for difference in comparison.value_differences[: args.max_differences]:
            print(
                f"  {difference.row_key:<40} {difference.field:<28}"
                f" pdfplumber={difference.pdfplumber!r}  ocr={difference.ocr!r}"
            )
        shown = min(args.max_differences, len(comparison.value_differences))
        if comparison.value_differences_total > shown:
            print(f"  … and {comparison.value_differences_total - shown} more")

    print()
    if comparison.identical:
        print("Identical — the OCR path reproduces every row and every value.")
        return 0
    print("Different — do not switch HAUSHALT_EXTRACTION to 'ocr' yet.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
