"""Consistency checks over the project list (MCP ``check_project_data``).

See docs/features/feature-infraplan-import.md → "Datenqualität". Each check
returns findings, never fixes anything: duplicated numbers and names are
sometimes intended (collective numbers like "L 27"), so a person decides.
The functions are pure; :func:`run_checks` takes plain records.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

from dashboard_backend.services.gvfg_parser import LAND_BY_CODE, normalize_key
from dashboard_backend.tasks.infraplan_matching import is_unnamed_subproject, normalize_text

CHECKS = ("duplicate_number", "duplicate_sibling_name", "gvfg_land_mismatch", "unnamed_subproject")

# Short names of the Länder as used in group names ("GVFG BW").
LAND_BY_ABBREVIATION = {
    "SH": "Schleswig-Holstein",
    "HH": "Hamburg",
    "NI": "Niedersachsen",
    "HB": "Bremen",
    "NW": "Nordrhein-Westfalen",
    "NRW": "Nordrhein-Westfalen",
    "HE": "Hessen",
    "RP": "Rheinland-Pfalz",
    "RLP": "Rheinland-Pfalz",
    "BW": "Baden-Württemberg",
    "BY": "Bayern",
    "SL": "Saarland",
    "BE": "Berlin",
    "BB": "Brandenburg",
    "MV": "Mecklenburg-Vorpommern",
    "SN": "Sachsen",
    "ST": "Sachsen-Anhalt",
    "TH": "Thüringen",
}
_GROUP_LAND = re.compile(r"^GVFG\s+([A-Z]{2,3})$")


@dataclass
class ProjectRecord:
    id: int
    name: str
    project_number: str | None = None
    superior_project_id: int | None = None
    description: str | None = None
    is_draft: bool = False
    groups: list[str] = field(default_factory=list)
    # (key, land) of the GVFG Vorhaben linked to the project
    gvfg_entries: list[tuple[str, str]] = field(default_factory=list)
    # (year, row_key, primary_number, laender) of the Infraplan entries linked to it
    infraplan_entries: list[tuple[int, str, str | None, str | None]] = field(default_factory=list)


def _ref(project: ProjectRecord) -> dict[str, Any]:
    return {"id": project.id, "name": project.name, "project_number": project.project_number}


def _number_key(number: str | None) -> str | None:
    if not number or not number.strip():
        return None
    return re.sub(r"\s+", " ", number.strip()).lower()


def duplicate_numbers(projects: Iterable[ProjectRecord]) -> list[dict[str, Any]]:
    """The same project number on several projects."""
    groups: dict[str, list[ProjectRecord]] = defaultdict(list)
    for project in projects:
        key = _number_key(project.project_number)
        if key:
            groups[key].append(project)
    return [
        {"project_number": members[0].project_number, "projects": [_ref(p) for p in members]}
        for _, members in sorted(groups.items())
        if len(members) > 1
    ]


def duplicate_sibling_names(projects: Iterable[ProjectRecord]) -> list[dict[str, Any]]:
    """Projects with the same name under the same superior project."""
    groups: dict[tuple[int, str], list[ProjectRecord]] = defaultdict(list)
    for project in projects:
        if project.superior_project_id is not None:
            groups[(project.superior_project_id, normalize_text(project.name))].append(project)
    return [
        {"superior_project_id": superior, "name": members[0].name, "projects": [_ref(p) for p in members]}
        for (superior, _), members in sorted(groups.items())
        if len(members) > 1
    ]


def _land_of_key(key: str) -> str | None:
    return LAND_BY_CODE.get(key[:2])


def gvfg_land_mismatches(projects: Iterable[ProjectRecord]) -> list[dict[str, Any]]:
    """GVFG keys in ``project_number`` whose Land code does not fit the Land
    of the project: its group "GVFG <Land>", its GVFG Vorhaben, or a linked
    Infraplan row whose key differs only in the Land code."""
    findings = []
    for project in projects:
        key = normalize_key(project.project_number)
        if not key:
            continue
        land = _land_of_key(key)
        reasons: list[str] = []
        for group in project.groups:
            match = _GROUP_LAND.match(group or "")
            expected = LAND_BY_ABBREVIATION.get(match.group(1)) if match else None
            if expected and expected != land:
                reasons.append(f"Projektgruppe „{group}“ ({expected})")
        for entry_key, entry_land in project.gvfg_entries:
            if entry_land and entry_land != land:
                reasons.append(f"GVFG-Vorhaben {entry_key} ({entry_land})")
        for year, row_key, number, laender in project.infraplan_entries:
            row_key_norm = normalize_key(number)
            if row_key_norm and row_key_norm != key and row_key_norm[2:] == key[2:]:
                reasons.append(
                    f"Infraplan {year} {row_key}: {row_key_norm} ({_land_of_key(row_key_norm) or laender})"
                )
        if reasons:
            findings.append({**_ref(project), "land_of_number": land, "reasons": reasons})
    return findings


def unnamed_subprojects(projects: Iterable[ProjectRecord]) -> list[dict[str, Any]]:
    """Subprojects whose name says no more than "Teilmaßnahme 3" beyond the
    name of their superior."""
    projects = list(projects)
    by_id = {p.id: p for p in projects}
    findings = []
    for project in projects:
        superior = by_id.get(project.superior_project_id)
        if superior is None:
            continue
        if is_unnamed_subproject(project.name, superior.name):
            findings.append(
                {
                    **_ref(project),
                    "superior_project_id": superior.id,
                    "superior_name": superior.name,
                    "has_description": bool((project.description or "").strip()),
                }
            )
    return findings


_RUNNERS = {
    "duplicate_number": duplicate_numbers,
    "duplicate_sibling_name": duplicate_sibling_names,
    "gvfg_land_mismatch": gvfg_land_mismatches,
    "unnamed_subproject": unnamed_subprojects,
}


def run_checks(projects: list[ProjectRecord], checks: Iterable[str] = CHECKS) -> dict[str, list[dict[str, Any]]]:
    return {check: _RUNNERS[check](projects) for check in checks}
