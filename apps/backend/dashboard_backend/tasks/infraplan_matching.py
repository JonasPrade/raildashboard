"""Project suggestions for Infraplan rows (stage 4 of the parse pipeline).

See docs/features/feature-infraplan-import.md → "Zuordnung zu Projekten" and
"Ausbau für den Import 2027". Order per row, strongest first:

1. **Previous year by number** — the confirmed links of the newest earlier year
   with the same ``primary_number`` (``NUMBER``, 1.0), with that year's note.
2. **Previous year by text** — same kind of table (Bedarfsplan/GVFG/InvKG) and
   the same normalised Bezeichnung + Maßnahme (``PREVIOUS_YEAR``, 0.95).
3. **Project number** — ``primary_number`` equals ``Project.project_number``
   (``NUMBER``, 1.0); GVFG rows with the normaliser of the GVFG import
   (``GVFG_KEY``, 1.0).
4. **Alias** — a Deutschlandtakt id ("DT 38") of the row equals an alias of the
   project (``ALIAS``, 1.0). D-numbers of the dashboard are never equated.
5. **Context** — the Bezeichnung names a parent ("Großknoten München",
   "PB 07: ABS/NBS Karlsruhe – Basel"); its subprojects (two levels) are matched
   by section number (Abschnitt/PFA, Teilmaßnahme, Baustufe; 0.9) or, if the
   best is unambiguous, by the words left after removing the parent's name
   (``CONTEXT``).
6. **Fuzzy** over Bezeichnung and Maßnahme against names and free aliases
   (``vib_matching._score``). A matching subproject replaces its superior.

Every comparison runs on :func:`normalize_text`, which writes out the
abbreviations of the Infraplan ("Ubf", "Vbk", "2gl.", "Mü", …) on both sides.
Rows with a suggestion of at least ``PRESELECT_CONFIDENCE`` are preselected.
The pure part (:func:`suggest_rows`) has no DB access.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from dashboard_backend.models.infraplan import (
    InfraplanEntry,
    InfraplanEntryProject,
    InfraplanReport,
)
from dashboard_backend.models.projects.project import Project
from dashboard_backend.services.gvfg_parser import normalize_key
from dashboard_backend.tasks.vib_matching import _VDE_RE, _score

PRESELECT_CONFIDENCE = 0.85
_FUZZY_THRESHOLD = 0.5
_MAX_FUZZY = 3
_MAX_SUGGESTIONS = 6
# Tokens shorter than this ("bf", "abs", "und") say nothing about a project.
_MIN_TOKEN = 4

CONF_PREVIOUS_TEXT = 0.95
CONF_CONTEXT_NUMBER = 0.9
# A parent named by the Bezeichnung without a matching subproject: a hint for
# collective rows, never preselected.
CONF_CONTEXT_PARENT = 0.7
# A name hit on a Bezeichnung that only names the parent stays below the threshold.
_CAPPED_BEZEICHNUNG = 0.8
# A word match among subprojects some of which are only "Teilmaßnahme n".
CONF_UNNAMED_SIBLINGS = 0.8
# A DT id that a row names besides its main measure ("… inkl. DT 2 …").
CONF_ALIAS_PART = 0.8

_PB_PREFIX = re.compile(r"^\s*PB\s*\d+[a-z]?\s*:\s*", re.IGNORECASE)

# Reasons of a suggestion. Identifier reasons are stored as source NUMBER,
# name-based ones as FUZZY.
REASON_NUMBER = "NUMBER"
REASON_GVFG_KEY = "GVFG_KEY"
REASON_PREVIOUS_YEAR = "PREVIOUS_YEAR"
REASON_ALIAS = "ALIAS"
REASON_CONTEXT = "CONTEXT"
REASON_FUZZY = "FUZZY"
# A previous-year link or a number says it all; nothing else is added then.
_DEFINITE_REASONS = (REASON_NUMBER, REASON_GVFG_KEY, REASON_PREVIOUS_YEAR)
_REASON_RANK = {
    REASON_NUMBER: 0,
    REASON_GVFG_KEY: 0,
    REASON_PREVIOUS_YEAR: 1,
    REASON_ALIAS: 2,
    REASON_CONTEXT: 3,
    REASON_FUZZY: 4,
}


@dataclass(frozen=True)
class ProjectRef:
    id: int
    name: str
    superior_project_id: int | None = None
    project_number: str | None = None
    aliases: tuple[str, ...] = ()
    description: str | None = None


@dataclass(frozen=True)
class PreviousLink:
    project_id: int
    note: str | None = None


@dataclass
class PreviousYear:
    """Confirmed links of earlier years: by ``primary_number`` and by the
    normalised row text (:func:`row_text_key`), each from the newest year that
    has the key."""

    by_number: dict[str, list[PreviousLink]] = field(default_factory=dict)
    by_text: dict[str, list[PreviousLink]] = field(default_factory=dict)
    years: dict[str, int] = field(default_factory=dict)  # key → year it came from

    @classmethod
    def from_numbers(cls, links: dict[str, list[int]]) -> "PreviousYear":
        return cls(by_number={k: [PreviousLink(pid) for pid in v] for k, v in links.items()})


# --- Normalisation ----------------------------------------------------------------

_NUMBER_WORDS = {"1": "ein", "2": "zwei", "3": "drei", "4": "vier", "5": "fünf", "6": "sechs"}
_ORDINAL_WORDS = {"zweite": "2", "dritte": "3", "vierte": "4"}

# (pattern, replacement) on lower-case text, in this order. Word boundaries keep
# "bf" out of "hbf" and "ma" out of "main".
_ABBREVIATIONS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern), replacement)
    for pattern, replacement in (
        (r"frankfurt\s*(?:am\s+main|\(main\)|/\s*m(?:ain)?\b\.?)", "frankfurt"),
        (r"\bgroßknoten\b", "knoten"),
        (r"\bubf\b\.?", "umschlagbahnhof"),
        (r"\bvbk\b\.?", "verbindungskurve"),
        (r"\babzw\b\.?", "abzweig"),
        (r"\bü-?bw\b\.?", "überwerfungsbauwerk"),
        (r"\büberwerfungsbw\b\.?", "überwerfungsbauwerk"),
        (r"\bkrbw\b\.?", "kreuzungsbauwerk"),
        (r"\bkrzb(?:h)?f\b\.?", "kreuzungsbahnhof"),
        (r"\bkrzg?s?gleis", "kreuzungsgleis"),
        (r"\bhbf\b\.?", "hauptbahnhof"),
        (r"\bgbf\b\.?", "güterbahnhof"),
        (r"\brbf\b\.?", "rangierbahnhof"),
        (r"\bpbf\b\.?", "personenbahnhof"),
        (r"\bbb(?:h)?f\b\.?", "betriebsbahnhof"),
        (r"\bb(?:h)?f\b\.?", "bahnhof"),
        (r"\bü-?gleis", "überholgleis"),
        (r"\belektr\b\.?", "elektrifizierung"),
        (r"\bteilmaßnahne?me?n?\b", "teilmaßnahme"),
        (r"\btm\s*(\d+)", r"teilmaßnahme \1"),
        (r"\b(\d+)\.?\s*bs\b\.?", r"\1. baustufe"),
        (r"\b(\d+)\.\s*ba\b\.?", r"\1. bauabschnitt"),
        (r"\b(?:mü|mu)\b", "münchen"),
        (r"\bhh\b", "hamburg"),
        (r"\bma\b", "mannheim"),
        (r"\bhd\b", "heidelberg"),
        (r"\bffm\b", "frankfurt"),
        (r"\blpz\b", "leipzig"),
        (r"\bbrhv\b", "bremerhaven"),
        (r"\bhann\b\.?", "hannover"),
        (r"\bmz\b", "mainz"),
        (r"\bbe?(?=[ -](?:spandau|südkreuz)\b)", "berlin"),
    )
)
_ORDINAL_TRACK = re.compile(r"\b(\d)\.\s*(?:gleis\b|gl\b\.?)")
_ORDINAL_WORD_TRACK = re.compile(r"\b(zweite|dritte|vierte)[snr]?\s+gleis")
_TRACKS = re.compile(r"\b(\d|mehr)\s*-?\s*(?:gl\b\.?|gleisige?[nrms]?\b)")
_TRACK_WORDS = re.compile(r"\b(ein|zwei|drei|vier|fünf|sechs|mehr)gleisige[nrms]?\b")


_PUNCTUATION = re.compile(r"[/\-–—,;:()\[\].!?„“\"'+&]")
# A leading "ABS"/"NBS" as a word only — "Abstellanlage" keeps its letters.
_LEADING_KIND = re.compile(r"^(?:(?:abs|nbs)\b\s*)+")


def normalize_text(text: str | None) -> str:
    """Lower-case text with the Infraplan's abbreviations written out, the
    punctuation removed and a leading ABS/NBS dropped."""
    text = _PUNCTUATION.sub(" ", expand_abbreviations(text))
    return _LEADING_KIND.sub("", " ".join(text.split()))


def expand_abbreviations(text: str | None) -> str:
    """Lower-case text with abbreviations written out, punctuation kept (the
    section numbers "PFA 9.2" still need their dots)."""
    if not text:
        return ""
    # The parser hands over U+FFFD where the PDF has a full stop ("1gl�").
    text = unicodedata.normalize("NFC", text).replace("�", ".").lower()
    text = _ORDINAL_TRACK.sub(r"\1. gleis", text)
    text = _ORDINAL_WORD_TRACK.sub(lambda m: f"{_ORDINAL_WORDS[m.group(1)]}. gleis", text)
    text = _TRACKS.sub(lambda m: f"{_NUMBER_WORDS.get(m.group(1), m.group(1))}gleisig", text)
    text = _TRACK_WORDS.sub(r"\1gleisig", text)
    for pattern, replacement in _ABBREVIATIONS:
        text = pattern.sub(replacement, text)
    return text


def strip_pb_prefix(text: str | None) -> str:
    return _PB_PREFIX.sub("", text or "").strip()


def _tokens(text: str) -> set[str]:
    """Significant tokens of an already normalised text."""
    return {t for t in text.split() if len(t) >= _MIN_TOKEN}


def row_text_key(row: dict[str, Any] | Any) -> str | None:
    """Kind of table + normalised Bezeichnung and Maßnahme — the same measure
    keeps this key from one year to the next even without a number."""
    get = row.get if isinstance(row, dict) else lambda k: getattr(row, k, None)
    section = str(get("section") or "")
    kind = "GVFG" if section.startswith("GVFG") else "BP" if section.startswith("BP") else section
    text = " | ".join(
        normalize_text(strip_pb_prefix(get(k)) if k == "bezeichnung" else get(k))
        for k in ("bezeichnung", "massnahme")
    )
    return f"{kind}:{text}" if text.strip(" |") else None


def _number_key(text: str | None) -> str | None:
    """Project numbers compared without case and spacing ("InvKG Nr. 6")."""
    if not text:
        return None
    key = re.sub(r"[\s.]+", "", text).lower()
    return key or None


# --- Identifiers --------------------------------------------------------------------

_DT_RE = re.compile(r"\b(?:dt|d-takt)\s*(\d+)(?:\s*[/–-]\s*(\d+))?", re.IGNORECASE)
_PB_RE = re.compile(r"\bpb\s*0*(\d+)\b", re.IGNORECASE)


_BUNDLE_NUMBER = re.compile(r"(?:^|_)PB_?(\d+)$", re.IGNORECASE)


def identifiers(text: str | None) -> set[str]:
    """Ids in a text: ``DT 38`` (Deutschlandtakt), ``PB 7`` (Projektbündel),
    ``VDE 8.1``. A range "DT 108/109" or "D-Takt 80–81" yields both ends."""
    if not text:
        return set()
    text = text.replace("�", ".")
    found: set[str] = set()
    for match in _DT_RE.finditer(text):
        first = int(match.group(1))
        last = int(match.group(2)) if match.group(2) else first
        if last < first or last - first > 10:
            last = first
        found.update(f"DT {n}" for n in range(first, last + 1))
    found.update(f"PB {int(m.group(1))}" for m in _PB_RE.finditer(text))
    found.update(f"VDE {m.group(1).lower()}" for m in _VDE_RE.finditer(text))
    return found


def _has_main_measure(massnahme: str | None) -> bool:
    """True when the Maßnahme names something of its own before its first DT
    id ("Elektrifizierung, 1gl. Vbk Bad Kleinen inkl DT 2 …"); false for rows
    that are DT measures ("DT 87 Langes Feld – Stuttgart Hbf")."""
    match = _DT_RE.search(massnahme or "")
    if not match:
        return False
    before = normalize_text(massnahme[: match.start()])
    return any(w not in _GENERIC and w not in _STOP and not w.isdigit() for w in _words(before))


def split_aliases(aliases: Iterable[str]) -> tuple[set[str], list[str]]:
    """(identifiers, free aliases) of a project's alias list."""
    ids: set[str] = set()
    free: list[str] = []
    for alias in aliases:
        found = identifiers(alias)
        if found:
            ids |= found
        elif alias and alias.strip():
            free.append(alias.strip())
    return ids, free


# --- Section numbers ----------------------------------------------------------------

_SECTION_RES = {
    "ABSCHNITT": re.compile(
        r"\b(?:(?:strecken|bau|ausbau)?abschnitt|pfa|pfb|sta|pf)\s*(\d+(?:\.\d+)?)(?:\s*[-–]\s*(\d+)\b(?!\.))?"
    ),
    "TEILMASSNAHME": re.compile(r"\bteilmaßnahme\s*(\d+)"),
    "STUFE": re.compile(
        r"\b(\d+)\.?\s*(?:bau|ausbau|inbetriebnahme|betriebs)?stufe\b|\b(?:bau|ausbau)?stufe\s*(\d+)"
    ),
}


def section_numbers(text: str) -> dict[str, set[str]]:
    """Section numbers per kind in an expanded text: "Abschnitt 2-6" →
    {2..6}, "PFA 9.2" → {9.2}, "TM8" → {8}, "2. Baustufe" → {2}."""
    out: dict[str, set[str]] = defaultdict(set)
    for kind, pattern in _SECTION_RES.items():
        for match in pattern.finditer(text):
            groups = [g for g in match.groups() if g]
            if not groups:
                continue
            first = groups[0]
            out[kind].add(first)
            if kind == "ABSCHNITT" and len(groups) > 1 and "." not in first:
                start, end = int(first), int(groups[1])
                if start < end <= start + 20:
                    out[kind].update(str(n) for n in range(start, end + 1))
    return out


_ENUMERATION = re.compile(r"\d\.?\s*(?:und|/|,|bis)\s*\d")


def _major(number: str) -> str:
    return number.split(".")[0]


# --- Word overlap (context) -----------------------------------------------------------

_STOP = {
    "abs", "nbs", "und", "der", "die", "das", "den", "des", "mit", "inkl", "von", "bis",
    "für", "auf", "im", "in", "an", "am", "zum", "zur", "ehem", "sowie", "teilmaßnahme",
    "teilmaßnahmen", "abschnitt", "baustufe", "projektbündel", "grenze", "strecke",
    "pfa", "pfb", "sta", "nr", "zusätzl", "zusätzliche", "zusätzlicher", "ohne", "tlw",
}
# Words that alone never identify a subproject ("Elektrifizierung" fits half
# of all subprojects); they count a third.
_GENERIC = {
    "elektrifizierung", "ausbau", "neubau", "blockverdichtung", "blockverdichtungen",
    "geschwindigkeitserhöhung", "kreuzungsbahnhof", "kreuzungsbahnhöfe", "kreuzungsgleise",
    "überholgleis", "überholgleise", "zweigleisig", "dreigleisig", "viergleisig",
    "eingleisig", "gleis", "bahnhof", "hauptbahnhof", "knoten", "ertüchtigung",
    "erhöhung", "streckengeschwindigkeit", "verbindungskurve", "maßnahmen", "anpassung",
    "abzweig",
}
_GENERIC_WEIGHT = 1 / 3
# A second subproject covered to more than this makes a word match ambiguous.
_AMBIGUOUS = 0.34


_NUMBERED_PART = re.compile(r"\b(?:teilmaßnahme|abschnitt|baustufe)\s*\d+")


def is_unnamed_subproject(name: str, superior_name: str | None) -> bool:
    """True for "Knoten Mannheim Teilmaßnahme 8" under "Knoten Mannheim": a
    numbered part whose name says nothing beyond its superior's name."""
    text = normalize_text(name)
    if not _NUMBERED_PART.search(text):
        return False
    superior = {w for w in _words(normalize_text(superior_name)) if not w.isdigit()}
    return not any(not w.isdigit() and not _covered(w, superior) for w in _words(text))


def _words(text: str) -> set[str]:
    """Context words of a normalised text: numbers and words of 3+ letters."""
    return {t for t in text.split() if t not in _STOP and (t.isdigit() or len(t) >= 3)}


@lru_cache(maxsize=200_000)
def _same_word(a: str, b: str) -> bool:
    if a == b:
        return True
    shorter = min(len(a), len(b))
    # German compounds and endings: "bahnsteige"/"bahnsteig", "wilhelmsburg".
    if shorter >= 5 and (a.startswith(b) or b.startswith(a)):
        return True
    # Typos in long names: "Mainschaff" for "Mainaschaff".
    return shorter >= 7 and SequenceMatcher(None, a, b).ratio() >= 0.9


def _covered(word: str, words: set[str]) -> bool:
    return any(_same_word(word, other) for other in words)


def _weight(word: str) -> float:
    return _GENERIC_WEIGHT if word in _GENERIC else 1.0


def _coverage(target: set[str], words: set[str], rarity: dict[str, float] | None = None) -> float:
    """Weighted share of ``target`` found in ``words``; 0 unless at least one
    non-generic word is found. ``rarity`` lowers words that several
    candidates carry ("Zeithain" in two sections of a line)."""
    rarity = rarity or {}

    def weight(word: str) -> float:
        return _weight(word) * rarity.get(word, 1.0)

    hit = [w for w in target if _covered(w, words)]
    if not any(w not in _GENERIC for w in hit):
        return 0.0
    # A generic word counts when the row has it, but its absence costs nothing
    # ("Abzweig Röderau – Abzweig Zeithain" for "Röderau – Zeithain").
    total = sum(weight(w) for w in target if w not in _GENERIC or w in hit)
    return sum(weight(w) for w in hit) / total


# --- Matcher ----------------------------------------------------------------------------


class _Index:
    """Everything about the project list the rows are matched against."""

    def __init__(self, projects: list[ProjectRef]) -> None:
        self.by_id = {p.id: p for p in projects}
        self.children: dict[int, list[ProjectRef]] = defaultdict(list)
        for p in projects:
            if p.superior_project_id in self.by_id:
                self.children[p.superior_project_id].append(p)
        self.by_gvfg_key: dict[str, list[ProjectRef]] = defaultdict(list)
        self.by_number: dict[str, list[ProjectRef]] = defaultdict(list)
        self.by_identifier: dict[str, list[ProjectRef]] = defaultdict(list)
        self.names: dict[int, list[str]] = {}
        self.tokens: dict[int, set[str]] = {}
        # Words of each name (name, free aliases) and of the description's
        # first sentence: the parent detection and the subproject words.
        self.word_sets: dict[int, list[set[str]]] = {}
        self.name_words: dict[int, set[str]] = {}
        self.words: dict[int, set[str]] = {}
        for p in projects:
            gvfg = normalize_key(p.project_number)
            if gvfg:
                self.by_gvfg_key[gvfg].append(p)
            number = _number_key(p.project_number)
            if number:
                self.by_number[number].append(p)
            alias_ids, free = split_aliases(p.aliases)
            # VDE ids are part of many names ("ABS/NBS Leipzig – Dresden (VDE 9)"),
            # bundles carry theirs in the number ("BSWAG_2023_PB_5").
            name_ids = {i for i in identifiers(p.name) if i.startswith("VDE")}
            bundle = _BUNDLE_NUMBER.search(p.project_number or "")
            if bundle:
                name_ids.add(f"PB {int(bundle.group(1))}")
            for ident in alias_ids | name_ids:
                self.by_identifier[ident].append(p)
            names = [normalize_text(n) for n in [p.name, *free] if n]
            self.names[p.id] = [n for n in names if n]
            self.tokens[p.id] = set().union(*(_tokens(n) for n in self.names[p.id])) if names else set()
            self.word_sets[p.id] = [w for w in (_words(n) for n in self.names[p.id]) if w]
            self.name_words[p.id] = set().union(*self.word_sets[p.id]) if self.word_sets[p.id] else set()
            self.words[p.id] = set(self.name_words[p.id])
            if p.description:
                self.words[p.id] |= _words(normalize_text(p.description.split(". ")[0]))

    def own_words(self, project: ProjectRef, context_words: set[str] = frozenset()) -> set[str]:
        """Words of a subproject beyond the context and, when it repeats it,
        its superior's name ("Knoten Hamburg Teilmaßnahme Elmshorn" →
        {"elmshorn"}; "Knoten Riesa" under "3. Baustufe: Riesa – Dresden"
        keeps "riesa"). No numbers."""
        words = {w for w in self.words.get(project.id, set()) if not w.isdigit()}
        superior = self.name_words.get(project.superior_project_id, set()) if project.superior_project_id else set()
        superior = {w for w in superior if not w.isdigit()}
        if superior and sum(1 for w in superior if _covered(w, words)) / len(superior) >= 0.6:
            words = {w for w in words if not _covered(w, superior)}
        return {w for w in words if not _covered(w, set(context_words))}

    def is_unnamed(self, project: ProjectRef, context_words: set[str] = frozenset()) -> bool:
        """A subproject that only says "Teilmaßnahme 3" (no description either)."""
        return (
            not project.description
            and bool(_NUMBERED_PART.search(normalize_text(project.name)))
            and not self.own_words(project, context_words)
        )

    def ancestors(self, project_id: int) -> set[int]:
        out: set[int] = set()
        current = self.by_id.get(project_id)
        while current and current.superior_project_id in self.by_id and current.superior_project_id not in out:
            out.add(current.superior_project_id)
            current = self.by_id[current.superior_project_id]
        return out

    def descendants(self, project_id: int) -> list[ProjectRef]:
        out: list[ProjectRef] = []
        for child in self.children.get(project_id, []):
            out.append(child)
            out.extend(self.children.get(child.id, []))
        return out


def _row_texts(row: dict[str, Any]) -> list[str]:
    bezeichnung = normalize_text(strip_pb_prefix(row.get("bezeichnung")))
    massnahme = normalize_text(row.get("massnahme"))
    texts = [t for t in (bezeichnung, massnahme) if t]
    if bezeichnung and massnahme:
        texts.append(f"{bezeichnung} {massnahme}")
    return texts


def _fuzzy(
    row: dict[str, Any], index: _Index, projects: list[ProjectRef], has_context: bool
) -> list[tuple[float, ProjectRef]]:
    bezeichnung = normalize_text(strip_pb_prefix(row.get("bezeichnung")))
    massnahme = normalize_text(row.get("massnahme"))
    texts = _row_texts(row)
    if not texts:
        return []
    # When the Bezeichnung only names the parent of the measure ("Großknoten
    # Frankfurt am Main" + "Fernbahntunnel"), a hit on the Bezeichnung alone is
    # a hint, not a match.
    cap_bezeichnung = has_context and bool(massnahme)
    row_tokens = set().union(*(_tokens(t) for t in texts))
    scored: list[tuple[float, ProjectRef]] = []
    for project in projects:
        # Cheap prefilter: without one shared significant word the
        # SequenceMatcher would only find accidental similarity.
        if not row_tokens & index.tokens[project.id]:
            continue
        score = 0.0
        for text in texts:
            text_score = max(_score(text, name) for name in index.names[project.id])
            if cap_bezeichnung and text == bezeichnung:
                text_score = min(text_score, _CAPPED_BEZEICHNUNG)
            score = max(score, text_score)
        if score >= _FUZZY_THRESHOLD:
            scored.append((score, project))
    # A matching subproject is preferred over its superior.
    matched = {p.id for _, p in scored}
    scored = [
        (s, p)
        for s, p in scored
        if not any(
            other.superior_project_id == p.id and other.id in matched for _, other in scored
        )
    ]
    scored.sort(key=lambda pair: (-pair[0], pair[1].id))
    return scored[:_MAX_FUZZY]


def _name_share(words: set[str], target: set[str]) -> tuple[float, int] | None:
    """(share, count) of a name's words found in ``words``, if it is named."""
    target = {w for w in target if not w.isdigit()}
    if len(target) < 2 and not any(len(w) >= 10 for w in target):
        return None
    hit = [w for w in target if _covered(w, words)]
    share = len(hit) / len(target)
    if share >= 0.6 and (len(hit) >= 2 or any(len(w) >= 10 for w in hit)):
        return share, len(hit)
    return None


def _context_parents(row: dict[str, Any], index: _Index) -> list[ProjectRef]:
    """Projects with subprojects that the Bezeichnung names: most of the
    parent's words found in it (at least two, or one long one), best share
    first; else a PB/VDE id of the Bezeichnung. None when a project without
    subprojects fits the Bezeichnung better — then it names that project."""
    raw = row.get("bezeichnung") or ""
    text = normalize_text(strip_pb_prefix(raw))
    if not text:
        return []
    words = _words(text)
    best: list[tuple[tuple[float, int], ProjectRef]] = []
    best_other: tuple[float, int] | None = None
    for project_id, word_sets in index.word_sets.items():
        shares = [s for s in (_name_share(words, target) for target in word_sets) if s]
        if not shares:
            continue
        share = max(shares)
        if project_id in index.children:
            best.append((share, index.by_id[project_id]))
        elif best_other is None or share > best_other:
            best_other = share
    if best_other is not None and (not best or best_other > max(share for share, _ in best)):
        return []
    if best:
        top = max(share for share, _ in best)
        tied = [p for share, p in best if share == top]
        tied_ids = {p.id for p in tied}
        # "ABS Berlin – Dresden" and its "1. Baustufe ABS Berlin – Dresden":
        # the stage is reached as a subproject of the line.
        return [p for p in tied if not (index.ancestors(p.id) & tied_ids)]
    ids = {i for i in identifiers(raw) if not i.startswith("DT")}
    return [p for i in sorted(ids) for p in index.by_identifier.get(i, []) if p.id in index.children]


def _child_texts(child: ProjectRef) -> str:
    """Name and number of a subproject, for the section numbers ("K-004-V01 TM8")."""
    return expand_abbreviations(f"{child.name} {child.project_number or ''}")


def _context(row: dict[str, Any], index: _Index) -> list[tuple[float, ProjectRef, str]]:
    """Subprojects of the parent the Bezeichnung names: by section number,
    else by the words left after the parent's name; the parent itself as a
    weak hint when nothing fits."""
    parents = _context_parents(row, index)
    if not parents:
        return []
    massnahme = expand_abbreviations(row.get("massnahme"))
    bezeichnung = expand_abbreviations(strip_pb_prefix(row.get("bezeichnung")))
    row_numbers = section_numbers(massnahme)
    # The Bezeichnung often names several stages ("1. und 2. Baustufe"); its
    # numbers only count when it names one.
    if not _ENUMERATION.search(bezeichnung):
        for kind, numbers in section_numbers(bezeichnung).items():
            if kind not in row_numbers and len(numbers) == 1:
                row_numbers[kind] = numbers
    out: list[tuple[float, ProjectRef, str]] = []
    for parent in parents:
        candidates = index.descendants(parent.id)
        numbered = _by_number(row_numbers, candidates)
        for child, label in numbered:
            grandchildren = index.children.get(child.id, [])
            # A numbered stage may itself have subprojects that the words name.
            deeper = _by_words(row, index, parent, grandchildren, exclude=label)
            if deeper:
                out.extend(
                    (max(PRESELECT_CONFIDENCE, _word_confidence(score)), d, f"{label}, {_short(parent)}")
                    for score, d in deeper
                )
            elif _names_a_subproject(row, index, parent, child, grandchildren, label):
                # "3. Baustufe: Überholgleis Böhla" is a part of the stage, not the stage.
                out.append((CONF_CONTEXT_PARENT, child, f"{label} unter {_short(parent)}, Teil davon"))
            else:
                out.append((CONF_CONTEXT_NUMBER, child, f"{label} unter {_short(parent)}"))
        if not numbered:
            chosen = _by_words(row, index, parent, candidates)
            # Nameless siblings ("Knoten München Teilmaßnahme 2") may be the
            # real target: a word match among the others stays a suggestion.
            parent_words = index.name_words.get(parent.id, set())
            unnamed = any(index.is_unnamed(c, parent_words) for c in candidates)
            for score, child in chosen:
                confidence = _word_confidence(score)
                detail = f"Teilprojekt von {_short(parent)}"
                if unnamed:
                    confidence = min(confidence, CONF_UNNAMED_SIBLINGS)
                    detail += ", daneben Teilmaßnahmen ohne Namen"
                out.append((confidence, child, detail))
    if not out:
        # Collective rows ("Großknoten Hamburg | …") went to the parent and to
        # new subprojects alike in 2026: a hint for the review, never a match.
        out = [(CONF_CONTEXT_PARENT, p, "Elternprojekt laut Bezeichnung") for p in parents]
    return out


def _word_confidence(score: float) -> float:
    return round(0.6 + 0.3 * score, 2)


def _names_a_subproject(
    row: dict[str, Any],
    index: _Index,
    parent: ProjectRef,
    child: ProjectRef,
    grandchildren: list[ProjectRef],
    label: str,
) -> bool:
    """True when the row has a word beyond the stage that one of the stage's
    subprojects carries."""
    if not grandchildren:
        return False
    text = normalize_text(row.get("massnahme")).replace(normalize_text(label), " ")
    known = index.name_words.get(parent.id, set()) | index.words.get(child.id, set())
    extra = {w for w in _words(text) if w not in _GENERIC and not w.isdigit() and not _covered(w, known)}
    return any(_covered(w, index.words.get(g.id, set())) for w in extra for g in grandchildren)


def _short(project: ProjectRef) -> str:
    return f"„{project.name[:60]}“"


_KIND_LABEL = {"ABSCHNITT": "Abschnitt", "TEILMASSNAHME": "Teilmaßnahme", "STUFE": "Baustufe"}


def _by_number(
    row_numbers: dict[str, set[str]], candidates: list[ProjectRef]
) -> list[tuple[ProjectRef, str]]:
    found: list[tuple[ProjectRef, str]] = []
    for kind, numbers in row_numbers.items():
        child_numbers = {c.id: section_numbers(_child_texts(c)).get(kind, set()) for c in candidates}
        for number in sorted(numbers):
            exact = [c for c in candidates if number in child_numbers[c.id]]
            # "PFA 9.2" falls in "Abschnitt 9" when there is no 9.2 of its own.
            hits = exact or [c for c in candidates if _major(number) in child_numbers[c.id]]
            found.extend((c, f"{_KIND_LABEL[kind]} {number}") for c in hits)
    seen: set[int] = set()
    unique = [(c, label) for c, label in found if not (c.id in seen or seen.add(c.id))]
    # A stage and its own subproject both carry "Baustufe 3": keep the stage.
    return [(c, label) for c, label in unique if c.superior_project_id not in seen]


def _by_words(
    row: dict[str, Any],
    index: _Index,
    parent: ProjectRef,
    candidates: list[ProjectRef],
    exclude: str | None = None,
) -> list[tuple[float, ProjectRef]]:
    """The candidates whose own words (name without the superior's name) the
    row covers fully, or the single best one if nobody else comes close."""
    if not candidates:
        return []
    parent_words = index.name_words.get(parent.id, set())
    text = " ".join(
        normalize_text(t)
        for t in (row.get("massnahme"), strip_pb_prefix(row.get("bezeichnung")))
        if t
    )
    if exclude:
        text = text.replace(normalize_text(exclude), " ")
    row_words = {w for w in _words(text) if not _covered(w, parent_words)}
    own_words = {c.id: index.own_words(c, parent_words) for c in candidates}
    counts: dict[str, int] = defaultdict(int)
    for own in own_words.values():
        for word in own:
            counts[word] += 1
    rarity = {w: 1 / n for w, n in counts.items()}
    scored: list[tuple[float, ProjectRef, frozenset[str]]] = []
    for child in candidates:
        own = own_words[child.id]
        score = _coverage(own, row_words, rarity) if own else 0.0
        if score > 0:
            covered = frozenset(w for w in own if _covered(w, row_words))
            scored.append((score, child, covered))
    if not scored:
        return []
    scored.sort(key=lambda item: (-item[0], item[1].id))
    # Several fully named subprojects: the row names them all ("Knoten Riesa
    # inkl. Röderau – Zeithain"). One whose words are a part of another's
    # ("Schönebeck – Halle" next to "Glindenberg – Schönebeck") drops out.
    full = [item for item in scored if item[0] >= 0.95]
    full = [item for item in full if not any(item[2] < other[2] for other in full)]
    chosen = full or scored[:1]
    chosen_ids = {c.id for _, c, _ in chosen}
    lineage = set().union(*(index.ancestors(i) for i in chosen_ids))
    rest = [
        score for score, c, covered in scored
        if c.id not in chosen_ids and c.id not in lineage
        and not any(covered < other for _, _, other in chosen)
    ]
    accepted = chosen[0][0] >= 0.6 and (not rest or rest[0] <= _AMBIGUOUS)
    return [(score, c) for score, c, _ in chosen] if accepted else []


def suggest_rows(
    rows: Iterable[dict[str, Any]],
    projects: list[ProjectRef],
    previous: PreviousYear | dict[str, list[int]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Suggestions per ``row_key``: ``[{project_id, confidence, reason, …}]``,
    strongest first. ``previous`` may be a plain ``{primary_number: [ids]}``."""
    if previous is None:
        previous = PreviousYear()
    elif not isinstance(previous, PreviousYear):
        previous = PreviousYear.from_numbers(previous)
    index = _Index(projects)

    out: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        found: dict[int, dict[str, Any]] = {}

        def add(project_id: int, confidence: float, reason: str, **extra: Any) -> None:
            if project_id not in index.by_id:
                return
            current = found.get(project_id)
            candidate = {"project_id": project_id, "confidence": round(confidence, 2), "reason": reason}
            candidate.update({k: v for k, v in extra.items() if v not in (None, "")})
            if current is None or (candidate["confidence"], -_REASON_RANK[reason]) > (
                current["confidence"],
                -_REASON_RANK[current["reason"]],
            ):
                found[project_id] = candidate

        number = row.get("primary_number")
        for link in previous.by_number.get(number or "", []):
            add(link.project_id, 1.0, REASON_NUMBER, previous_year=previous.years.get(f"n:{number}"),
                previous_note=link.note)
        text_key = row_text_key(row)
        for link in previous.by_text.get(text_key or "", []):
            add(link.project_id, CONF_PREVIOUS_TEXT, REASON_PREVIOUS_YEAR,
                previous_year=previous.years.get(f"t:{text_key}"), previous_note=link.note)
        if str(row.get("section", "")).startswith("GVFG"):
            key = normalize_key(number)
            for project in index.by_gvfg_key.get(key or "", []):
                add(project.id, 1.0, REASON_GVFG_KEY)
        for project in index.by_number.get(_number_key(number) or "", []):
            add(project.id, 1.0, REASON_NUMBER, detail="Projektnummer")
        row_ids = {
            i for i in identifiers(f"{row.get('bezeichnung') or ''} {row.get('massnahme') or ''}")
            if i.startswith("DT")
        }
        # "Elektrifizierung … inkl. DT 2 …": the DT measure is a part of the row,
        # not the row — a suggestion next to the main measure, not a match.
        alias_confidence = CONF_ALIAS_PART if _has_main_measure(row.get("massnahme")) else 1.0
        for ident in sorted(row_ids):
            for project in index.by_identifier.get(ident, []):
                add(project.id, alias_confidence, REASON_ALIAS, detail=ident)
        context = _context(row, index)
        for confidence, project, detail in context:
            add(project.id, confidence, REASON_CONTEXT, detail=detail)
        for score, project in _fuzzy(row, index, projects, has_context=bool(context)):
            add(project.id, score, REASON_FUZZY)
        suggestions = sorted(
            found.values(),
            key=lambda s: (-s["confidence"], _REASON_RANK[s["reason"]], s["project_id"]),
        )
        out[row["row_key"]] = suggestions[:_MAX_SUGGESTIONS]
    return out


def preselection(suggestions: list[dict[str, Any]], min_confidence: float) -> tuple[list[int], str | None]:
    """Projects to assign from suggestions at or above the threshold: every
    number/key/previous-year hit; else every alias and context hit; else the
    best fuzzy hit. Returns (ids, source)."""
    sure = [s for s in suggestions if s["confidence"] >= min_confidence]
    definite = [s["project_id"] for s in sure if s["reason"] in _DEFINITE_REASONS]
    if definite:
        return definite, "NUMBER"
    named = [s for s in sure if s["reason"] in (REASON_ALIAS, REASON_CONTEXT)]
    if named:
        source = "NUMBER" if any(s["reason"] == REASON_ALIAS for s in named) else "FUZZY"
        return [s["project_id"] for s in named], source
    fuzzy = [s for s in sure if s["reason"] == REASON_FUZZY]
    if fuzzy:
        return [fuzzy[0]["project_id"]], "FUZZY"
    return [], None


def preselection_note(suggestions: list[dict[str, Any]], project_ids: list[int]) -> str | None:
    """Why the preselected projects were chosen, for ``assignment_note``: the
    note of the previous year's assignment, else the context/alias detail."""
    notes: list[str] = []
    for s in suggestions:
        if s["project_id"] not in project_ids:
            continue
        if s.get("previous_note"):
            year = s.get("previous_year")
            notes.append(f"Vorjahr {year}: {s['previous_note']}" if year else s["previous_note"])
        elif s["reason"] in (REASON_CONTEXT, REASON_ALIAS) and s.get("detail"):
            notes.append(s["detail"])
    return "; ".join(dict.fromkeys(notes)) or None


# --- DB loaders ----------------------------------------------------------------


def load_projects(db: Session) -> list[ProjectRef]:
    return [
        ProjectRef(pid, name or "", superior, number, tuple(aliases or ()), description)
        for pid, name, superior, number, aliases, description in db.execute(
            select(
                Project.id,
                Project.name,
                Project.superior_project_id,
                Project.project_number,
                Project.aliases,
                Project.description,
            )
        )
    ]


def previous_year(db: Session, before_year: int) -> PreviousYear:
    """Confirmed links before ``before_year``, by ``primary_number`` and by row
    text; each key from the newest year that has it, with the link's note."""
    entries = db.execute(
        select(InfraplanEntry, InfraplanReport.year, InfraplanEntryProject.project_id, InfraplanEntryProject.note)
        .join(InfraplanReport, InfraplanReport.id == InfraplanEntry.report_id)
        .join(InfraplanEntryProject, InfraplanEntryProject.entry_id == InfraplanEntry.id)
        .where(InfraplanReport.year < before_year)
    ).all()
    result = PreviousYear()
    for entry, year, project_id, note in sorted(entries, key=lambda r: (-r[1], r[0].id)):
        for prefix, key, target in (
            ("n", entry.primary_number, result.by_number),
            ("t", row_text_key(entry), result.by_text),
        ):
            if not key:
                continue
            if result.years.setdefault(f"{prefix}:{key}", year) != year:
                continue
            links = target.setdefault(key, [])
            if all(link.project_id != project_id for link in links):
                links.append(PreviousLink(project_id, note))
    return result


def previous_links(db: Session, before_year: int) -> dict[str, list[int]]:
    """``primary_number`` → projects linked in the newest confirmed year before
    ``before_year`` that carries this number."""
    return {
        number: [link.project_id for link in links]
        for number, links in previous_year(db, before_year).by_number.items()
    }


def suggestions_for_draft(db: Session, rows: list[dict[str, Any]], year: int) -> dict[str, list[dict[str, Any]]]:
    return suggest_rows(rows, load_projects(db), previous_year(db, year))
