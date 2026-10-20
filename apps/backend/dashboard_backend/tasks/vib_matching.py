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

# VIB headings often start with the running number of the Bedarfsplan line:
# "Lfd. Vorhaben Nr. 2 – ABS Lübeck/Hagenow Land–Rostock–Stralsund (VDE Nr. 1)".
# Drop it so the name itself (and the ABS/NBS prefix after it) is compared.
_LFD_PREFIX = re.compile(r"^lfd\.?\s*(?:vorhaben\s*)?nr\.?\s*\d+\w?\s*[-–—:]?\s*")
_STRIP_PREFIXES = re.compile(
    r"^(abs/nbs|nbs/abs|abs|nbs|neu-|aus-|um-)\s*",
    re.IGNORECASE,
)
_PUNCTUATION = re.compile(r"[/\-–—,;:()\[\].]")
_WHITESPACE = re.compile(r"\s+")

# Slightly higher threshold than finve_matching (0.45) — VIB names are long proper nouns
_THRESHOLD = 0.50
_MAX_SUGGESTIONS = 3

# PFA section labels/localities are short and partial, so the threshold for
# matching a PFA to a subproject is permissive — it is only a review-UI hint.
_PFA_THRESHOLD = 0.35


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = _LFD_PREFIX.sub("", text)
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


def rank_projects_for_vib_entry(
    vib_name: str,
    projects: list,  # list of Project ORM instances (.id, .name, .description)
) -> list[tuple[int, str, float]]:
    """All candidate projects for a VIB name as ``(project_id, reason, score)``.

    VDE-number matches come first (reason ``"vde"``, score 1.0), then fuzzy
    name matches above _THRESHOLD (reason ``"name"``), best first.
    """
    vde: list[tuple[int, str, float]] = []
    fuzzy: list[tuple[int, str, float]] = []
    for project in projects:
        if not project.name:
            continue
        proj_desc = getattr(project, "description", None) or ""
        if _vde_match(vib_name, project.name, proj_desc):
            vde.append((project.id, "vde", 1.0))
            continue
        s = _score(vib_name, project.name)
        if s >= _THRESHOLD:
            fuzzy.append((project.id, "name", s))
    fuzzy.sort(key=lambda x: x[2], reverse=True)
    return vde + fuzzy


def same_vib_name(a: str, b: str) -> bool:
    """True when two VIB headings name the same Vorhaben (year-over-year)."""
    return bool(a and b) and (_normalize(a) == _normalize(b) or _score(a, b) >= 0.9)


def suggest_projects_for_vib_entry(
    vib_name: str,
    projects: list,  # list of Project ORM instances (.id, .name, .description)
) -> list[int]:
    """Return project IDs (up to _MAX_SUGGESTIONS) that best match the given VIB name.

    VDE-number matches first (high confidence), then fuzzy name matches above
    _THRESHOLD — see :func:`rank_projects_for_vib_entry`.
    """
    return [pid for pid, _, _ in rank_projects_for_vib_entry(vib_name, projects)][:_MAX_SUGGESTIONS]


def suggest_project_for_bauportal(
    title: str,
    projects: list,  # list of Project ORM instances (.id, .name)
) -> int | None:
    """Best-matching project id for one DB-Bauportal entry, or None.

    Single best fuzzy match of the Bauportal ``shorttitle`` against our project
    names above ``_THRESHOLD``. Only a review-UI suggestion — the editor confirms
    or corrects it before it drives materialisation.
    """
    if not title or not title.strip():
        return None
    best_id: int | None = None
    best_score = 0.0
    for project in projects:
        if not project.name:
            continue
        s = _score(title, project.name)
        if s > best_score:
            best_score = s
            best_id = project.id
    return best_id if best_score >= _THRESHOLD else None


def suggest_subproject_for_pfa(
    pfa_text: str,
    subprojects: list,  # list of Project ORM instances (.id, .name)
) -> int | None:
    """Best-matching subproject id for one PFA section, or None.

    ``pfa_text`` is the combined section identifier (abschnitt_label / nr_pfa /
    oertlichkeit). Returns the single best fuzzy match against the candidate
    subproject names above ``_PFA_THRESHOLD``, or None when nothing is close
    enough. Used to pre-fill the per-PFA subproject Select in the review UI; the
    editor confirms or corrects it.
    """
    if not pfa_text or not pfa_text.strip():
        return None
    best_id: int | None = None
    best_score = 0.0
    for sub in subprojects:
        if not sub.name:
            continue
        s = _score(pfa_text, sub.name)
        if s > best_score:
            best_score = s
            best_id = sub.id
    return best_id if best_score >= _PFA_THRESHOLD else None
