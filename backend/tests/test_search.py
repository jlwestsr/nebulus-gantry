"""Tests for the conversation search endpoint."""
import os

# Set test database URL before any backend imports.
os.environ["DATABASE_URL"] = "sqlite:///./test_search.db"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.dependencies import get_db
from backend.main import app
from backend.models.user import User
from backend.models.conversation import Conversation
from backend.models.message import Message
from backend.services.auth_service import AuthService


# ── Test database setup ──────────────────────────────────────────────────────

TEST_DB_URL = "sqlite:///./test_search.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Provide a test database session."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """Provide a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def user_with_token(db):
    """Create a regular user and return (user, session_token)."""
    auth = AuthService(db)
    user = auth.create_user(
        email="searcher@test.com",
        password="searchpass123",
        display_name="Search User",
        role="user",
    )
    token = auth.create_session(user.id)
    return user, token


@pytest.fixture
def other_user_with_token(db):
    """Create another user whose conversations should not appear in search."""
    auth = AuthService(db)
    user = auth.create_user(
        email="other@test.com",
        password="otherpass123",
        display_name="Other User",
        role="user",
    )
    token = auth.create_session(user.id)
    return user, token


@pytest.fixture
def user_with_conversations(db, user_with_token):
    """Create a user with conversations and messages for search testing."""
    user, token = user_with_token

    # Conversation 1: about Python
    conv1 = Conversation(user_id=user.id, title="Python Discussion")
    db.add(conv1)
    db.flush()

    msg1 = Message(conversation_id=conv1.id, role="user", content="How do I use list comprehensions in Python?")
    msg2 = Message(conversation_id=conv1.id, role="assistant", content="List comprehensions provide a concise way to create lists in Python. For example: [x**2 for x in range(10)]")
    db.add_all([msg1, msg2])

    # Conversation 2: about JavaScript
    conv2 = Conversation(user_id=user.id, title="JavaScript Help")
    db.add(conv2)
    db.flush()

    msg3 = Message(conversation_id=conv2.id, role="user", content="What are arrow functions in JavaScript?")
    msg4 = Message(conversation_id=conv2.id, role="assistant", content="Arrow functions are a concise syntax for writing function expressions in JavaScript: const add = (a, b) => a + b;")
    db.add_all([msg3, msg4])

    # Conversation 3: about databases
    conv3 = Conversation(user_id=user.id, title="Database Questions")
    db.add(conv3)
    db.flush()

    msg5 = Message(conversation_id=conv3.id, role="user", content="Explain SQL joins to me")
    msg6 = Message(conversation_id=conv3.id, role="assistant", content="SQL joins are used to combine rows from two or more tables based on a related column. The main types are INNER JOIN, LEFT JOIN, RIGHT JOIN, and FULL OUTER JOIN.")
    db.add_all([msg5, msg6])

    db.commit()
    return user, token


# ── Authentication tests ─────────────────────────────────────────────────────


class TestSearchAuthentication:
    """Test that unauthenticated requests are rejected."""

    def test_search_unauthenticated(self, client):
        response = client.get("/api/chat/search?q=python")
        assert response.status_code == 401

    def test_search_invalid_token(self, client):
        response = client.get(
            "/api/chat/search?q=python",
            cookies={"session_token": "invalid-token"},
        )
        assert response.status_code == 401


# ── Search functionality tests ───────────────────────────────────────────────


class TestSearchResults:
    """Test search endpoint returns correct results."""

    def test_search_returns_matching_results(self, client, user_with_conversations):
        _, token = user_with_conversations
        response = client.get(
            "/api/chat/search?q=Python",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) > 0

        # All results should mention Python
        for result in data["results"]:
            assert "python" in result["message_snippet"].lower()

    def test_search_case_insensitive(self, client, user_with_conversations):
        _, token = user_with_conversations
        response = client.get(
            "/api/chat/search?q=python",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        lower_results = response.json()["results"]

        response = client.get(
            "/api/chat/search?q=PYTHON",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        upper_results = response.json()["results"]

        assert len(lower_results) == len(upper_results)

    def test_search_no_results(self, client, user_with_conversations):
        _, token = user_with_conversations
        response = client.get(
            "/api/chat/search?q=xyznonexistent123",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []

    def test_search_empty_query(self, client, user_with_conversations):
        _, token = user_with_conversations
        response = client.get(
            "/api/chat/search?q=",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []

    def test_search_whitespace_query(self, client, user_with_conversations):
        _, token = user_with_conversations
        response = client.get(
            "/api/chat/search?q=   ",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []

    def test_search_result_schema(self, client, user_with_conversations):
        """Each result should contain the expected fields."""
        _, token = user_with_conversations
        response = client.get(
            "/api/chat/search?q=Python",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) > 0

        result = results[0]
        assert "conversation_id" in result
        assert "conversation_title" in result
        assert "message_snippet" in result
        assert "role" in result
        assert "created_at" in result
        assert result["role"] in ("user", "assistant")

    def test_search_multiple_conversations(self, client, user_with_conversations):
        """Search for a term that appears in multiple conversations."""
        _, token = user_with_conversations
        # "function" appears in JavaScript conversation
        response = client.get(
            "/api/chat/search?q=function",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) > 0

    def test_search_includes_conversation_title(self, client, user_with_conversations):
        _, token = user_with_conversations
        response = client.get(
            "/api/chat/search?q=SQL",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) > 0

        titles = {r["conversation_title"] for r in results}
        assert "Database Questions" in titles


# ── Isolation tests ──────────────────────────────────────────────────────────


class TestSearchIsolation:
    """Test that users can only search their own conversations."""

    def test_cannot_see_other_users_conversations(
        self, client, db, user_with_conversations, other_user_with_token
    ):
        """A user should not see another user's conversations in search."""
        _, other_token = other_user_with_token

        # Other user searches for Python, which exists in first user's conversations
        response = client.get(
            "/api/chat/search?q=Python",
            cookies={"session_token": other_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
