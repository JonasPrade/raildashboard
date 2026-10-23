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
from typing import NamedTuple

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

# Free-text section → subproject name (Fulda "Abschnitt"): short, partial text,
# so the threshold is permissive — it is only a suggestion.
_SUBPROJECT_NAME_THRESHOLD = 0.35

# PFA → subproject name match (feature-vib-import.md → Phase 8): only place
# tokens count, and the best candidate must lead the runner-up clearly.
_PFA_THRESHOLD = 0.5
_PFA_MARGIN = 0.1


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


def suggest_subproject_by_name(
    text: str,
    subprojects: list,  # list of Project ORM instances (.id, .name)
) -> int | None:
    """Best fuzzy match of a free-text section name against subproject names
    above ``_SUBPROJECT_NAME_THRESHOLD``, or None (used for Fulda sections;
    VIB PFA rows use :func:`suggest_subproject_for_pfa`)."""
    if not text or not text.strip():
        return None
    best_id: int | None = None
    best_score = 0.0
    for sub in subprojects:
        if not sub.name:
            continue
        s = _score(text, sub.name)
        if s > best_score:
            best_score = s
            best_id = sub.id
    return best_id if best_score >= _SUBPROJECT_NAME_THRESHOLD else None


# ---------------------------------------------------------------------------
# PFA section → subproject (feature-vib-import.md → Phase 8)
# ---------------------------------------------------------------------------

# A section number: "7", "7.1", "16a", "3.0a".
_NUM = r"\d+(?:\.\d+)?[a-z]?"
# A number list after a section keyword in a project name or number:
# "Abschnitt 7", "Abschnitt7", "PF 11, 14", "PF 15-16", "PFA 1+2", "StA 2-6".
_KEYED_NUMBERS_RE = re.compile(
    rf"\b(?:abschnitt|pfa|pf|pa|sta|ba)\.?\s*({_NUM}(?:\s*(?:,|\+|-|–|—|/|und)\s*{_NUM})*)",
    re.IGNORECASE,
)
_NUM_RE = re.compile(_NUM, re.IGNORECASE)
_RANGE_RE = re.compile(r"^\s*(\d+)\s*[-–—]\s*(\d+)\s*$")

# Noise in PFA localities: "(a)"/"(e)" (Anfang/Ende), km ranges, footnote marks.
_KM_RE = re.compile(r"\(?\bkm\b[^)]*\)?", re.IGNORECASE)
_AE_RE = re.compile(r"\((?:a|e)\)", re.IGNORECASE)
_FOOTNOTE_RE = re.compile(r"[¹²³⁴⁵⁶⁷⁸⁹⁰]|\^\{?\d+\}?")
_WORD_RE = re.compile(r"[^\W\d_]{3,}", re.UNICODE)
# Words that say nothing about the place of a section.
_GENERIC_TOKENS = frozenset(
    {
        "abs", "nbs", "vde", "abschnitt", "abschnitte", "teilabschnitt", "teilmaßnahme",
        "teilmaßnahnme", "maßnahme", "baustufe", "stufe", "projekt", "ausbau", "neubau",
        "ausbaustrecke", "neubaustrecke", "strecke", "bahnhof", "hbf", "abzw", "und",
        "der", "die", "das", "von", "bis", "mit", "für", "grenze", "knoten", "bswag",
        "rrx", "gleis", "gleise", "nord", "süd", "ost", "west", "pfa", "sta",
        "stadtgebiet", "bereich", "anbindung", "sanierung", "zweigleisiger",
    }
)


class PfaSuggestion(NamedTuple):
    project_id: int
    kind: str  # "vorjahr" | "nummer" | "name"
    reason: str  # German, shown to the editor/agent
    strong: bool  # safe to apply without a look (previous year, unique number)


def _pfa_numbers(nr_pfa: str | None) -> set[str]:
    """Numbers of a PFA cell: '7.1' → {'7.1'}, '2–6' → {'2'..'6'}, '16a' → {'16a'}."""
    if not nr_pfa:
        return set()
    text = _FOOTNOTE_RE.sub("", nr_pfa).strip().lower()
    m = _RANGE_RE.match(text)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        if 0 < hi - lo <= 20:
            return {str(n) for n in range(lo, hi + 1)}
    return set(_NUM_RE.findall(text))


def _major(number: str) -> str:
    """'7.1' → '7', '16a' → '16', '3.0a' → '3'."""
    return re.match(r"\d+", number).group(0)


def project_section_numbers(*texts: str | None) -> set[str]:
    """Section numbers a project carries after a keyword in name/number."""
    out: set[str] = set()
    for text in texts:
        for m in _KEYED_NUMBERS_RE.finditer(text or ""):
            group = m.group(1).lower()
            parts = re.split(r"\s*(?:,|\+|/|und)\s*", group)
            for part in parts:
                rng = _RANGE_RE.match(part)
                if rng and 0 < int(rng.group(2)) - int(rng.group(1)) <= 20:
                    out.update(str(n) for n in range(int(rng.group(1)), int(rng.group(2)) + 1))
                else:
                    out.update(_NUM_RE.findall(part))
    return out


def _place_tokens(text: str | None, stop: frozenset[str] | set[str] = frozenset()) -> set[str]:
    if not text:
        return set()
    text = unicodedata.normalize("NFC", text).lower()
    text = _FOOTNOTE_RE.sub(" ", _AE_RE.sub(" ", _KM_RE.sub(" ", text)))
    return {t for t in _WORD_RE.findall(text) if t not in _GENERIC_TOKENS and t not in stop}


def place_stop_tokens(*names: str | None) -> set[str]:
    """Tokens of the Vorhaben and its projects: they name the whole line, not a
    section ('Nürnberg', 'Erfurt' in 'Nürnberg–Erfurt'), so they never decide."""
    out: set[str] = set()
    for name in names:
        out |= _place_tokens(name)
    return out


def _place_score(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    common = a & b
    if not common:
        return 0.0
    # Containment: subproject names add words ("Güterzugtunnel Fürth") that the
    # locality lacks; Jaccard keeps a one-word overlap with a long name lower.
    return 0.6 * (len(common) / min(len(a), len(b))) + 0.4 * (len(common) / len(a | b))


def suggest_subproject_for_pfa(
    nr_pfa: str | None,
    oertlichkeit: str | None,
    abschnitt_label: str | None,
    candidates: list,  # (project, depth): Project-like with .id/.name/.project_number
    stop_tokens: set[str] | frozenset[str] = frozenset(),
) -> PfaSuggestion | None:
    """Best subproject for one PFA row by section number, then by place name.

    Section number: the row's number(s) against the numbers a candidate carries
    after "Abschnitt"/"PFA"/"PF"/"StA"… in its name or project number; an exact
    number beats the main number ("7.1" → "Abschnitt 7"), a deeper project
    beats its ancestor. Unique → strong. Name: place tokens (without the
    Vorhaben's own place names) above ``_PFA_THRESHOLD`` and ahead of the
    runner-up by ``_PFA_MARGIN`` → weak. The previous year is handled by the
    caller (it needs the database).
    """
    numbers = _pfa_numbers(nr_pfa)
    if numbers:
        majors = {_major(n) for n in numbers}
        hits: list[tuple[int, int, object, str]] = []  # (level, depth, project, carried)
        for project, depth in candidates:
            carried = project_section_numbers(project.name, getattr(project, "project_number", None))
            if not carried:
                continue
            if numbers & carried:
                hits.append((2, depth, project, sorted(numbers & carried)[0]))
            elif majors & carried:
                hits.append((1, depth, project, sorted(majors & carried)[0]))
        if hits:
            best_key = max((lvl, depth) for lvl, depth, _, _ in hits)
            best = [h for h in hits if (h[0], h[1]) == best_key]
            if len(best) == 1:
                _, _, project, carried = best[0]
                return PfaSuggestion(
                    project.id,
                    "nummer",
                    f"Abschnittsnummer {nr_pfa.strip()} ↔ {carried} in „{project.name}“",
                    True,
                )
            candidates = [(h[2], h[1]) for h in best]

    tokens = _place_tokens(oertlichkeit, stop_tokens) or _place_tokens(abschnitt_label, stop_tokens)
    if not tokens:
        return None
    scored = sorted(
        (
            (_place_score(tokens, _place_tokens(project.name, stop_tokens)), depth, project)
            for project, depth in candidates
            if project.name
        ),
        key=lambda x: (x[0], x[1]),
        reverse=True,
    )
    if not scored or scored[0][0] < _PFA_THRESHOLD:
        return None
    if len(scored) > 1 and scored[0][0] - scored[1][0] < _PFA_MARGIN and scored[1][1] == scored[0][1]:
        return None
    score, _, project = scored[0]
    return PfaSuggestion(project.id, "name", f"Namensähnlichkeit {score:.2f}", False)


def pfa_row_key(nr_pfa: str | None, oertlichkeit: str | None) -> tuple[str, str]:
    """Normalised identity of a PFA row across report years."""
    nr = _FOOTNOTE_RE.sub("", nr_pfa or "").strip().lower().replace("–", "-")
    place = " ".join(sorted(_place_tokens(oertlichkeit)))
    return nr, place
