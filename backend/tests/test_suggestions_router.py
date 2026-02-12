"""Tests for the suggestions API router."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.database import Base  # noqa: E402
from backend.dependencies import get_db  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models.user import User  # noqa: E402, F401
from backend.models.session import Session  # noqa: E402, F401
from backend.routers import suggestions as suggestions_router  # noqa: E402
from backend.routers.suggestions import _DEFAULT_SUGGESTIONS, Suggestion  # noqa: E402

# Router is registered in main.py — no need to add here


@pytest.fixture(autouse=True)
def setup_db():
    """Create an isolated in-memory database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestSessionLocal
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


class TestGetSuggestions:
    """Tests for GET /api/suggestions."""

    def test_returns_200(self):
        """Endpoint returns 200 OK."""
        resp = client.get("/api/suggestions")
        assert resp.status_code == 200

    def test_returns_four_suggestions(self):
        """Response contains exactly 4 suggestions."""
        resp = client.get("/api/suggestions")
        data = resp.json()
        assert len(data["suggestions"]) == 4

    def test_no_auth_required(self):
        """Endpoint is accessible without authentication cookies."""
        resp = client.get("/api/suggestions")
        assert resp.status_code == 200

    def test_suggestion_has_required_fields(self):
        """Each suggestion contains id, label, prompt, and icon fields."""
        resp = client.get("/api/suggestions")
        for s in resp.json()["suggestions"]:
            assert "id" in s
            assert "label" in s
            assert "prompt" in s
            assert "icon" in s

    def test_suggestion_ids_are_unique(self):
        """All suggestion IDs are unique."""
        resp = client.get("/api/suggestions")
        ids = [s["id"] for s in resp.json()["suggestions"]]
        assert len(ids) == len(set(ids))

    def test_suggestions_have_nonempty_prompts(self):
        """All suggestions have non-empty prompt strings."""
        resp = client.get("/api/suggestions")
        for s in resp.json()["suggestions"]:
            assert len(s["prompt"]) > 0

    def test_response_matches_default_suggestions(self):
        """Response matches the hardcoded default suggestions."""
        resp = client.get("/api/suggestions")
        data = resp.json()
        assert len(data["suggestions"]) == len(_DEFAULT_SUGGESTIONS)
        for returned, expected in zip(data["suggestions"], _DEFAULT_SUGGESTIONS):
            assert returned["id"] == expected.id
            assert returned["prompt"] == expected.prompt

    def test_suggestion_model_validation(self):
        """Suggestion Pydantic model validates correctly."""
        s = Suggestion(id="test", label="Test", prompt="Do something")
        assert s.icon is None
        s2 = Suggestion(id="test2", label="Test2", prompt="Do more", icon="star")
        assert s2.icon == "star"
