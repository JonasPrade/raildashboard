from __future__ import annotations

from sqlalchemy.orm import Session

from dashboard_backend.models.projects.text_attachment import TextAttachment


def create_text_attachment(
    db: Session,
    text_id: int,
    filename: str,
    stored_filename: str,
    mime_type: str,
    file_size: int,
    user_id: int | None,
) -> TextAttachment:
    attachment = TextAttachment(
        text_id=text_id,
        filename=filename,
        stored_filename=stored_filename,
        mime_type=mime_type,
        file_size=file_size,
        uploaded_by_user_id=user_id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def get_text_attachments(db: Session, text_id: int) -> list[TextAttachment]:
    return db.query(TextAttachment).filter(TextAttachment.text_id == text_id).all()


def get_text_attachment(db: Session, attachment_id: int) -> TextAttachment | None:
    return db.query(TextAttachment).filter(TextAttachment.id == attachment_id).first()


def delete_text_attachment(db: Session, attachment_id: int) -> bool:
    attachment = db.query(TextAttachment).filter(TextAttachment.id == attachment_id).first()
    if not attachment:
        return False
    db.delete(attachment)
    db.commit()
    return True
