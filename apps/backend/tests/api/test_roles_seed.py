"""Phase 1 acceptance: the seeded system roles reproduce the historic
viewer/editor/admin behaviour 1:1, and the admin role bypasses the permission
check. Mirrors what the database migration backfill must guarantee.
"""

from __future__ import annotations

from dashboard_backend.core.permissions import all_permission_keys
from dashboard_backend.crud import roles as roles_crud
from dashboard_backend.schemas.users import UserRole


EDITOR_KEYS = {
    "project.create",
    "project.edit",
    "project.delete",
    "haushalt.import",
    "vib.import",
    "finve.edit",
    "projecttext.edit",
    "assignment.manage",
    "progress.edit",
    "todo.create",
    "todo.edit",
    "todo.delete",
}

ADMIN_ONLY_KEYS = {"projectgroup.create", "projectgroup.edit", "user.manage", "role.manage", "settings.manage"}


def test_system_roles_are_seeded(db_session):
    for name in ("viewer", "editor", "admin"):
        role = roles_crud.get_role_by_name(db_session, name)
        assert role is not None
        assert role.is_system is True


def test_viewer_has_no_permissions(create_user):
    viewer = create_user("viewer-user", "password123", UserRole.viewer)
    assert viewer.effective_permissions == set()
    assert viewer.has_permission("project.edit") is False


def test_editor_reproduces_historic_capabilities(create_user):
    editor = create_user("editor-user", "password123", UserRole.editor)
    assert editor.effective_permissions == EDITOR_KEYS
    for key in EDITOR_KEYS:
        assert editor.has_permission(key) is True
    # Editor must NOT hold the admin-only capabilities.
    for key in ADMIN_ONLY_KEYS:
        assert editor.has_permission(key) is False


def test_admin_is_implicit_superadmin(create_user):
    admin = create_user("admin-user", "password123", UserRole.admin)
    assert admin.effective_permissions == set(all_permission_keys())
    for key in all_permission_keys():
        assert admin.has_permission(key) is True
    # Even an unknown/future key is granted via the bypass.
    assert admin.has_permission("something.new") is True
