"""Fuzzy name-matching between VIB Vorhaben names and Project names.

Used during the VIB PDF parse task to suggest project assignments for each
Vorhaben entry so editors can confirm or correct them in the review UI.

Two matching strategies are combined:
1. VDE number extraction — "VDE Nr. 1" or "VDE 8.2" in the Vorhaben name is
   matched against the same pattern in project names/descriptions.
2. Fuzzy name matching — SequenceMatcher + token overlap, same algorithm as
   finve_matching.py, threshold 0.5 (raised slightly for VIB because names
   tend to be longer and more distinctive).
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

# ---------------------------------------------------------------------------
# VDE number extraction
# ---------------------------------------------------------------------------

# Matches "VDE Nr. 1", "VDE Nr.1", "VDE 8", "VDE 8.2", "VDE 8.1b"
_VDE_RE = re.compile(r"\bVDE\s*(?:Nr\.?\s*)?(\d+(?:\.\d+[a-z]?)?)\b", re.IGNORECASE)


def _extract_vde_number(text: str) -> str | None:
    """Return the VDE number string (e.g. '1', '8.2') from text, or None."""
    m = _VDE_RE.search(text)
    return m.group(1) if m else None


def _vde_match(vib_name: str, project_name: str, project_description: str | None) -> bool:
    """True if both texts refer to the same VDE number."""
    vib_vde = _extract_vde_number(vib_name)
    if vib_vde is None:
        return False
    candidate_text = (project_name or "") + " " + (project_description or "")
    proj_vde = _extract_vde_number(candidate_text)
    return proj_vde is not None and vib_vde == proj_vde


# ---------------------------------------------------------------------------
# Fuzzy name matching (same approach as finve_matching.py)
# ---------------------------------------------------------------------------

_STRIP_PREFIXES = re.compile(
    r"^(abs/nbs|nbs/abs|abs|nbs|neu-|aus-|um-)\s*",
    re.IGNORECASE,
)
_PUNCTUATION = re.compile(r"[/\-–—,;:()\[\].]")
_WHITESPACE = re.compile(r"\s+")

# Slightly higher threshold than finve_matching (0.45) — VIB names are long proper nouns
_THRESHOLD = 0.50
_MAX_SUGGESTIONS = 3


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = _STRIP_PREFIXES.sub("", text)
    text = _PUNCTUATION.sub(" ", text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text


def _score(vib_name: str, project_name: str) -> float:
    """Return a similarity score in [0, 1] between two normalised names."""
    a = _normalize(vib_name)
    b = _normalize(project_name)
    if not a or not b:
        return 0.0

    full = SequenceMatcher(None, a, b, autojunk=False).ratio()

    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if tokens_a and tokens_b:
        common = tokens_a & tokens_b
        token_score = len(common) / max(len(tokens_a), len(tokens_b))
    else:
        token_score = 0.0

    return 0.6 * full + 0.4 * token_score


def suggest_projects_for_vib_entry(
    vib_name: str,
    projects: list,  # list of Project ORM instances (.id, .name, .description)
) -> list[int]:
    """Return project IDs (up to _MAX_SUGGESTIONS) that best match the given VIB name.

    Strategy:
    1. If any project shares the same VDE number → include it unconditionally at
       the top of the list (high confidence match).
    2. Fuzzy name match for remaining candidates above _THRESHOLD.
    3. Return deduplicated list, VDE matches first.
    """
    vde_matches: list[int] = []
    fuzzy_scored: list[tuple[float, int]] = []
    seen: set[int] = set()

    for project in projects:
        if not project.name:
            continue
        proj_desc = getattr(project, "description", None) or ""

        if _vde_match(vib_name, project.name, proj_desc):
            if project.id not in seen:
                vde_matches.append(project.id)
                seen.add(project.id)

        s = _score(vib_name, project.name)
        if s >= _THRESHOLD and project.id not in seen:
            fuzzy_scored.append((s, project.id))

    fuzzy_scored.sort(key=lambda x: x[0], reverse=True)
    result = vde_matches[:]
    for _, pid in fuzzy_scored:
        if pid not in seen:
            result.append(pid)
            seen.add(pid)
        if len(result) >= _MAX_SUGGESTIONS:
            break

    return result[:_MAX_SUGGESTIONS]
