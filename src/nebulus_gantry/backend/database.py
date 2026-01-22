import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database Setup
DB_PATH = os.getenv("DB_PATH", "sqlite:///./data/gantry.db")
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    # Import entities so they are registered with Base metadata
    from .models import entities  # noqa: F401

    # Create data directory if it doesn't exist
    if "sqlite" in DB_PATH:
        db_file = DB_PATH.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(os.path.abspath(db_file)), exist_ok=True)
    Base.metadata.create_all(bind=engine)


@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
