from typing import Generator
from sqlalchemy.orm import Session as DBSession

from backend.database import get_engine, get_session_maker, Base
from backend.config import Settings

settings = Settings()
engine = get_engine(settings.database_url)
SessionLocal = get_session_maker(engine)

# Create tables
Base.metadata.create_all(bind=engine)


def get_db() -> Generator[DBSession, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
