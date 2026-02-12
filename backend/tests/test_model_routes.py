"""Tests for model selection routes — ensures the chat model picker works.

Test 1: The active model displays correctly (GET /api/models returns
         model list with the correct one flagged as active).
Test 2: Selecting a different model loads it correctly
         (POST /v1/model/load triggers on switch, GET /api/models/active
         reflects the new model).
"""
import os
from unittest.mock import patch, AsyncMock

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import httpx  # noqa: E402
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


# ── Test database setup ──────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def setup_db():
    """Create an isolated in-memory database for each test."""
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
        password="testpass",
        display_name="Test User",
        role="user",
    )
    token = auth.create_session(user.id)
    return user, token


@pytest.fixture
def admin_user(db):
    """Create an admin user and return (user, session_token)."""
    auth = AuthService(db)
    user = auth.create_user(
        email="admin@test.com",
        password="adminpass",
        display_name="Admin",
        role="admin",
    )
    token = auth.create_session(user.id)
    return user, token


def _mock_response(json_data: dict, status_code: int = 200) -> httpx.Response:
    """Build a fake httpx.Response for mocking."""
    resp = httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "http://fake"),
    )
    return resp


# ── Test 1: Active model displays correctly in model selector ────────────────


class TestActiveModelDisplay:
    """Verify GET /api/models returns the model list with the active flag.

    This is what the frontend model picker uses to show the currently
    selected LLM in the chat input area.
    """

    def test_list_models_shows_active_model(self, client, test_user):
        """The active model should be flagged in the model list."""
        _, token = test_user

        models_response = _mock_response({
            "data": [
                {"id": "llama-3.1-8b", "active": True},
                {"id": "qwen-2.5-14b", "active": False},
            ]
        })
        active_response = _mock_response({"id": "llama-3.1-8b"})

        async def mock_get(url, **kwargs):
            if "/v1/model" in url and "/v1/models" not in url:
                return active_response
            return models_response

        with patch("backend.services.model_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=mock_get)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            response = client.get(
                "/api/models",
                cookies={"session_token": token},
            )

        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) == 2

        active = [m for m in data["models"] if m["active"]]
        assert len(active) == 1
        assert active[0]["id"] == "llama-3.1-8b"
        assert active[0]["name"] == "llama-3.1-8b"

    def test_active_model_endpoint(self, client, test_user):
        """GET /api/models/active returns the currently loaded model."""
        _, token = test_user

        active_response = _mock_response({"id": "llama-3.1-8b"})

        async def mock_get(url, **kwargs):
            return active_response

        with patch("backend.services.model_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=mock_get)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            response = client.get(
                "/api/models/active",
                cookies={"session_token": token},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["model"] is not None
        assert data["model"]["id"] == "llama-3.1-8b"

    def test_no_active_model_returns_null(self, client, test_user):
        """When no model is loaded, active endpoint returns null."""
        _, token = test_user

        async def mock_get(url, **kwargs):
            raise httpx.ConnectError("LLM server down")

        with patch("backend.services.model_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=mock_get)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            response = client.get(
                "/api/models/active",
                cookies={"session_token": token},
            )

        assert response.status_code == 200
        assert response.json()["model"] is None

    def test_list_models_unauthenticated(self, client):
        """Model listing requires authentication."""
        response = client.get("/api/models")
        assert response.status_code == 401

    def test_list_models_empty_when_server_down(self, client, test_user):
        """When LLM server is unreachable, return empty model list."""
        _, token = test_user

        with patch("backend.services.model_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.ConnectError("refused")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            response = client.get(
                "/api/models",
                cookies={"session_token": token},
            )

        assert response.status_code == 200
        assert response.json()["models"] == []


# ── Test 2: Selecting a different model loads correctly ──────────────────────


class TestModelSwitching:
    """Verify that switching models calls the LLM server and reflects
    the change in subsequent queries.

    This covers the admin model load endpoint and confirms the active
    model updates after a switch.
    """

    def test_switch_model_calls_load_endpoint(self, client, admin_user):
        """Switching models calls POST /v1/model/load on the LLM server."""
        _, token = admin_user

        load_response = _mock_response({"status": "ok"})

        with patch("backend.services.model_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=load_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            response = client.post(
                "/api/admin/models/switch",
                json={"model_id": "qwen-2.5-14b"},
                cookies={"session_token": token},
            )

        assert response.status_code == 200

        # Verify the LLM server was called with the correct model
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "v1/model/load" in call_args[0][0]
        assert call_args[1]["json"]["name"] == "qwen-2.5-14b"

    def test_switched_model_shows_as_active(self, client, test_user):
        """After switching, the new model appears as active in the list."""
        _, token = test_user

        # Simulate the state AFTER switching to qwen-2.5-14b
        models_response = _mock_response({
            "data": [
                {"id": "llama-3.1-8b", "active": False},
                {"id": "qwen-2.5-14b", "active": True},
            ]
        })
        active_response = _mock_response({"id": "qwen-2.5-14b"})

        async def mock_get(url, **kwargs):
            if "/v1/model" in url and "/v1/models" not in url:
                return active_response
            return models_response

        with patch("backend.services.model_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=mock_get)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            response = client.get(
                "/api/models",
                cookies={"session_token": token},
            )

        assert response.status_code == 200
        data = response.json()
        active = [m for m in data["models"] if m["active"]]
        assert len(active) == 1
        assert active[0]["id"] == "qwen-2.5-14b"

        inactive = [m for m in data["models"] if not m["active"]]
        assert len(inactive) == 1
        assert inactive[0]["id"] == "llama-3.1-8b"

    def test_switch_model_nonexistent_server(self, client, admin_user):
        """Switching models when LLM server is down returns failure."""
        _, token = admin_user

        with patch("backend.services.model_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                side_effect=httpx.ConnectError("refused")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            response = client.post(
                "/api/admin/models/switch",
                json={"model_id": "qwen-2.5-14b"},
                cookies={"session_token": token},
            )

        # Should return 503 (service unavailable), not crash
        assert response.status_code == 503

    def test_switch_model_requires_admin(self, client, test_user):
        """Only admins can switch models."""
        _, token = test_user
        response = client.post(
            "/api/admin/models/switch",
            json={"model_id": "qwen-2.5-14b"},
            cookies={"session_token": token},
        )
        assert response.status_code == 403
