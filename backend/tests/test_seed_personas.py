"""Tests for the persona seed script.

Uses an in-memory SQLite database and ``tmp_path`` for fixture files.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.persona import Persona
from backend.scripts.seed_personas import seed_personas


@pytest.fixture()
def db_session():
    """Provide a transactional in-memory SQLite session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _write_fixture(directory: Path, name: str, data: dict) -> Path:
    """Helper — write a JSON fixture file into *directory*."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


_VALID_PERSONA = {
    "name": "Test Analyst",
    "description": "A test persona.",
    "system_prompt": "You are a test.",
    "temperature": 0.5,
    "is_default": False,
}


# ── 1. Seed a brand-new persona ──────────────────────────────────────

def test_seed_new_persona(db_session, tmp_path: Path) -> None:
    """A new persona is inserted when the DB is empty."""
    _write_fixture(tmp_path, "analyst", _VALID_PERSONA)
    result = seed_personas(db=db_session, fixtures_dir=tmp_path)

    assert result["seeded"] == ["Test Analyst"]
    assert result["skipped"] == []
    assert db_session.query(Persona).count() == 1


# ── 2. Skip existing persona (idempotent) ────────────────────────────

def test_skip_existing_persona(db_session, tmp_path: Path) -> None:
    """Running twice does not create a duplicate."""
    _write_fixture(tmp_path, "analyst", _VALID_PERSONA)
    seed_personas(db=db_session, fixtures_dir=tmp_path)
    result = seed_personas(db=db_session, fixtures_dir=tmp_path)

    assert result["seeded"] == []
    assert result["skipped"] == ["Test Analyst"]
    assert db_session.query(Persona).count() == 1


# ── 3. Empty fixtures directory ───────────────────────────────────────

def test_empty_fixtures_dir(db_session, tmp_path: Path) -> None:
    """An empty directory produces no inserts and no errors."""
    result = seed_personas(db=db_session, fixtures_dir=tmp_path)

    assert result == {"seeded": [], "skipped": []}
    assert db_session.query(Persona).count() == 0


# ── 4. Non-existent fixtures directory ────────────────────────────────

def test_nonexistent_fixtures_dir(db_session, tmp_path: Path) -> None:
    """A missing directory is handled gracefully."""
    result = seed_personas(db=db_session, fixtures_dir=tmp_path / "nope")

    assert result == {"seeded": [], "skipped": []}


# ── 5. Malformed JSON file ────────────────────────────────────────────

def test_malformed_json(db_session, tmp_path: Path) -> None:
    """A file with invalid JSON is skipped without aborting."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "bad.json").write_text("{not valid json", encoding="utf-8")
    _write_fixture(tmp_path, "good", _VALID_PERSONA)

    result = seed_personas(db=db_session, fixtures_dir=tmp_path)

    assert result["seeded"] == ["Test Analyst"]
    assert db_session.query(Persona).count() == 1


# ── 6. Fixture missing required 'name' field ─────────────────────────

def test_missing_name_field(db_session, tmp_path: Path) -> None:
    """A fixture without a 'name' key is skipped."""
    _write_fixture(tmp_path, "no_name", {"system_prompt": "hello"})

    result = seed_personas(db=db_session, fixtures_dir=tmp_path)

    assert result["seeded"] == []
    assert result["skipped"] == []
    assert db_session.query(Persona).count() == 0


# ── 7. Multiple fixtures seeded in one call ───────────────────────────

def test_multiple_fixtures(db_session, tmp_path: Path) -> None:
    """All valid fixtures are seeded in a single call."""
    for i in range(3):
        _write_fixture(tmp_path, f"persona_{i}", {
            **_VALID_PERSONA,
            "name": f"Persona {i}",
        })

    result = seed_personas(db=db_session, fixtures_dir=tmp_path)

    assert len(result["seeded"]) == 3
    assert db_session.query(Persona).count() == 3


# ── 8. Persona fields are stored correctly ────────────────────────────

def test_persona_fields_stored(db_session, tmp_path: Path) -> None:
    """All fixture fields map correctly to the Persona model."""
    data = {
        "name": "Field Check",
        "description": "desc",
        "system_prompt": "prompt",
        "temperature": 0.3,
        "model_id": "gpt-4",
        "is_default": True,
    }
    _write_fixture(tmp_path, "fields", data)
    seed_personas(db=db_session, fixtures_dir=tmp_path)

    persona = db_session.query(Persona).first()
    assert persona is not None
    assert persona.name == "Field Check"
    assert persona.description == "desc"
    assert persona.system_prompt == "prompt"
    assert persona.temperature == pytest.approx(0.3)
    assert persona.model_id == "gpt-4"
    assert persona.is_default is True
    assert persona.user_id is None  # system persona


# ── 9. User-owned persona with same name does not block seeding ───────

def test_user_persona_does_not_block_system(db_session, tmp_path: Path) -> None:
    """A user-owned persona with the same name should not prevent seeding a system one."""
    # Create a user-owned persona manually.
    db_session.add(Persona(
        user_id=1, name="Test Analyst", system_prompt="user", temperature=0.7,
    ))
    db_session.commit()

    _write_fixture(tmp_path, "analyst", _VALID_PERSONA)
    result = seed_personas(db=db_session, fixtures_dir=tmp_path)

    assert result["seeded"] == ["Test Analyst"]
    assert db_session.query(Persona).count() == 2


# ── 10. Default temperature when omitted ──────────────────────────────

def test_default_temperature(db_session, tmp_path: Path) -> None:
    """When temperature is omitted from the fixture, 0.7 is used."""
    _write_fixture(tmp_path, "minimal", {
        "name": "Minimal",
        "system_prompt": "hi",
    })
    seed_personas(db=db_session, fixtures_dir=tmp_path)

    persona = db_session.query(Persona).first()
    assert persona is not None
    assert persona.temperature == pytest.approx(0.7)
