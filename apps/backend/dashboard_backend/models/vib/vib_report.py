from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from dashboard_backend.models.base import Base


class VibReport(Base):
    __tablename__ = "vib_report"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, unique=True, nullable=False, index=True)
    drucksache_nr = Column(String(50), nullable=True)
    report_date = Column(Date, nullable=True)
    imported_at = Column(DateTime, nullable=False, server_default=func.now())
    imported_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    entries = relationship("VibEntry", back_populates="report", cascade="all, delete-orphan")
    imported_by = relationship("User", foreign_keys=[imported_by_user_id])
