from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from dashboard_backend.models.base import Base


class TextAttachment(Base):
    __tablename__ = "text_attachment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text_id = Column(Integer, ForeignKey("project_text.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)          # original name shown to user
    stored_filename = Column(String(255), nullable=False)   # UUID-based name on disk
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)             # bytes
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    text = relationship("ProjectText", back_populates="attachments")

    def __repr__(self) -> str:
        return f"<TextAttachment(id={self.id}, filename='{self.filename}', text_id={self.text_id})>"
