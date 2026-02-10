"""Tests for Situation Map endpoints — budget and active dispatches.

Validates the new Phase B endpoints:
- GET /api/overlord/budget
- GET /api/overlord/dispatch/active
- POST /api/overlord/halt
"""
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
from backend.models.user import User  # noqa: E402, F401
from backend.models.session import Session  # noqa: E402, F401
from backend.services.auth_service import AuthService  # noqa: E402
from backend.services.overlord_service import (  # noqa: E402
    OverlordService,
    reset_overlord_service,
)


# ── Test database setup ──────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def setup_db():
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


@pytest.fixture(autouse=True)
def reset_service():
    reset_overlord_service()
    yield
    reset_overlord_service()


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
def admin_client(client, admin_user):
    _, token = admin_user
    client.cookies.set("session_token", token)
    return client


def _mock_service() -> MagicMock:
    """Create a mock OverlordService with situation map defaults."""
    svc = MagicMock(spec=OverlordService)

    svc.get_budget_status.return_value = {
        "tokens_used_today": 45200,
        "token_ceiling": 200000,
        "cost_usd_today": 1.24,
        "cost_ceiling_usd": 10.0,
        "usage_pct": 22.6,
    }

    svc.get_active_dispatches.return_value = [
        {
            "id": "task-001",
            "title": "Build auth feature",
            "project": "nebulus-core",
            "status": "dispatched",
        },
        {
            "id": "task-002",
            "title": "Fix router bug",
            "project": "nebulus-gantry",
            "status": "in_review",
        },
    ]

    svc.halt_all.return_value = {
        "message": "Halted: 2 task(s) cancelled, daemon not running",
        "tasks_cancelled": 2,
        "daemon_stopped": False,
    }

    return svc


# ── Budget Endpoint Tests ─────────────────────────────────────────────────


class TestBudgetEndpoint:
    def test_returns_budget_status(self, admin_client):
        mock_svc = _mock_service()
        with patch(
            "backend.routers.overlord.get_overlord_service",
            return_value=mock_svc,
        ):
            resp = admin_client.get("/api/overlord/budget")

        assert resp.status_code == 200
        data = resp.json()
        assert data["tokens_used_today"] == 45200
        assert data["token_ceiling"] == 200000
        assert data["cost_usd_today"] == 1.24
        assert data["cost_ceiling_usd"] == 10.0
        assert data["usage_pct"] == 22.6

    def test_returns_zeros_when_unavailable(self, admin_client):
        mock_svc = _mock_service()
        mock_svc.get_budget_status.return_value = {
            "tokens_used_today": 0,
            "token_ceiling": 200000,
            "cost_usd_today": 0.0,
            "cost_ceiling_usd": 10.0,
            "usage_pct": 0.0,
        }
        with patch(
            "backend.routers.overlord.get_overlord_service",
            return_value=mock_svc,
        ):
            resp = admin_client.get("/api/overlord/budget")

        assert resp.status_code == 200
        data = resp.json()
        assert data["tokens_used_today"] == 0
        assert data["usage_pct"] == 0.0

    def test_requires_admin(self, client):
        """Budget endpoint should require admin auth."""
        resp = client.get("/api/overlord/budget")
        assert resp.status_code in (401, 403)

    def test_503_when_overlord_unavailable(self, admin_client):
        """Should return 503 when OverlordService cannot be created."""
        with patch(
            "backend.routers.overlord.get_overlord_service",
            side_effect=RuntimeError("not available"),
        ):
            resp = admin_client.get("/api/overlord/budget")
        assert resp.status_code == 503


# ── Active Dispatches Endpoint Tests ──────────────────────────────────────


class TestActiveDispatchesEndpoint:
    def test_returns_dispatch_list(self, admin_client):
        mock_svc = _mock_service()
        with patch(
            "backend.routers.overlord.get_overlord_service",
            return_value=mock_svc,
        ):
            resp = admin_client.get("/api/overlord/dispatch/active")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["dispatches"]) == 2
        assert data["dispatches"][0]["id"] == "task-001"
        assert data["dispatches"][0]["status"] == "dispatched"
        assert data["dispatches"][1]["project"] == "nebulus-gantry"

    def test_empty_list_when_no_dispatches(self, admin_client):
        mock_svc = _mock_service()
        mock_svc.get_active_dispatches.return_value = []
        with patch(
            "backend.routers.overlord.get_overlord_service",
            return_value=mock_svc,
        ):
            resp = admin_client.get("/api/overlord/dispatch/active")

        assert resp.status_code == 200
        data = resp.json()
        assert data["dispatches"] == []

    def test_requires_admin(self, client):
        resp = client.get("/api/overlord/dispatch/active")
        assert resp.status_code in (401, 403)


# ── Halt Endpoint Tests ──────────────────────────────────────────────────


class TestHaltEndpoint:
    def test_halt_returns_result(self, admin_client):
        mock_svc = _mock_service()
        with patch(
            "backend.routers.overlord.get_overlord_service",
            return_value=mock_svc,
        ):
            resp = admin_client.post("/api/overlord/halt")

        assert resp.status_code == 200
        data = resp.json()
        assert data["tasks_cancelled"] == 2
        assert "Halted" in data["message"]
        mock_svc.halt_all.assert_called_once()

    def test_halt_with_nothing_running(self, admin_client):
        mock_svc = _mock_service()
        mock_svc.halt_all.return_value = {
            "message": "Halted: 0 task(s) cancelled, daemon not running",
            "tasks_cancelled": 0,
            "daemon_stopped": False,
        }
        with patch(
            "backend.routers.overlord.get_overlord_service",
            return_value=mock_svc,
        ):
            resp = admin_client.post("/api/overlord/halt")

        assert resp.status_code == 200
        data = resp.json()
        assert data["tasks_cancelled"] == 0

    def test_halt_requires_admin(self, client):
        resp = client.post("/api/overlord/halt")
        assert resp.status_code in (401, 403)
