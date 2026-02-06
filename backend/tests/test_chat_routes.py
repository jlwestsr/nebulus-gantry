"""Tests for chat routes (conversations CRUD, message streaming)."""
import os
from unittest.mock import patch, AsyncMock, MagicMock

# Set test database URL before any backend imports to avoid the module-level
# create_all in dependencies.py trying to open the default sqlite file.
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
from backend.models.conversation import Conversation  # noqa: E402, F401
from backend.models.message import Message  # noqa: E402, F401
from backend.services.auth_service import AuthService  # noqa: E402
from backend.services.chat_service import ChatService  # noqa: E402


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


# ── Create Conversation tests ────────────────────────────────────────────────


class TestCreateConversation:
    """Test POST /api/chat/conversations."""

    def test_create_conversation(self, client, test_user):
        """POST /api/chat/conversations returns 200 with title and id."""
        _, token = test_user
        response = client.post(
            "/api/chat/conversations",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "New Thread"

    def test_create_conversation_unauthenticated(self, client):
        """POST /api/chat/conversations without cookie returns 401."""
        response = client.post("/api/chat/conversations")
        assert response.status_code == 401


# ── List Conversations tests ─────────────────────────────────────────────────


class TestListConversations:
    """Test GET /api/chat/conversations."""

    def test_list_conversations(self, client, test_user):
        """Create 2 conversations, GET returns list of 2."""
        _, token = test_user
        client.post("/api/chat/conversations", cookies={"session_token": token})
        client.post("/api/chat/conversations", cookies={"session_token": token})

        response = client.get(
            "/api/chat/conversations",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_list_conversations_empty(self, client, test_user):
        """GET with no conversations returns empty list."""
        _, token = test_user
        response = client.get(
            "/api/chat/conversations",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data == []


# ── Get Conversation tests ───────────────────────────────────────────────────


class TestGetConversation:
    """Test GET /api/chat/conversations/{id}."""

    def test_get_conversation_with_messages(self, client, test_user, db):
        """Create conversation + add message via ChatService, GET returns both."""
        _, token = test_user
        # Create conversation via API
        create_resp = client.post(
            "/api/chat/conversations",
            cookies={"session_token": token},
        )
        conv_id = create_resp.json()["id"]

        # Add a message directly via ChatService
        chat_svc = ChatService(db)
        chat_svc.add_message(conv_id, "user", "Hello")

        response = client.get(
            f"/api/chat/conversations/{conv_id}",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "conversation" in data
        assert "messages" in data
        assert data["conversation"]["id"] == conv_id
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "Hello"
        assert data["messages"][0]["role"] == "user"

    def test_get_conversation_not_found(self, client, test_user):
        """GET with nonexistent conversation id returns 404."""
        _, token = test_user
        response = client.get(
            "/api/chat/conversations/99999",
            cookies={"session_token": token},
        )
        assert response.status_code == 404


# ── Delete Conversation tests ────────────────────────────────────────────────


class TestDeleteConversation:
    """Test DELETE /api/chat/conversations/{id}."""

    def test_delete_conversation(self, client, test_user):
        """Creates, deletes, confirms it's 404 afterwards."""
        _, token = test_user
        # Create
        create_resp = client.post(
            "/api/chat/conversations",
            cookies={"session_token": token},
        )
        conv_id = create_resp.json()["id"]

        # Delete
        delete_resp = client.delete(
            f"/api/chat/conversations/{conv_id}",
            cookies={"session_token": token},
        )
        assert delete_resp.status_code == 200

        # Confirm 404
        get_resp = client.get(
            f"/api/chat/conversations/{conv_id}",
            cookies={"session_token": token},
        )
        assert get_resp.status_code == 404

    def test_delete_conversation_not_found(self, client, test_user):
        """DELETE with nonexistent conversation id returns 404."""
        _, token = test_user
        response = client.delete(
            "/api/chat/conversations/99999",
            cookies={"session_token": token},
        )
        assert response.status_code == 404


# ── Send Message tests ───────────────────────────────────────────────────────


class TestSendMessage:
    """Test POST /api/chat/conversations/{id}/messages."""

    def test_send_message_streams_response(self, client, test_user):
        """POST returns streaming response with mocked LLM/Memory/Graph services."""
        _, token = test_user
        # Create a conversation first
        create_resp = client.post(
            "/api/chat/conversations",
            cookies={"session_token": token},
        )
        conv_id = create_resp.json()["id"]

        async def fake_stream(messages, model="default", temperature=None):
            yield "Hello "
            yield "world"

        with patch("backend.routers.chat.LLMService") as MockLLM, \
             patch("backend.routers.chat._create_memory_service") as mock_mem_factory, \
             patch("backend.routers.chat._create_graph_service") as mock_graph_factory:
            # Mock MemoryService
            mock_mem = MagicMock()
            mock_mem.search_similar = AsyncMock(return_value=[])
            mock_mem.embed_message = AsyncMock()
            mock_mem_factory.return_value = mock_mem

            # Mock GraphService
            mock_graph = MagicMock()
            mock_graph.extract_entities.return_value = []
            mock_graph.get_related.return_value = []
            mock_graph_factory.return_value = mock_graph

            # Mock LLMService
            mock_llm = MagicMock()
            mock_llm.stream_chat = fake_stream
            MockLLM.return_value = mock_llm

            response = client.post(
                f"/api/chat/conversations/{conv_id}/messages",
                json={"content": "Hi there"},
                cookies={"session_token": token},
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            body = response.text
            assert "Hello " in body
            assert "world" in body

    def test_send_message_to_nonexistent_conversation(self, client, test_user):
        """POST to nonexistent conversation returns 404."""
        _, token = test_user

        with patch("backend.routers.chat.LLMService"), \
             patch("backend.routers.chat._create_memory_service"), \
             patch("backend.routers.chat._create_graph_service"):
            response = client.post(
                "/api/chat/conversations/99999/messages",
                json={"content": "Hello"},
                cookies={"session_token": token},
            )
            assert response.status_code == 404

    def test_send_message_unauthenticated(self, client):
        """POST without cookie returns 401."""
        response = client.post(
            "/api/chat/conversations/1/messages",
            json={"content": "Hello"},
        )
        assert response.status_code == 401
