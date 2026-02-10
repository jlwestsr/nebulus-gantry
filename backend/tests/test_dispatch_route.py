"""Tests for the /api/chat/dispatch endpoint."""
import json
import os
from unittest.mock import patch, MagicMock

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.database import Base  # noqa: E402
from backend.dependencies import get_db  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models.user import User  # noqa: F401, E402
from backend.models.session import Session  # noqa: F401, E402
from backend.services.auth_service import AuthService  # noqa: E402
from backend.services.conversation_router import reset_conversation_router  # noqa: E402


# ── Test database setup ──────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def setup_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
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


@pytest.fixture(autouse=True)
def reset_router():
    reset_conversation_router()
    yield
    reset_conversation_router()


@pytest.fixture
def db(setup_db):
    session = setup_db()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_user(db):
    auth = AuthService(db)
    user = auth.create_user(
        email="user@test.com",
        password="testpass123",
        display_name="Test User",
    )
    return user


@pytest.fixture
def auth_client(client, auth_user):
    """Return a client with an authenticated session."""
    client.post(
        "/api/auth/login",
        json={"email": "user@test.com", "password": "testpass123"},
    )
    return client


# ── Endpoint Tests ───────────────────────────────────────────────────────────


class TestDispatchEndpointAuth:
    def test_dispatch_requires_auth(self, client):
        """Dispatch endpoint should require authentication."""
        resp = client.post(
            "/api/chat/dispatch",
            json={"user_message": "hello"},
        )
        assert resp.status_code in (401, 403)

    def test_dispatch_with_auth_returns_stream(self, auth_client):
        """Authenticated dispatch should return SSE stream."""
        # Mock the conversation router to avoid real LLM calls
        from backend.schemas.dispatch import content_event, result_event

        async def mock_route(*args, **kwargs):
            yield content_event("Hello", source="local")
            yield result_event("", source="local")

        with patch(
            "backend.services.conversation_router.get_conversation_router"
        ) as mock_get:
            mock_router = MagicMock()
            mock_router.route_message = mock_route
            mock_get.return_value = mock_router

            resp = auth_client.post(
                "/api/chat/dispatch",
                json={"user_message": "hello"},
            )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")


class TestDispatchFallback:
    def test_fallback_when_routing_disabled(self, auth_client):
        """When OVERLORD_ROUTING_ENABLED=False, should use direct LLM."""
        from backend.config import settings

        original = settings.overlord_routing_enabled
        settings.overlord_routing_enabled = False

        try:
            # Mock LLMService.stream_chat
            async def mock_stream(*args, **kwargs):
                yield "Hello"
                yield " world"

            with patch(
                "backend.routers.chat.LLMService"
            ) as MockLLM:
                mock_instance = MagicMock()
                mock_instance.stream_chat = mock_stream
                MockLLM.return_value = mock_instance

                resp = auth_client.post(
                    "/api/chat/dispatch",
                    json={"user_message": "hello"},
                )

            assert resp.status_code == 200

            # Parse SSE events
            events = _parse_sse_events(resp.text)
            content_events = [e for e in events if e.get("type") == "content"]
            assert len(content_events) >= 1
        finally:
            settings.overlord_routing_enabled = original


class TestDispatchProtocol:
    def test_dispatch_accepts_full_request(self, auth_client):
        """Dispatch should accept a full DispatchRequest payload."""
        from backend.schemas.dispatch import content_event, result_event

        async def mock_route(*args, **kwargs):
            yield content_event("OK", source="claude")
            yield result_event("", source="claude")

        with patch(
            "backend.services.conversation_router.get_conversation_router"
        ) as mock_get:
            mock_router = MagicMock()
            mock_router.route_message = mock_route
            mock_get.return_value = mock_router

            resp = auth_client.post(
                "/api/chat/dispatch",
                json={
                    "user_message": "explain the code",
                    "conversation_history": [
                        {"role": "user", "content": "hi"},
                        {"role": "assistant", "content": "hello"},
                    ],
                    "context": {
                        "active_project": "nebulus-core",
                        "trust_level": "cautious",
                        "token_budget": 25000,
                    },
                    "role": "pm",
                },
            )

        assert resp.status_code == 200

    def test_dispatch_stream_ends_with_done(self, auth_client):
        """SSE stream should end with [DONE] marker."""
        from backend.schemas.dispatch import result_event

        async def mock_route(*args, **kwargs):
            yield result_event("done")

        with patch(
            "backend.services.conversation_router.get_conversation_router"
        ) as mock_get:
            mock_router = MagicMock()
            mock_router.route_message = mock_route
            mock_get.return_value = mock_router

            resp = auth_client.post(
                "/api/chat/dispatch",
                json={"user_message": "test"},
            )

        assert resp.status_code == 200
        assert "data: [DONE]" in resp.text


class TestExistingEndpointsNotBroken:
    def test_conversations_endpoint_still_works(self, auth_client):
        """Existing conversation CRUD should be unaffected."""
        # Create a conversation
        resp = auth_client.post("/api/chat/conversations")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

        # List conversations
        resp = auth_client.get("/api/chat/conversations")
        assert resp.status_code == 200

    def test_send_message_endpoint_still_works(self, auth_client):
        """Existing /messages endpoint should still function."""
        # Create a conversation first
        resp = auth_client.post("/api/chat/conversations")
        conv_id = resp.json()["id"]

        # Send message (will fail to connect to LLM, but endpoint should respond)
        resp = auth_client.post(
            f"/api/chat/conversations/{conv_id}/messages",
            json={"content": "hello"},
        )
        # Should return 200 with streaming response (even if LLM errors)
        assert resp.status_code == 200


# ── Helpers ──────────────────────────────────────────────────────────────────


def _parse_sse_events(text: str) -> list[dict]:
    """Parse SSE text into a list of event dicts."""
    events = []
    for line in text.split("\n\n"):
        line = line.strip()
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                continue
            try:
                events.append(json.loads(data))
            except json.JSONDecodeError:
                continue
    return events
