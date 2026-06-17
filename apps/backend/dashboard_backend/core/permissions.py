"""Capability catalog for the role/permission system.

The catalog lives in code (not the database): ``role_permissions.permission_key``
rows reference these keys. New capabilities are added here without a data
migration; unknown keys found in the database are ignored when computing a
user's effective permissions.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


# Capability group labels (German, shown in the admin UI).
GROUP_PROJECTS = "Projekte"
GROUP_PROJECT_GROUPS = "Projektgruppen"
GROUP_FINANCING = "Finanzierung"
GROUP_CONTENT = "Inhalte"
GROUP_ADMINISTRATION = "Administration"


@dataclass(frozen=True)
class Permission:
    key: str
    label: str
    group: str


# Initial catalog, derived from the historic role-based gates.
PERMISSIONS: tuple[Permission, ...] = (
    Permission("project.create", "Projekte anlegen", GROUP_PROJECTS),
    Permission("project.edit", "Projekte bearbeiten", GROUP_PROJECTS),
    Permission("project.delete", "Projekte löschen", GROUP_PROJECTS),
    Permission("projectgroup.create", "Projektgruppen anlegen", GROUP_PROJECT_GROUPS),
    Permission("projectgroup.edit", "Projektgruppen bearbeiten/löschen", GROUP_PROJECT_GROUPS),
    Permission("haushalt.import", "Haushaltsberichte importieren", GROUP_FINANCING),
    Permission("vib.import", "VIB importieren", GROUP_FINANCING),
    Permission("finve.edit", "Finanzierungsvereinbarungen einarbeiten", GROUP_FINANCING),
    Permission("projecttext.edit", "Projekttexte bearbeiten", GROUP_CONTENT),
    Permission("assignment.manage", "Offene Zuordnungen verwalten", GROUP_CONTENT),
    Permission("user.manage", "Nutzer verwalten", GROUP_ADMINISTRATION),
    Permission("role.manage", "Rollen & Rechte verwalten", GROUP_ADMINISTRATION),
    Permission("settings.manage", "App-Einstellungen", GROUP_ADMINISTRATION),
)

_PERMISSIONS_BY_KEY: dict[str, Permission] = {p.key: p for p in PERMISSIONS}


def all_permission_keys() -> list[str]:
    """Return every capability key in catalog order."""

    return [p.key for p in PERMISSIONS]


def is_valid_permission(key: str) -> bool:
    return key in _PERMISSIONS_BY_KEY


# --- System roles -----------------------------------------------------------
# Seeded roles that reproduce the historic viewer/editor/admin behaviour 1:1.

VIEWER_ROLE_NAME = "viewer"
EDITOR_ROLE_NAME = "editor"
ADMIN_ROLE_NAME = "admin"

SYSTEM_ROLE_NAMES: tuple[str, ...] = (VIEWER_ROLE_NAME, EDITOR_ROLE_NAME, ADMIN_ROLE_NAME)

# Editor capability set derived from the historic ``editor|admin`` gates.
_EDITOR_PERMISSIONS: frozenset[str] = frozenset(
    {
        "project.create",
        "project.edit",
        "project.delete",
        "haushalt.import",
        "vib.import",
        "finve.edit",
        "projecttext.edit",
        "assignment.manage",
    }
)

# Permission keys seeded for each system role. ``admin`` is an implicit
# super-admin (bypasses the permission check), so it needs no explicit rows.
SYSTEM_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    VIEWER_ROLE_NAME: frozenset(),
    EDITOR_ROLE_NAME: _EDITOR_PERMISSIONS,
    ADMIN_ROLE_NAME: frozenset(),
}

SYSTEM_ROLE_DESCRIPTIONS: dict[str, str] = {
    VIEWER_ROLE_NAME: "Nur Lesezugriff",
    EDITOR_ROLE_NAME: "Bearbeitung von Projekten, Importen und Inhalten",
    ADMIN_ROLE_NAME: "Voller Zugriff (Super-Admin)",
}


def is_superadmin_role(role_name: str | None) -> bool:
    """The ``admin`` system role bypasses every permission check."""

    return role_name == ADMIN_ROLE_NAME


def effective_permissions_for(role_name: str | None, role_permission_keys: Iterable[str]) -> set[str]:
    """Resolve the effective permission set for a role.

    The ``admin`` role implicitly holds every catalog capability; any other
    role holds exactly its (validated) assigned keys.
    """

    if is_superadmin_role(role_name):
        return set(all_permission_keys())
    return {key for key in role_permission_keys if is_valid_permission(key)}
