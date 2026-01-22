
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
# Assuming we have a main app definition.
# In a real scenario, we'd import the initialized `app` from `nebulus_gantry.main`.
# Here we will create a minimal app with the router for testing isolation.
from fastapi import FastAPI
from nebulus_gantry.routers.notes_routes import router, get_db, get_current_user_id

# --- Fixtures ---


@pytest.fixture
def mock_db_session():
    """Mocks the SQLAlchemy Session."""
    session = MagicMock()
    return session


@pytest.fixture
def client(mock_db_session):
    """
    Creates a TestClient with overridden dependencies.
    """
    app = FastAPI()
    app.include_router(router)

    # Override the database dependency
    app.dependency_overrides[get_db] = lambda: mock_db_session
    # Override user auth to simulate a logged-in user (ID=1)
    app.dependency_overrides[get_current_user_id] = lambda: 1

    return TestClient(app)

# --- Tests ---


def test_get_notes_empty(client, mock_db_session):
    """
    Test GET /api/notes returns an empty list when DB is empty.
    """
    # Setup mock to return empty list
    mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

    response = client.get("/api/notes")

    assert response.status_code == 200
    assert response.json() == []


def test_create_note_success(client, mock_db_session):
    """
    Test POST /api/notes successfully creates a note and returns Pydantic model.
    """
    payload = {
        "title": "Test Creation",
        "content": "This is a test note.",
        "category": "Testing"
    }

    # Setup the mock to simulate the object creation logic typically handled by DB
    # We don't control the ID generation in unit test unless we mock the refresh,
    # but strictly speaking the Router expects the object to have an ID after commit/refresh.
    def mock_add(created_note):
        created_note.id = 101  # Simulate DB ID assignment

    mock_db_session.add.side_effect = mock_add

    response = client.post("/api/notes", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 101
    assert data["title"] == "Test Creation"
    assert data["user_id"] == 1  # From dependency override

    # Verify DB interactions
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()


def test_get_note_not_found(client, mock_db_session):
    """
    Test GET /api/notes/{id} returns 404 for non-existent note.
    """
    # Setup mock to return None
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    response = client.get("/api/notes/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Note not found"
