from sqlalchemy import Column, Integer, String, Text
from dashboard_backend.models.base import Base


class AppSettings(Base):
    """Singleton settings row (always id=1)."""
    __tablename__ = 'app_settings'

    id = Column(Integer, primary_key=True, default=1)
    map_group_mode = Column(
        String(20),
        nullable=False,
        default='preconfigured',
        comment="'preconfigured' = use is_default_selected groups; 'all' = show all projects without group filter",
    )
    # Legal pages (Impressum, Datenschutz): URL set → footer link and route go
    # outside; otherwise the Markdown is rendered on /impressum or /datenschutz.
    impressum_url = Column(String(500), nullable=True)
    impressum_markdown = Column(Text, nullable=True)
    datenschutz_url = Column(String(500), nullable=True)
    datenschutz_markdown = Column(Text, nullable=True)
