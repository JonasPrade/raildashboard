"""Identity for measures the budget report lists without a FinVe number.

Only the Bedarfsplan table (Tabelle 1) prints a FinVe number per row; it is the
primary key of ``finve``.  The other tables of Annex VWIB Part B identify their
entries differently:

===========  ====================================  ==========================
Tabelle      first column                          identity used here
===========  ====================================  ==========================
2 Lärm       ``YYY SV 52/2017`` / bare ``YYY``      ``t2:SV 52/2017``
3 ERTMS      ``YYY F08Q0770``                      ``t3:F08Q0770``
4 KMM        ``YYY F 03 E 0793``                   ``t4:F 03 E 0793``
5 InvKG      ``B0094 5/ Nr.1 F 21/S 0555``         ``t5:B0094``
===========  ====================================  ==========================

Tabelle 5 keys on the running number because it shares one continuous ``B####``
space with Tabelle 1 (verified on the 2027 report: no overlap between the two),
which makes it the most stable identifier the row carries.  Where a row prints
no identifier at all, the measure name plus its starting year stands in.

The key is what ties a measure to the same ``finve`` row in the next report
year, so it is deliberately built from what the report itself prints — never
from the row's position in the document.
"""

from __future__ import annotations

import re
import unicodedata

# Maximum length of Finve.finve_key
_MAX_KEY_LENGTH = 120

# "B0094 5/ Nr.1 F 21/S 0555" → running number of the InvKG table
_LFD_NR_RE = re.compile(r"^\s*(B\d+)\b")

# "YYY SV 52/2017" / "YYY F 03 E 0793" / "YYY" → the identifier after the marker
_YYY_PREFIX_RE = re.compile(r"^\s*YYY\b[ \t]*", re.IGNORECASE)
_YYY_MARKER_RE = re.compile(r"^\s*YYY\b", re.IGNORECASE)


_TRANSLITERATION = {
    "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
    "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
}


def _slug(value: str) -> str:
    """ASCII slug of a measure name — the stand-in for a missing identifier."""
    text = value or ""
    for source, target in _TRANSLITERATION.items():
        text = text.replace(source, target)
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_only).strip("-").lower()
    return slug[:60]


def has_measure_marker(id_cell: str | None) -> bool:
    """True when the first column marks the start of a measure.

    The report opens every measure with ``YYY`` (the tables without FinVe
    numbers) or with its running number ``B####``.  Section headings and stray
    text that pdfplumber drops into the first column carry neither, so this is
    what tells a measure from a continuation row.
    """
    if not id_cell:
        return False
    cell = re.sub(r"\s+", " ", str(id_cell)).strip()
    return bool(_LFD_NR_RE.match(cell) or _YYY_MARKER_RE.match(cell))


def measure_identifier(id_cell: str | None, finve_cell: str | None = None) -> str | None:
    """The identifier a non-Bedarfsplan row prints for its measure.

    The running number wins where the report prints one (Tabelle 5).  Otherwise
    the designation follows the ``YYY`` marker — in the first column on most
    pages, in the FinVe column on the pages whose rows had to be rebuilt, where
    the finer column grid separates ``YYY`` from ``F08Q0770``.

    Returns None when the row marks a measure but names no identifier at all,
    so the caller falls back to the measure name.
    """
    if not has_measure_marker(id_cell):
        return None
    cell = re.sub(r"\s+", " ", str(id_cell)).strip()

    lfd = _LFD_NR_RE.match(cell)
    if lfd:
        return lfd.group(1)

    remainder = _YYY_PREFIX_RE.sub("", cell).strip()
    if remainder:
        return remainder

    from_finve_column = re.sub(r"\s+", " ", str(finve_cell or "")).strip()
    return from_finve_column or None


def build_finve_key(
    table_number: int | None,
    id_cell: str | None,
    finve_cell: str | None,
    name: str,
    starting_year: int | None,
    taken: set[str],
) -> str:
    """A stable, document-scoped key for one measure without a FinVe number.

    ``taken`` collects the keys already handed out for this document; a measure
    whose identifier repeats (the 2027 report lists ``F 03 E 0793`` twice, once
    for the original agreement and once for its amendment) gets ``#2``, ``#3``
    appended in the order the report prints them.
    """
    prefix = f"t{table_number}" if table_number is not None else "t"
    identifier = measure_identifier(id_cell, finve_cell)
    if identifier is None:
        identifier = _slug(name) or "unbenannt"
        if starting_year:
            identifier = f"{identifier}-{starting_year}"

    base = f"{prefix}:{identifier}"[:_MAX_KEY_LENGTH]
    key = base
    suffix = 1
    while key in taken:
        suffix += 1
        marker = f"#{suffix}"
        key = base[: _MAX_KEY_LENGTH - len(marker)] + marker
    taken.add(key)
    return key
