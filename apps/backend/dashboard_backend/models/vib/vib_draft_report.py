from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from dashboard_backend.models.base import Base


class VibDraftReport(Base):
    """Stores the raw VIB parse result in the DB immediately after the Celery task
    completes — before the user reviews/corrects and confirms the import.

    This ensures the parse result survives Redis eviction and allows the user
    to resume a review session without re-uploading the PDF.
    """

    __tablename__ = "vib_draft_report"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(200), unique=True, nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    # Full VibParseTaskResult serialised as JSON string
    raw_result_json = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    created_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # OCR extraction fields — populated by parse_vib_pdf when OCR is used
    ocr_raw_text = Column(Text, nullable=True)       # full OCR text before block-splitting
    ocr_status = Column(String(20), nullable=True)   # "done" | "fallback" | "failed"
    ocr_model = Column(String(100), nullable=True)   # e.g. "mistral-ocr-2512" or "pymupdf"
    ocr_images_json = Column(Text, nullable=True)    # JSON list of {page_index, id, image_base64}

    created_by = relationship("User", foreign_keys=[created_by_user_id])
