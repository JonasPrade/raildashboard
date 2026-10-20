"""Project suggestions for Infraplan rows (stage 4 of the parse pipeline).

See docs/features/feature-infraplan-import.md → "Zuordnung zu Projekten".
Order per row:

1. **Project number of an earlier year** — the confirmed links of the newest
   earlier year with the same ``primary_number`` (confidence 1.0).
2. **GVFG key** — GVFG rows against ``Project.project_number`` with the same
   normaliser as the GVFG import (counts like a number hit, 1.0).
3. **Fuzzy** over ``Bezeichnung`` and ``Maßnahme`` (``vib_matching._score``,
   prefix ``PB nn:`` removed). A matching subproject replaces its superior.

Rows with a suggestion of at least ``PRESELECT_CONFIDENCE`` are preselected.
The pure part (:func:`suggest_rows`) has no DB access.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
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
from dashboard_backend.tasks.vib_matching import _normalize, _score

PRESELECT_CONFIDENCE = 0.85
_FUZZY_THRESHOLD = 0.5
_MAX_FUZZY = 3
# Tokens shorter than this ("bf", "abs", "und") say nothing about a project.
_MIN_TOKEN = 4

_PB_PREFIX = re.compile(r"^\s*PB\s*\d+[a-z]?\s*:\s*", re.IGNORECASE)

# Reasons of a suggestion; NUMBER and GVFG_KEY are stored as source NUMBER.
REASON_NUMBER = "NUMBER"
REASON_GVFG_KEY = "GVFG_KEY"
REASON_FUZZY = "FUZZY"


@dataclass(frozen=True)
class ProjectRef:
    id: int
    name: str
    superior_project_id: int | None = None
    project_number: str | None = None


def strip_pb_prefix(text: str | None) -> str:
    return _PB_PREFIX.sub("", text or "").strip()


def _tokens(text: str) -> set[str]:
    return {t for t in _normalize(text).split() if len(t) >= _MIN_TOKEN}


def _row_texts(row: dict[str, Any]) -> list[str]:
    bezeichnung = strip_pb_prefix(row.get("bezeichnung"))
    massnahme = (row.get("massnahme") or "").strip()
    texts = [t for t in (bezeichnung, massnahme) if t]
    if bezeichnung and massnahme:
        texts.append(f"{bezeichnung} {massnahme}")
    return texts


def _fuzzy(
    row: dict[str, Any], projects: list[ProjectRef], tokens: dict[int, set[str]]
) -> list[tuple[float, ProjectRef]]:
    texts = _row_texts(row)
    if not texts:
        return []
    row_tokens = set().union(*(_tokens(t) for t in texts))
    scored: list[tuple[float, ProjectRef]] = []
    for project in projects:
        # Cheap prefilter: without one shared significant word the
        # SequenceMatcher would only find accidental similarity.
        if not row_tokens & tokens[project.id]:
            continue
        score = max(_score(text, project.name) for text in texts)
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


def suggest_rows(
    rows: Iterable[dict[str, Any]],
    projects: list[ProjectRef],
    previous_links: dict[str, list[int]],
) -> dict[str, list[dict[str, Any]]]:
    """Suggestions per ``row_key``: ``[{project_id, confidence, reason}]``,
    strongest first."""
    by_id = {p.id: p for p in projects}
    by_gvfg_key: dict[str, list[ProjectRef]] = defaultdict(list)
    for project in projects:
        key = normalize_key(project.project_number)
        if key:
            by_gvfg_key[key].append(project)
    tokens = {p.id: _tokens(p.name) for p in projects}

    out: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        suggestions: list[dict[str, Any]] = []
        seen: set[int] = set()

        def add(project_id: int, confidence: float, reason: str) -> None:
            if project_id in seen or project_id not in by_id:
                return
            seen.add(project_id)
            suggestions.append(
                {"project_id": project_id, "confidence": round(confidence, 2), "reason": reason}
            )

        number = row.get("primary_number")
        for project_id in previous_links.get(number or "", []):
            add(project_id, 1.0, REASON_NUMBER)
        if str(row.get("section", "")).startswith("GVFG"):
            key = normalize_key(number)
            for project in by_gvfg_key.get(key or "", []):
                add(project.id, 1.0, REASON_GVFG_KEY)
        for score, project in _fuzzy(row, projects, tokens):
            add(project.id, score, REASON_FUZZY)
        out[row["row_key"]] = suggestions
    return out


def preselection(suggestions: list[dict[str, Any]], min_confidence: float) -> tuple[list[int], str | None]:
    """Projects to assign from suggestions: every number/key hit at or above
    the threshold, otherwise the best fuzzy hit. Returns (ids, source)."""
    strong = [
        s["project_id"]
        for s in suggestions
        if s["reason"] != REASON_FUZZY and s["confidence"] >= min_confidence
    ]
    if strong:
        return strong, "NUMBER"
    fuzzy = [s for s in suggestions if s["reason"] == REASON_FUZZY and s["confidence"] >= min_confidence]
    if fuzzy:
        return [fuzzy[0]["project_id"]], "FUZZY"
    return [], None


# --- DB loaders ----------------------------------------------------------------


def load_projects(db: Session) -> list[ProjectRef]:
    return [
        ProjectRef(pid, name or "", superior, number)
        for pid, name, superior, number in db.execute(
            select(Project.id, Project.name, Project.superior_project_id, Project.project_number)
        )
    ]


def previous_links(db: Session, before_year: int) -> dict[str, list[int]]:
    """``primary_number`` → projects linked in the newest confirmed year before
    ``before_year`` that carries this number."""
    rows = db.execute(
        select(InfraplanEntry.primary_number, InfraplanReport.year, InfraplanEntryProject.project_id)
        .join(InfraplanReport, InfraplanReport.id == InfraplanEntry.report_id)
        .join(InfraplanEntryProject, InfraplanEntryProject.entry_id == InfraplanEntry.id)
        .where(InfraplanEntry.primary_number.isnot(None), InfraplanReport.year < before_year)
    ).all()
    newest: dict[str, int] = {}
    links: dict[str, list[int]] = defaultdict(list)
    for number, year, project_id in sorted(rows, key=lambda r: -r[1]):
        if newest.setdefault(number, year) == year and project_id not in links[number]:
            links[number].append(project_id)
    return dict(links)


def suggestions_for_draft(db: Session, rows: list[dict[str, Any]], year: int) -> dict[str, list[dict[str, Any]]]:
    return suggest_rows(rows, load_projects(db), previous_links(db, year))
