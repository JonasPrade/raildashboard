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


def suggest_projects_for_sv_erlaeuterung(
    project_names: list[str],
    projects: list,  # list of Project ORM instances (need .id and .name)
) -> list[int]:
    """For Sammel-FinVes: match each listed project name from the Erläuterung
    against DB projects and return the best match per name (deduplicated).
    Used to populate the parent FinVe's suggested_project_ids.
    """
    result: list[int] = []
    seen: set[int] = set()
    for name in project_names:
        best: tuple[float, int] | None = None
        for proj in projects:
            if not proj.name:
                continue
            s = _score(name, proj.name)
            if s >= _THRESHOLD and (best is None or s > best[0]):
                best = (s, proj.id)
        if best and best[1] not in seen:
            seen.add(best[1])
            result.append(best[1])
    return result


def suggest_per_erlaeuterung_project(
    project_names: list[str],
    projects: list,  # list of Project ORM instances (need .id and .name)
) -> list[int | None]:
    """Return one best-match project ID per erlaeuterung project name (or None if
    no match is found above the threshold).  Result length == len(project_names).
    Unlike suggest_projects_for_sv_erlaeuterung, duplicates are allowed so that
    each subrow gets its own independent suggestion.
    """
    result: list[int | None] = []
    for name in project_names:
        best: tuple[float, int] | None = None
        for proj in projects:
            if not proj.name:
                continue
            s = _score(name, proj.name)
            if s >= _THRESHOLD and (best is None or s > best[0]):
                best = (s, proj.id)
        result.append(best[1] if best else None)
    return result


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
