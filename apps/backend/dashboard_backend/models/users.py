from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard_backend.core.permissions import effective_permissions_for, is_superadmin_role

from .base import Base
from .roles import Role


class User(Base):
    """Persisted application user with role based access permissions."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    role: Mapped[Role] = relationship(back_populates="users", lazy="joined")

    @property
    def role_name(self) -> str | None:
        return self.role.name if self.role is not None else None

    @property
    def effective_permissions(self) -> set[str]:
        """Resolve the user's capability keys (admin → every catalog key)."""

        if self.role is None:
            return set()
        return effective_permissions_for(self.role.name, self.role.permission_keys)

    @property
    def permissions(self) -> list[str]:
        """Effective capability keys as a stable, serialisable list."""

        return sorted(self.effective_permissions)

    def has_permission(self, key: str) -> bool:
        """Whether the user holds a capability (admin bypasses the check)."""

        if self.role is not None and is_superadmin_role(self.role.name):
            return True
        return key in self.effective_permissions
