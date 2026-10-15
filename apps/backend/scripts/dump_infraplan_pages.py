"""Write the test fixture of the Infraplan parser (stage 1 output as JSON).

Usage (from apps/backend):
    PYTHONPATH=. .venv/bin/python scripts/dump_infraplan_pages.py \\
        ../../docs/261002_Infraplan_2026_1.pdf \\
        tests/fixtures/infraplan_2026_pages.json [--pages 33-56]

    # KPI chart detection (chapter 3 and appendix I, plus an appendix list page):
    PYTHONPATH=. .venv/bin/python scripts/dump_infraplan_pages.py \\
        ../../docs/261002_Infraplan_2026_1.pdf \\
        tests/fixtures/infraplan_2026_kpi_pages.json --pages 57,60-62,66-68,85,93-94,102

The fixture holds, per page, the words with position and font size plus the
header tables (bbox and column edges) — exactly what stage 2 reads, so the
parser tests run without the PDF (which lies outside the Docker build
context of apps/backend). Pattern: tests/fixtures/haushalt_ep12_2027_pages.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dashboard_backend.tasks.infraplan import extract_pages


def _page_range(spec: str) -> list[int]:
    """``33-56`` or ``57,60-62,93`` → 1-indexed page numbers."""
    pages: list[int] = []
    for part in spec.split(","):
        first, _, last = part.strip().partition("-")
        pages.extend(range(int(first), int(last or first) + 1))
    return pages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pdf", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--pages", default="33-56", help="1-indexed pages, e.g. 33-56 or 57,60-62 (default 33-56)")
    args = parser.parse_args()

    pages = extract_pages(args.pdf.read_bytes(), _page_range(args.pages))
    payload = {
        "source": args.pdf.name,
        "pages": [page.to_dict() for page in pages],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    words = sum(len(p.words) for p in pages)
    print(f"{len(pages)} pages, {words} words → {args.out}")


if __name__ == "__main__":
    main()
