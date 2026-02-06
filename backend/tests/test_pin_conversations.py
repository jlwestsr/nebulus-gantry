"""Tests for conversation pinning functionality."""
import os

# Set test database URL before any backend imports
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.database import Base  # noqa: E402
from backend.dependencies import get_db  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models.user import User  # noqa: E402, F401
from backend.models.session import Session  # noqa: E402, F401
from backend.models.conversation import Conversation  # noqa: E402
from backend.models.message import Message  # noqa: E402
from backend.services.auth_service import AuthService  # noqa: E402


# ── Test database setup ──────────────────────────────────────────────────────


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
    engine.dispose()


@pytest.fixture
def db(setup_db):
    """Provide a test database session."""
    session = setup_db()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """Provide a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def test_user(db):
    """Create a regular user and return (user, session_token)."""
    auth = AuthService(db)
    user = auth.create_user(
        email="user@test.com",
        password="correctpass",
        display_name="Test User",
        role="user",
    )
    token = auth.create_session(user.id)
    return user, token


# ── Toggle Pin tests ────────────────────────────────────────────────────────


class TestTogglePin:
    """Tests for the toggle pin endpoint."""

    def test_toggle_pin_success(self, client, test_user, db):
        """Test successfully toggling pin status."""
        user, token = test_user

        # Create a conversation directly in the database
        conv = Conversation(user_id=user.id, title="Test Conversation", pinned=False)
        db.add(conv)
        db.commit()
        conv_id = conv.id

        # Toggle pin ON
        response = client.patch(
            f"/api/chat/conversations/{conv_id}/pin",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pinned"] is True
        assert data["id"] == conv_id

        # Toggle pin OFF
        response = client.patch(
            f"/api/chat/conversations/{conv_id}/pin",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pinned"] is False

    def test_toggle_pin_not_found(self, client, test_user):
        """Test toggling pin on non-existent conversation returns 404."""
        _, token = test_user
        response = client.patch(
            "/api/chat/conversations/99999/pin",
            cookies={"session_token": token},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Conversation not found"

    def test_toggle_pin_wrong_user(self, client, test_user, db):
        """Test toggling pin on another user's conversation returns 404."""
        _, token = test_user

        # Create a user for the "other" user
        auth = AuthService(db)
        other_user = auth.create_user(
            email="other@test.com",
            password="otherpass",
            display_name="Other User",
            role="user",
        )

        # Create a conversation belonging to that other user
        conv = Conversation(user_id=other_user.id, title="Other User Conv", pinned=False)
        db.add(conv)
        db.commit()
        conv_id = conv.id

        # Try to pin it as the original test user
        response = client.patch(
            f"/api/chat/conversations/{conv_id}/pin",
            cookies={"session_token": token},
        )
        assert response.status_code == 404

    def test_toggle_pin_unauthenticated(self, client):
        """Test toggling pin without authentication returns 401."""
        response = client.patch("/api/chat/conversations/1/pin")
        assert response.status_code == 401


# ── Pinned Sorting tests ────────────────────────────────────────────────────


class TestPinnedSorting:
    """Tests for pinned conversations appearing first."""

    def test_pinned_conversations_first(self, client, test_user, db):
        """Test that pinned conversations appear before non-pinned ones."""
        user, token = test_user
        # Use naive UTC datetime for SQLite compatibility
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Create multiple conversations with varying dates and pin status
        conv1 = Conversation(
            user_id=user.id,
            title="Old Unpinned",
            pinned=False,
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(days=10),
        )
        conv2 = Conversation(
            user_id=user.id,
            title="Old Pinned",
            pinned=True,
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=5),
        )
        conv3 = Conversation(
            user_id=user.id,
            title="Recent Unpinned",
            pinned=False,
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1),
        )

        db.add_all([conv1, conv2, conv3])
        db.commit()

        # Fetch conversations
        response = client.get(
            "/api/chat/conversations",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()

        # Find the pinned conversation and verify it's first
        assert len(data) == 3
        assert data[0]["pinned"] is True
        assert data[0]["title"] == "Old Pinned"

        # Unpinned should be sorted by updated_at desc
        unpinned = [c for c in data if not c["pinned"]]
        assert unpinned[0]["title"] == "Recent Unpinned"
        assert unpinned[1]["title"] == "Old Unpinned"


# ── Search With Titles tests ────────────────────────────────────────────────


class TestSearchWithTitles:
    """Tests for search including conversation titles."""

    def test_search_matches_title(self, client, test_user, db):
        """Test that search matches conversation titles."""
        user, token = test_user

        # Create conversation with distinctive title
        conv = Conversation(user_id=user.id, title="Project Alpha Discussion", pinned=False)
        db.add(conv)
        db.commit()

        # Add a message that doesn't contain our search term
        msg = Message(conversation_id=conv.id, role="user", content="Hello there")
        db.add(msg)
        db.commit()

        # Search for a term in the title
        response = client.get(
            "/api/chat/search?q=Alpha",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()

        # Should find the conversation via title match
        assert len(data["results"]) > 0
        assert any(r["conversation_title"] == "Project Alpha Discussion" for r in data["results"])

    def test_search_matches_content_only(self, client, test_user, db):
        """Test that search still matches message content."""
        user, token = test_user

        conv = Conversation(user_id=user.id, title="Generic Title", pinned=False)
        db.add(conv)
        db.commit()

        msg = Message(conversation_id=conv.id, role="user", content="Special keyword unique")
        db.add(msg)
        db.commit()

        response = client.get(
            "/api/chat/search?q=unique",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) > 0
        assert "unique" in data["results"][0]["message_snippet"].lower()
