from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .users import User


class ApiKey(Base):
    """Personal API key (``Authorization: Bearer rdb_<prefix>_<secret>``).

    Only the SHA-256 hash of the secret is stored; the full token is shown once
    on creation. A key acts as its owner, narrowed to ``scopes`` when set.
    Revoked keys keep their row for traceability.
    """

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    prefix: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # NULL = every capability of the owner; otherwise the intersection with it.
    scopes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(lazy="joined")

    def is_active(self, now: datetime) -> bool:
        if self.revoked_at is not None:
            return False
        return self.expires_at is None or self.expires_at > now
