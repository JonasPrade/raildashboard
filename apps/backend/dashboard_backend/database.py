from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dashboard_backend.core.config import settings

# Pool tuning: the defaults (5 connections, 10 overflow, no liveness check) let
# a burst of parallel requests queue up behind five connections and let a
# connection that the database or a proxy closed in the background surface as a
# failed request. ``pool_pre_ping`` swaps such a connection out transparently,
# ``pool_recycle`` retires connections before an idle timeout can hit them.
# SQLite (test suite) does not use a queue pool, so the sizing args are skipped.
_engine_kwargs: dict = {"pool_pre_ping": True}
if not settings.database_url.startswith("sqlite"):
    _engine_kwargs.update(
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle_seconds,
    )

engine = create_engine(settings.database_url, **_engine_kwargs)
Session = sessionmaker(autocommit=False, bind=engine)

def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
