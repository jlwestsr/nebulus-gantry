import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database import Base
from backend.dependencies import get_db
from backend.services.auth_service import AuthService


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create test user
    auth = AuthService(session)
    auth.create_user("user@test.com", "password123", "Test User")

    yield session
    session.close()


@pytest.fixture
def client(test_db):
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(client):
    # Login first
    client.post("/api/auth/login", json={
        "email": "user@test.com",
        "password": "password123"
    })
    return client


def test_create_conversation(authenticated_client):
    response = authenticated_client.post("/api/chat/conversations")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "title" in data


def test_list_conversations(authenticated_client):
    # Create a conversation first
    authenticated_client.post("/api/chat/conversations")

    response = authenticated_client.get("/api/chat/conversations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_conversation(authenticated_client):
    # Create a conversation first
    create_response = authenticated_client.post("/api/chat/conversations")
    conv_id = create_response.json()["id"]

    response = authenticated_client.get(f"/api/chat/conversations/{conv_id}")
    assert response.status_code == 200
    data = response.json()
    assert "conversation" in data
    assert "messages" in data


def test_delete_conversation(authenticated_client):
    # Create a conversation first
    create_response = authenticated_client.post("/api/chat/conversations")
    conv_id = create_response.json()["id"]

    response = authenticated_client.delete(f"/api/chat/conversations/{conv_id}")
    assert response.status_code == 200

    # Verify it's deleted
    get_response = authenticated_client.get(f"/api/chat/conversations/{conv_id}")
    assert get_response.status_code == 404


def test_conversations_unauthenticated(client):
    response = client.get("/api/chat/conversations")
    assert response.status_code == 401


def test_send_message_to_conversation(authenticated_client):
    # Create a conversation first
    create_response = authenticated_client.post("/api/chat/conversations")
    conv_id = create_response.json()["id"]

    # Send a message (this will fail to connect to LLM but should return streaming response)
    response = authenticated_client.post(
        f"/api/chat/conversations/{conv_id}/messages",
        json={"content": "Hello"}
    )
    assert response.status_code == 200
    # The response should be a streaming response
    assert "text/event-stream" in response.headers.get("content-type", "")
