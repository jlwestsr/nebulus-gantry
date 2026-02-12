"""Tests for the persona seed script."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import json  # noqa: E402
from pathlib import Path  # noqa: E402
from tempfile import TemporaryDirectory  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.database import Base  # noqa: E402
from backend.models.persona import Persona  # noqa: E402
from backend.models.user import User  # noqa: E402, F401
from backend.models.conversation import Conversation  # noqa: E402, F401
from backend.models.session import Session  # noqa: E402, F401
from backend.scripts.seed_personas import seed_personas  # noqa: E402


@pytest.fixture(autouse=True)
def db_session():
    """Create an isolated in-memory database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    _Session = sessionmaker(bind=engine)
    session = _Session()
    yield session
    session.close()


@pytest.fixture()
def fixtures_dir():
    """Temporary directory with a sample persona fixture."""
    with TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        data = {
            "name": "Dealership Analyst",
            "description": "Expert used car dealership analyst.",
            "temperature": 0.4,
            "is_default": True,
            "system_prompt": "You are a senior dealership business analyst.",
        }
        (p / "dealership_analyst.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        yield p


# -- Core seeding --------------------------------------------------------


def test_seed_creates_persona(db_session, fixtures_dir):
    """Seed script should create the Dealership Analyst persona."""
    result = seed_personas(db=db_session, fixtures_dir=fixtures_dir)
    assert "Dealership Analyst" in result["seeded"]

    persona = (
        db_session.query(Persona)
        .filter(Persona.name == "Dealership Analyst")
        .first()
    )
    assert persona is not None
    assert persona.user_id is None  # system persona
    assert persona.is_default is True
    assert persona.temperature == pytest.approx(0.4)


# -- Idempotency ---------------------------------------------------------


def test_seed_is_idempotent(db_session, fixtures_dir):
    """Running seed twice should not create duplicates."""
    seed_personas(db=db_session, fixtures_dir=fixtures_dir)
    result = seed_personas(db=db_session, fixtures_dir=fixtures_dir)

    assert "Dealership Analyst" in result["skipped"]
    assert result["seeded"] == []

    count = (
        db_session.query(Persona)
        .filter(Persona.name == "Dealership Analyst")
        .count()
    )
    assert count == 1


# -- Edge cases -----------------------------------------------------------


def test_seed_empty_directory(db_session):
    """Seed with no fixtures returns empty results."""
    with TemporaryDirectory() as tmpdir:
        result = seed_personas(db=db_session, fixtures_dir=Path(tmpdir))
    assert result["seeded"] == []
    assert result["skipped"] == []


def test_seed_skips_malformed_json(db_session):
    """Seed skips files with invalid JSON."""
    with TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "bad.json").write_text("{invalid json", encoding="utf-8")
        result = seed_personas(db=db_session, fixtures_dir=p)
    assert result["seeded"] == []
    assert result["skipped"] == []


def test_seed_skips_missing_name(db_session):
    """Seed skips fixtures without a 'name' field."""
    with TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        data = {"description": "no name", "system_prompt": "test"}
        (p / "noname.json").write_text(json.dumps(data), encoding="utf-8")
        result = seed_personas(db=db_session, fixtures_dir=p)
    assert result["seeded"] == []
