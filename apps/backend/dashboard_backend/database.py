from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dashboard_backend.core.config import settings

engine = create_engine(settings.database_url)
Session = sessionmaker(autocommit=False, bind=engine)

def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
