"""Debug helper for the Fulda-Runde importer (#46).

Usage (from apps/backend):
    .venv/bin/python scripts/dump_fulda_parse.py /path/to/kleine_anfrage.pdf

Prints the OCR status + a text sample, the raw LLM response, and the normalised
items — so we can see why extraction yields 0 entries for a given document.
"""

from __future__ import annotations

import json
import sys

from dashboard_backend.core.config import settings
from dashboard_backend.tasks.fulda_extraction import (
    _MAX_TEXT_CHARS,
    _USER_PROMPT_TEMPLATE,
    _call_llm,
    normalize_items,
    ocr_fulda_pdf,
)


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: dump_fulda_parse.py <pdf-path>")
        raise SystemExit(2)

    with open(sys.argv[1], "rb") as fh:
        pdf_bytes = fh.read()

    text, model, status = ocr_fulda_pdf(pdf_bytes)
    print(f"OCR: status={status} model={model} chars={len(text)}")
    print("=" * 70)
    print("OCR TEXT SAMPLE (first 4000 chars):")
    print(text[:4000])
    print("=" * 70)

    if not settings.llm_base_url:
        print("No LLM configured (llm_base_url empty) — extraction would be empty.")
        return

    prompt = _USER_PROMPT_TEMPLATE.format(text=text[:_MAX_TEXT_CHARS])
    raw = _call_llm(prompt)
    print("RAW LLM RESPONSE:")
    print(json.dumps(raw, ensure_ascii=False, indent=2)[:6000])
    print("=" * 70)
    print("NORMALISED ITEMS:", normalize_items(raw.get("items")))


if __name__ == "__main__":
    main()
