from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()


def get_engine(database_url: str = "sqlite:///./data/gantry.db"):
    return create_engine(database_url, connect_args={"check_same_thread": False})


def get_session_maker(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
