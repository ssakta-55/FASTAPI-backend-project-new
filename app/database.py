from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

# SQLite needs this flag because FastAPI may use different threads.
connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_db():
    """Open a DB session for one request and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
