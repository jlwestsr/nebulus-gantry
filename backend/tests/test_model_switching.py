"""Tests for automatic model switching during chat."""
import os
from unittest.mock import AsyncMock, patch

# Set test database URL before any backend imports
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
from backend.models.conversation import Conversation  # noqa: E402
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


# ── Model Switching Tests ────────────────────────────────────────────────────


class TestModelSwitching:
    """Tests for automatic model switching when sending messages."""

    def test_model_switching_when_different_model_requested(
        self, client, test_user, db
    ):
        """Test that model switches when a different model is requested."""
        user, token = test_user

        # Create a conversation
        conv = Conversation(user_id=user.id, title="Test Conversation")
        db.add(conv)
        db.commit()
        conv_id = conv.id

        # Mock TabbyAPI responses
        with patch(
            "backend.services.model_service.ModelService.get_active_model"
        ) as mock_get_active, patch(
            "backend.services.model_service.ModelService.switch_model"
        ) as mock_switch, patch(
            "backend.services.llm_service.LLMService.stream_chat"
        ) as mock_stream:
            # First call returns model-a, second call returns model-b after switch
            mock_get_active.side_effect = [
                {"id": "model-a", "name": "Model A"},
                {"id": "model-b", "name": "Model B"},
            ]
            mock_switch.return_value = AsyncMock(return_value=True)

            async def async_gen():
                for chunk in ["Hello", " ", "World"]:
                    yield chunk

            mock_stream.return_value = async_gen()

            # Send message with model-b (different from currently loaded model-a)
            response = client.post(
                f"/api/chat/conversations/{conv_id}/messages",
                json={"content": "Test message", "model": "model-b"},
                cookies={"session_token": token},
            )

            # Should switch and then stream
            assert mock_switch.called
            mock_switch.assert_called_once_with("model-b")
            assert response.status_code == 200

    def test_no_switch_when_same_model_requested(self, client, test_user, db):
        """Test that no switch occurs when requesting the already-loaded model."""
        user, token = test_user

        # Create a conversation
        conv = Conversation(user_id=user.id, title="Test Conversation")
        db.add(conv)
        db.commit()
        conv_id = conv.id

        # Mock TabbyAPI responses
        with patch(
            "backend.services.model_service.ModelService.get_active_model"
        ) as mock_get_active, patch(
            "backend.services.model_service.ModelService.switch_model"
        ) as mock_switch, patch(
            "backend.services.llm_service.LLMService.stream_chat"
        ) as mock_stream:
            # Model-a is already loaded
            mock_get_active.side_effect = [
                {"id": "model-a", "name": "Model A"},
                {"id": "model-a", "name": "Model A"},
            ]

            async def async_gen():
                for chunk in ["Hello", " ", "World"]:
                    yield chunk

            mock_stream.return_value = async_gen()

            # Send message with model-a (same as currently loaded)
            response = client.post(
                f"/api/chat/conversations/{conv_id}/messages",
                json={"content": "Test message", "model": "model-a"},
                cookies={"session_token": token},
            )

            # Should NOT switch
            assert not mock_switch.called
            assert response.status_code == 200

    def test_switch_fails_returns_error(self, client, test_user, db):
        """Test that a failed model switch returns an error to the user."""
        user, token = test_user

        # Create a conversation
        conv = Conversation(user_id=user.id, title="Test Conversation")
        db.add(conv)
        db.commit()
        conv_id = conv.id

        # Mock TabbyAPI responses
        with patch(
            "backend.services.model_service.ModelService.get_active_model"
        ) as mock_get_active, patch(
            "backend.services.model_service.ModelService.switch_model"
        ) as mock_switch:
            # Model-a is loaded, trying to switch to model-b
            mock_get_active.return_value = {"id": "model-a", "name": "Model A"}
            # Switch fails (return False from the async method)
            mock_switch.return_value = False

            # Send message with model-b
            response = client.post(
                f"/api/chat/conversations/{conv_id}/messages",
                json={"content": "Test message", "model": "model-b"},
                cookies={"session_token": token},
            )

            # Should return 500 error
            assert response.status_code == 500
            assert "Failed to load model" in response.json()["detail"]
            assert "model-b" in response.json()["detail"]

    def test_no_model_specified_uses_current(self, client, test_user, db):
        """Test that when no model is specified, the current model is used."""
        user, token = test_user

        # Create a conversation
        conv = Conversation(user_id=user.id, title="Test Conversation")
        db.add(conv)
        db.commit()
        conv_id = conv.id

        # Mock TabbyAPI responses
        with patch(
            "backend.services.model_service.ModelService.get_active_model"
        ) as mock_get_active, patch(
            "backend.services.model_service.ModelService.switch_model"
        ) as mock_switch, patch(
            "backend.services.llm_service.LLMService.stream_chat"
        ) as mock_stream:
            # Model-a is loaded
            mock_get_active.return_value = {"id": "model-a", "name": "Model A"}

            async def async_gen():
                for chunk in ["Hello", " ", "World"]:
                    yield chunk

            mock_stream.return_value = async_gen()

            # Send message without specifying model
            response = client.post(
                f"/api/chat/conversations/{conv_id}/messages",
                json={"content": "Test message"},
                cookies={"session_token": token},
            )

            # Should NOT attempt to switch
            assert not mock_switch.called
            assert response.status_code == 200
