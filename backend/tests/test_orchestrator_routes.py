"""Tests for Orchestrator API router — proxy to Atom's workflow orchestrator."""
import os
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from httpx import HTTPStatusError, Request, Response  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.database import Base  # noqa: E402
from backend.dependencies import get_db  # noqa: E402
from backend.main import app  # noqa: E402
from backend.services.auth_service import AuthService  # noqa: E402


# ── Test database setup ──────────────────────────────────────────────────


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
    session = setup_db()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_user(db):
    auth = AuthService(db)
    user = auth.create_user(
        email="admin@test.com",
        password="adminpass123",
        display_name="Admin User",
        role="admin",
    )
    token = auth.create_session(user.id)
    return user, token


@pytest.fixture
def regular_user(db):
    auth = AuthService(db)
    user = auth.create_user(
        email="user@test.com",
        password="userpass123",
        display_name="Regular User",
        role="user",
    )
    token = auth.create_session(user.id)
    return user, token


# ── Mock data ────────────────────────────────────────────────────────────


def mock_job_response():
    """Mock job response from Atom orchestrator."""
    return {
        "id": "job-123",
        "workflow": "build-feature",
        "status": "running",
        "inputs": {"goal": "Add authentication"},
        "steps": {
            "plan": {
                "status": "completed",
                "output": "Implementation plan created",
                "error": None,
                "duration_seconds": 2.5,
                "model_used": "claude-sonnet-4",
            },
            "implement": {
                "status": "running",
                "output": None,
                "error": None,
                "duration_seconds": None,
                "model_used": None,
            },
        },
        "created_at": "2026-03-20T10:00:00Z",
        "started_at": "2026-03-20T10:00:01Z",
        "completed_at": None,
        "error": None,
    }


def mock_template_info():
    """Mock template info from Atom orchestrator."""
    return {
        "name": "build-feature",
        "description": "Build a new feature with planning and implementation",
        "steps": ["plan", "implement", "test"],
    }


# ── Tests ────────────────────────────────────────────────────────────────


def test_health_check_available(client):
    """Health check returns available when Atom is reachable."""
    with patch(
        "backend.services.orchestrator_client.OrchestratorClient.health_check",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = client.get("/api/orchestrator/health")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert "base_url" in data


def test_health_check_unavailable(client):
    """Health check returns unavailable when Atom is unreachable."""
    with patch(
        "backend.services.orchestrator_client.OrchestratorClient.health_check",
        new_callable=AsyncMock,
        return_value=False,
    ):
        response = client.get("/api/orchestrator/health")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False


def test_submit_job_requires_admin(client, regular_user):
    """Submitting a job requires admin authentication."""
    _, token = regular_user
    response = client.post(
        "/api/orchestrator/jobs",
        json={"template": "build-feature", "inputs": {"goal": "Test"}},
        cookies={"session_token": token},
    )
    assert response.status_code == 403


def test_submit_job_success(client, admin_user):
    """Admin can submit a job successfully."""
    _, token = admin_user
    with patch(
        "backend.services.orchestrator_client.OrchestratorClient.submit_job",
        new_callable=AsyncMock,
        return_value=mock_job_response(),
    ):
        response = client.post(
            "/api/orchestrator/jobs",
            json={"template": "build-feature", "inputs": {"goal": "Add auth"}},
            cookies={"session_token": token},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["id"] == "job-123"
        assert data["status"] == "running"


def test_submit_job_atom_unavailable(client, admin_user):
    """Returns 503 when Atom orchestrator is unavailable."""
    _, token = admin_user
    with patch(
        "backend.services.orchestrator_client.OrchestratorClient.submit_job",
        new_callable=AsyncMock,
        side_effect=Exception("Connection refused"),
    ):
        response = client.post(
            "/api/orchestrator/jobs",
            json={"template": "build-feature", "inputs": {"goal": "Test"}},
            cookies={"session_token": token},
        )
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()


def test_list_jobs_requires_admin(client, regular_user):
    """Listing jobs requires admin authentication."""
    _, token = regular_user
    response = client.get(
        "/api/orchestrator/jobs",
        cookies={"session_token": token},
    )
    assert response.status_code == 403


def test_list_jobs_success(client, admin_user):
    """Admin can list jobs successfully."""
    _, token = admin_user
    with patch(
        "backend.services.orchestrator_client.OrchestratorClient.list_jobs",
        new_callable=AsyncMock,
        return_value=[mock_job_response()],
    ):
        response = client.get(
            "/api/orchestrator/jobs",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "job-123"


def test_get_job_requires_admin(client, regular_user):
    """Getting a job requires admin authentication."""
    _, token = regular_user
    response = client.get(
        "/api/orchestrator/jobs/job-123",
        cookies={"session_token": token},
    )
    assert response.status_code == 403


def test_get_job_success(client, admin_user):
    """Admin can get a job successfully."""
    _, token = admin_user
    with patch(
        "backend.services.orchestrator_client.OrchestratorClient.get_job",
        new_callable=AsyncMock,
        return_value=mock_job_response(),
    ):
        response = client.get(
            "/api/orchestrator/jobs/job-123",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "job-123"


def test_get_job_not_found(client, admin_user):
    """Returns 404 when job is not found."""
    _, token = admin_user
    mock_response = Response(404, json={"detail": "Not found"})
    mock_request = Request("GET", "http://test/jobs/job-999")
    with patch(
        "backend.services.orchestrator_client.OrchestratorClient.get_job",
        new_callable=AsyncMock,
        side_effect=HTTPStatusError("Not found", request=mock_request, response=mock_response),
    ):
        response = client.get(
            "/api/orchestrator/jobs/job-999",
            cookies={"session_token": token},
        )
        assert response.status_code == 404


def test_list_templates_requires_admin(client, regular_user):
    """Listing templates requires admin authentication."""
    _, token = regular_user
    response = client.get(
        "/api/orchestrator/templates",
        cookies={"session_token": token},
    )
    assert response.status_code == 403


def test_list_templates_success(client, admin_user):
    """Admin can list templates successfully."""
    _, token = admin_user
    with patch(
        "backend.services.orchestrator_client.OrchestratorClient.list_templates",
        new_callable=AsyncMock,
        return_value=[mock_template_info()],
    ):
        response = client.get(
            "/api/orchestrator/templates",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "build-feature"


def test_cancel_job_requires_admin(client, regular_user):
    """Canceling a job requires admin authentication."""
    _, token = regular_user
    response = client.delete(
        "/api/orchestrator/jobs/job-123",
        cookies={"session_token": token},
    )
    assert response.status_code == 403


def test_cancel_job_success(client, admin_user):
    """Admin can cancel a job successfully."""
    _, token = admin_user
    with patch(
        "backend.services.orchestrator_client.OrchestratorClient.cancel_job",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = client.delete(
            "/api/orchestrator/jobs/job-123",
            cookies={"session_token": token},
        )
        assert response.status_code == 204
