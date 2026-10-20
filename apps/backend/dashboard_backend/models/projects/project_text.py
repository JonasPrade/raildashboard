from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey, true
from sqlalchemy.orm import relationship
from dashboard_backend.models.base import Base


class ProjectText(Base):
    __tablename__ = 'project_text'
    id = Column(Integer, primary_key=True, autoincrement=True)
    header = Column(String(100), nullable=False)
    weblink = Column(String(1000), nullable=True)
    text = Column(Text, nullable=True)
    type = Column(Integer, ForeignKey('project_text_type.id'), nullable=False)
    logo_url = Column(String(1000), nullable=True)
    # Nullable for expand/contract: code from before categories inserts without it.
    category_id = Column(Integer, ForeignKey('project_text_category.id'), nullable=True)
    # False = only delivered to signed-in users.
    is_public = Column(Boolean, nullable=False, default=True, server_default=true())

    created_at = Column(Integer, nullable=False, default=0)
    updated_at = Column(Integer, nullable=False, default=0)

    text_type = relationship("ProjectTextType", backref="project_texts")
    category = relationship("ProjectTextCategory")
    attachments = relationship("TextAttachment", back_populates="text", cascade="all, delete-orphan")
    # projects = relationship("ProjectTextType", backref="texts", lazy=True)

    def __repr__(self):
        return f"<ProjectText(id={self.id}, header='{self.header}', type={self.type})>"
