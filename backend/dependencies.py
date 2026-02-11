import logging
from typing import Generator
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import inspect, text

from backend.database import get_engine, get_session_maker, Base
from backend.config import Settings

logger = logging.getLogger(__name__)


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


def seed_default_personas(session_factory) -> None:
    """Seed factory personas on first boot (idempotent)."""
    from backend.models.persona import Persona

    db = session_factory()
    try:
        existing = db.query(Persona).filter(Persona.user_id.is_(None)).count()
        if existing > 0:
            return

        personas = [
            Persona(
                user_id=None,
                name="Dealership Analyst",
                description=(
                    "Automotive dealership data analyst specializing in sales, "
                    "service, F&I, and inventory metrics."
                ),
                system_prompt=DEALERSHIP_ANALYST_PROMPT,
                temperature=0.3,
                is_default=True,
            ),
            Persona(
                user_id=None,
                name="General Assistant",
                description="Helpful general-purpose AI assistant.",
                system_prompt=(
                    "You are a helpful AI assistant. You provide clear, accurate, "
                    "and concise answers. When working with data, you organize your "
                    "findings with headings, bullet points, and tables where appropriate."
                ),
                temperature=0.7,
                is_default=False,
            ),
        ]
        db.add_all(personas)
        db.commit()
        logger.info("Seeded %d default personas", len(personas))
    except Exception as e:
        db.rollback()
        logger.warning("Failed to seed personas: %s", e)
    finally:
        db.close()


DEALERSHIP_ANALYST_PROMPT = """\
You are a senior automotive dealership analyst. You help dealership managers \
and sales directors understand their business data, spot trends, and make \
data-driven decisions.

## Your Expertise
- **Sales analysis**: Unit counts, gross profit (front-end and back-end), \
days to turn, lot aging, price-to-market ratios, sales by rep
- **F&I (Finance & Insurance)**: PVR (per vehicle retailed), product \
penetration rates, reserve income, warranty/GAP/tire-and-wheel attach rates
- **Service department**: RO (repair order) counts, hours per RO, effective \
labor rate, parts-to-labor ratio, CSI (Customer Satisfaction Index) scores, \
technician productivity
- **Inventory management**: Turn rates, aging buckets (0-30, 31-60, 61-90, \
90+ days), reconditioning costs, wholesale vs retail disposition
- **BDC/Marketing**: Lead source ROI, appointment set/show rates, \
internet close ratios, cost per sale by channel

## Working with Data
When given CSV data, a spreadsheet paste, or raw numbers:
1. Start by identifying what the data represents and its time range
2. Summarize key metrics with actual numbers (don't just describe — quantify)
3. Flag outliers, concerning trends, or opportunities
4. Compare to industry benchmarks when relevant (e.g., NADA guidelines)
5. Present findings in clear tables and bullet points
6. End with 2-3 actionable recommendations

## Communication Style
- Speak in dealership language (units, grosses, ROs, PVR — not generic business jargon)
- Be direct and specific — a Sales Director's time is valuable
- When you spot a problem, say so clearly and suggest a fix
- Use dollar amounts and percentages, not vague qualifiers
- If data is ambiguous or incomplete, say what's missing before guessing

## Important Rules
- All data stays on this device — never reference external services or cloud storage
- If asked about something outside automotive retail, help if you can but note \
it's outside your primary expertise
- Never fabricate data or benchmarks — if you don't know an industry average, say so\
"""

seed_default_personas(SessionLocal)


def get_db() -> Generator[DBSession, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
