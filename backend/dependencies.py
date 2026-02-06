from typing import Generator
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import inspect, text

from backend.database import get_engine, get_session_maker, Base
from backend.config import Settings


def migrate_add_pinned_column(engine) -> None:
    """Add pinned column to conversations table if it doesn't exist (idempotent)."""
    inspector = inspect(engine)
    # Check if conversations table exists first
    if "conversations" not in inspector.get_table_names():
        return
    columns = [c["name"] for c in inspector.get_columns("conversations")]
    if "pinned" not in columns:
        with engine.connect() as conn:
            conn.execute(
                text("ALTER TABLE conversations ADD COLUMN pinned BOOLEAN DEFAULT 0 NOT NULL")
            )
            conn.commit()


def migrate_add_knowledge_vault_columns(engine) -> None:
    """Add document_scope and persona_id columns to conversations (idempotent)."""
    inspector = inspect(engine)

    # Check if conversations table exists first
    if "conversations" not in inspector.get_table_names():
        return

    columns = [c["name"] for c in inspector.get_columns("conversations")]

    with engine.connect() as conn:
        if "document_scope" not in columns:
            conn.execute(
                text("ALTER TABLE conversations ADD COLUMN document_scope TEXT")
            )
        if "persona_id" not in columns:
            conn.execute(
                text("ALTER TABLE conversations ADD COLUMN persona_id INTEGER")
            )
        conn.commit()


settings = Settings()
engine = get_engine(settings.database_url)
SessionLocal = get_session_maker(engine)

# Create tables
Base.metadata.create_all(bind=engine)

# Run migrations
migrate_add_pinned_column(engine)
migrate_add_knowledge_vault_columns(engine)


def get_db() -> Generator[DBSession, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
