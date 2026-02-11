"""Seed personas from JSON fixture files into the database.

Reads all JSON files from ``backend/fixtures/personas/``, creates system
personas (``user_id=None``) via :class:`PersonaService`, and skips any
persona whose name already exists.  Can be run standalone::

    python -m backend.scripts.seed_personas

Or imported and called programmatically::

    from backend.scripts.seed_personas import seed_personas
    seed_personas()
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from sqlalchemy.orm import Session as DBSession

from backend.config import settings
from backend.database import Base, get_engine, get_session_maker
from backend.models.persona import Persona
from backend.services.persona_service import PersonaService

logger = logging.getLogger(__name__)

# Resolved at import time so the module works regardless of cwd.
_DEFAULT_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "personas"


def seed_personas(
    db: DBSession | None = None,
    fixtures_dir: Path | None = None,
) -> dict[str, list[str]]:
    """Load persona fixtures and insert missing ones into the database.

    Args:
        db: An existing SQLAlchemy session.  When ``None`` a new session is
            created from :data:`backend.config.settings`.
        fixtures_dir: Directory containing ``*.json`` fixture files.  Defaults
            to ``backend/fixtures/personas/``.

    Returns:
        A dict with two keys — ``"seeded"`` and ``"skipped"`` — each
        containing a list of persona names.
    """
    own_session = False
    if db is None:
        engine = get_engine(settings.database_url)
        Base.metadata.create_all(bind=engine)
        session_maker = get_session_maker(engine)
        db = session_maker()
        own_session = True

    fixtures_dir = fixtures_dir or _DEFAULT_FIXTURES_DIR
    result: dict[str, list[str]] = {"seeded": [], "skipped": []}

    try:
        json_files = sorted(fixtures_dir.glob("*.json")) if fixtures_dir.is_dir() else []
        if not json_files:
            logger.info("No persona fixture files found in %s", fixtures_dir)
            return result

        svc = PersonaService(db)

        for filepath in json_files:
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Skipping malformed fixture %s: %s", filepath.name, exc)
                continue

            name = data.get("name")
            if not name:
                logger.warning("Skipping fixture %s: missing 'name' field", filepath.name)
                continue

            # Idempotent check — skip if a system persona with this name exists.
            existing = (
                db.query(Persona)
                .filter(Persona.name == name, Persona.user_id.is_(None))
                .first()
            )
            if existing is not None:
                logger.info("Skipped (already exists): %s", name)
                result["skipped"].append(name)
                continue

            svc.create_persona(
                user_id=None,
                name=name,
                system_prompt=data.get("system_prompt", ""),
                description=data.get("description"),
                temperature=float(data.get("temperature", 0.7)),
                model_id=data.get("model_id"),
                is_default=bool(data.get("is_default", False)),
            )
            logger.info("Seeded persona: %s", name)
            result["seeded"].append(name)

    finally:
        if own_session:
            db.close()

    return result


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    result = seed_personas()
    seeded, skipped = result["seeded"], result["skipped"]
    logger.info(
        "Done — %d seeded, %d skipped.",
        len(seeded),
        len(skipped),
    )
    if not seeded and not skipped:
        sys.exit(0)


if __name__ == "__main__":
    main()
