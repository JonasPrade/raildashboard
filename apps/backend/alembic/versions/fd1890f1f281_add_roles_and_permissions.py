"""add roles and permissions

Revision ID: fd1890f1f281
Revises: f77c3078826f
Create Date: 2026-06-17 14:46:28.355985

Introduces the ``roles`` / ``role_permissions`` tables and replaces the
``users.role`` string column with a ``users.role_id`` foreign key. The three
historic roles (viewer/editor/admin) are seeded as system roles with the
permission sets that reproduce today's behaviour, and existing users are
backfilled by matching their old role name.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fd1890f1f281'
down_revision: Union[str, None] = 'f77c3078826f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Editor capability set — a point-in-time snapshot derived from the historic
# ``editor|admin`` gates. The ``admin`` role is an implicit super-admin and
# therefore needs no explicit permission rows.
_EDITOR_PERMISSIONS = (
    "project.create",
    "project.edit",
    "project.delete",
    "haushalt.import",
    "vib.import",
    "finve.edit",
    "projecttext.edit",
    "assignment.manage",
)


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_roles_id"), "roles", ["id"], unique=False)
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_key", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_key"),
    )

    # Seed the three system roles.
    op.execute(
        sa.text(
            """
            INSERT INTO roles (name, description, is_system, created_at) VALUES
            ('viewer', 'Nur Lesezugriff', true, now()),
            ('editor', 'Bearbeitung von Projekten, Importen und Inhalten', true, now()),
            ('admin', 'Voller Zugriff (Super-Admin)', true, now())
            """
        )
    )

    # Seed the editor permission rows.
    editor_values = ", ".join(f"('{key}')" for key in _EDITOR_PERMISSIONS)
    op.execute(
        sa.text(
            f"""
            INSERT INTO role_permissions (role_id, permission_key)
            SELECT r.id, k.permission_key
            FROM roles r
            JOIN (VALUES {editor_values}) AS k(permission_key) ON true
            WHERE r.name = 'editor'
            """
        )
    )

    # Replace users.role (string) with users.role_id (FK), backfilling by name.
    op.add_column("users", sa.Column("role_id", sa.Integer(), nullable=True))
    op.execute(
        sa.text("UPDATE users SET role_id = roles.id FROM roles WHERE roles.name = users.role")
    )
    # Defensive: any unmatched legacy role falls back to viewer.
    op.execute(
        sa.text(
            "UPDATE users SET role_id = (SELECT id FROM roles WHERE name = 'viewer') "
            "WHERE role_id IS NULL"
        )
    )
    op.alter_column("users", "role_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key("fk_users_role_id_roles", "users", "roles", ["role_id"], ["id"])
    op.drop_column("users", "role")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
            server_default="viewer",
        ),
    )
    op.execute(
        sa.text("UPDATE users SET role = roles.name FROM roles WHERE roles.id = users.role_id")
    )
    op.drop_constraint("fk_users_role_id_roles", "users", type_="foreignkey")
    op.drop_column("users", "role_id")
    op.drop_table("role_permissions")
    op.drop_index(op.f("ix_roles_id"), table_name="roles")
    op.drop_table("roles")
