from sqlalchemy import Column, Integer, String
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
