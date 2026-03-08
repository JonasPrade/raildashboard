"""Fuzzy name-matching between FinVe names and Project names.

Used during the Haushalt PDF parse task to suggest project assignments for new
FinVes so editors can confirm or correct them in the review UI.
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

_STRIP_PREFIXES = re.compile(
    r"^(abs/nbs|nbs/abs|abs|nbs|neu-|aus-|um-)\s*",
    re.IGNORECASE,
)
_PUNCTUATION = re.compile(r"[/\-–—,;:()\[\].]")
_WHITESPACE = re.compile(r"\s+")

# Minimum similarity score to include a project as a suggestion
_THRESHOLD = 0.45
# Maximum number of suggestions to return per FinVe
_MAX_SUGGESTIONS = 3


def _normalize(text: str) -> str:
    """Normalise a name for fuzzy comparison.

    Steps:
    1. Unicode NFC normalise
    2. Lowercase
    3. Strip leading type prefixes (ABS, NBS, ABS/NBS …)
    4. Replace punctuation / hyphens with spaces
    5. Collapse whitespace
    """
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = _STRIP_PREFIXES.sub("", text)
    text = _PUNCTUATION.sub(" ", text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text


def _score(finve_name: str, project_name: str) -> float:
    """Return a similarity score in [0, 1] between two normalised names."""
    a = _normalize(finve_name)
    b = _normalize(project_name)
    if not a or not b:
        return 0.0

    # Full-string similarity
    full = SequenceMatcher(None, a, b, autojunk=False).ratio()

    # Token-set bonus: score using sorted token intersection (handles reordering)
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if tokens_a and tokens_b:
        common = tokens_a & tokens_b
        token_score = len(common) / max(len(tokens_a), len(tokens_b))
    else:
        token_score = 0.0

    # Combine: weight full-string slightly more than token overlap
    return 0.6 * full + 0.4 * token_score


def suggest_projects_for_finve(
    finve_name: str,
    projects: list,  # list of Project ORM instances (need .id and .name)
) -> list[int]:
    """Return a list of project IDs (up to _MAX_SUGGESTIONS) that best match
    the given FinVe name.  Only projects scoring above _THRESHOLD are included.
    """
    scored: list[tuple[float, int]] = []
    for project in projects:
        if not project.name:
            continue
        s = _score(finve_name, project.name)
        if s >= _THRESHOLD:
            scored.append((s, project.id))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [pid for _, pid in scored[:_MAX_SUGGESTIONS]]
