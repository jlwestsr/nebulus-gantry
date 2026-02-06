"""Tests for Overlord API router and role-based access control."""
import os
from dataclasses import dataclass, field
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


@pytest.fixture(autouse=True)
def reset_service():
    """Reset the singleton service between tests."""
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


# ── Mock data factories ──────────────────────────────────────────────────────


@dataclass
class MockGitState:
    branch: str = "develop"
    clean: bool = True
    ahead: int = 0
    behind: int = 0
    last_commit: str = "abc1234"
    last_commit_date: str = "2026-02-06"
    stale_branches: list = field(default_factory=list)
    tags: list = field(default_factory=list)


@dataclass
class MockTestHealth:
    has_tests: bool = True
    test_command: str = "pytest"
    last_run: str | None = None


@dataclass
class MockProjectConfig:
    name: str = "core"
    path: str = "/tmp/core"
    remote: str = "origin"
    role: str = "library"
    branch_model: str = "develop-main"
    depends_on: list = field(default_factory=list)


@dataclass
class MockProjectStatus:
    name: str = "core"
    config: MockProjectConfig = field(default_factory=MockProjectConfig)
    git: MockGitState = field(default_factory=MockGitState)
    tests: MockTestHealth = field(default_factory=MockTestHealth)
    issues: list = field(default_factory=list)


def _mock_overlord_service() -> MagicMock:
    """Create a mock OverlordService with sensible defaults."""
    svc = MagicMock(spec=OverlordService)

    svc.get_dashboard.return_value = {
        "projects": [
            {
                "name": "nebulus-core",
                "role": "library",
                "git": {
                    "branch": "develop",
                    "clean": True,
                    "ahead": 0,
                    "behind": 0,
                    "last_commit": "abc1234",
                    "last_commit_date": "2026-02-06",
                    "stale_branches": [],
                },
                "tests": {"has_tests": True, "test_command": "pytest"},
                "issues": [],
            },
        ],
        "daemon": {"running": True, "pid": 12345},
        "config": {
            "autonomy_levels": {"nebulus-core": "cautious"},
            "scheduled_tasks": [],
        },
    }

    svc.scan_single_project.return_value = {
        "name": "nebulus-core",
        "role": "library",
        "git": {
            "branch": "develop",
            "clean": True,
            "ahead": 0,
            "behind": 0,
            "last_commit": "abc1234",
            "last_commit_date": "2026-02-06",
            "stale_branches": [],
        },
        "tests": {"has_tests": True, "test_command": "pytest"},
        "issues": [],
    }

    svc.get_graph.return_value = {
        "adjacency": {"nebulus-core": ["nebulus-prime"]},
        "ascii": "core -> prime",
    }

    svc.list_memory.return_value = {
        "entries": [
            {
                "id": "mem-1",
                "timestamp": "2026-02-06T10:00:00",
                "category": "decision",
                "project": "nebulus-core",
                "content": "Use shared adapter pattern",
                "metadata": {},
            },
        ],
        "count": 1,
    }

    svc.add_memory.return_value = "mem-new"
    svc.delete_memory.return_value = True

    svc.parse_task.return_value = {
        "task": "run tests in core",
        "steps": [
            {
                "id": "step-1",
                "action": "run tests",
                "project": "nebulus-core",
                "dependencies": [],
                "model_tier": None,
                "timeout": 300,
            },
        ],
        "scope": {
            "projects": ["nebulus-core"],
            "branches": [],
            "destructive": False,
            "reversible": True,
            "affects_remote": False,
            "estimated_impact": "low",
        },
        "estimated_duration": 300,
        "requires_approval": False,
    }

    svc.execute_task.return_value = {
        "status": "success",
        "steps": [
            {
                "step_id": "step-1",
                "success": True,
                "output": "All tests passed",
                "error": None,
                "duration": 5.2,
            },
        ],
        "reason": "",
    }

    svc.list_proposals.return_value = [
        {
            "id": "prop-1",
            "task": "merge develop to main",
            "scope_projects": ["nebulus-core"],
            "scope_impact": "medium",
            "affects_remote": False,
            "reason": "Scheduled merge",
            "state": "pending",
            "created_at": "2026-02-06T10:00:00",
            "resolved_at": None,
            "result_summary": None,
        },
    ]

    svc.approve_proposal.return_value = {
        "message": "Proposal approved and executed",
        "result": {
            "status": "success",
            "steps": [],
            "reason": "",
        },
    }

    svc.get_audit_proposals.return_value = svc.list_proposals.return_value
    svc.get_detections.return_value = [
        {
            "detector": "stale_branch",
            "project": "nebulus-core",
            "severity": "medium",
            "description": "Branch feat/old is 14 days stale",
            "proposed_action": "Delete branch feat/old",
        },
    ]
    svc.get_notification_stats.return_value = {
        "urgent_count": 1,
        "buffered_count": 3,
        "last_digest_time": None,
    }

    return svc


@pytest.fixture
def mock_service():
    """Override the service dependency with a mock."""
    svc = _mock_overlord_service()
    from backend.routers.overlord import _get_service

    app.dependency_overrides[_get_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(_get_service, None)


# ── Authentication Tests ─────────────────────────────────────────────────────


class TestOverlordAuthentication:
    """All overlord endpoints require authentication."""

    ENDPOINTS = [
        ("GET", "/api/overlord/dashboard"),
        ("GET", "/api/overlord/graph"),
        ("GET", "/api/overlord/memory"),
        ("GET", "/api/overlord/proposals"),
        ("GET", "/api/overlord/audit/proposals"),
        ("GET", "/api/overlord/audit/detections"),
        ("GET", "/api/overlord/audit/notifications"),
    ]

    @pytest.mark.parametrize("method,path", ENDPOINTS)
    def test_unauthenticated_returns_401(self, client, mock_service, method, path):
        response = getattr(client, method.lower())(path)
        assert response.status_code == 401


class TestOverlordAuthorization:
    """All overlord endpoints require admin role."""

    ENDPOINTS = [
        ("GET", "/api/overlord/dashboard"),
        ("GET", "/api/overlord/graph"),
        ("GET", "/api/overlord/memory"),
        ("GET", "/api/overlord/proposals"),
        ("GET", "/api/overlord/audit/proposals"),
        ("GET", "/api/overlord/audit/detections"),
        ("GET", "/api/overlord/audit/notifications"),
    ]

    @pytest.mark.parametrize("method,path", ENDPOINTS)
    def test_regular_user_returns_403(
        self, client, regular_user, mock_service, method, path
    ):
        _, token = regular_user
        response = getattr(client, method.lower())(
            path, cookies={"session_token": token}
        )
        assert response.status_code == 403


# ── Tier 1: Dashboard Tests ─────────────────────────────────────────────────


class TestDashboardEndpoints:

    def test_dashboard_returns_projects(self, client, admin_user, mock_service):
        _, token = admin_user
        response = client.get(
            "/api/overlord/dashboard", cookies={"session_token": token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert "daemon" in data
        assert "config" in data
        assert len(data["projects"]) == 1
        assert data["projects"][0]["name"] == "nebulus-core"
        assert data["daemon"]["running"] is True

    def test_scan_single_project(self, client, admin_user, mock_service):
        _, token = admin_user
        response = client.get(
            "/api/overlord/scan/nebulus-core", cookies={"session_token": token}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "nebulus-core"
        assert data["git"]["branch"] == "develop"

    def test_scan_unknown_project_returns_404(
        self, client, admin_user, mock_service
    ):
        _, token = admin_user
        mock_service.scan_single_project.side_effect = KeyError("Unknown project")
        response = client.get(
            "/api/overlord/scan/nonexistent", cookies={"session_token": token}
        )
        assert response.status_code == 404

    def test_graph_returns_adjacency_and_ascii(self, client, admin_user, mock_service):
        _, token = admin_user
        response = client.get(
            "/api/overlord/graph", cookies={"session_token": token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "adjacency" in data
        assert "ascii" in data
        assert "nebulus-core" in data["adjacency"]


# ── Tier 2: Memory Tests ────────────────────────────────────────────────────


class TestMemoryEndpoints:

    def test_list_memory(self, client, admin_user, mock_service):
        _, token = admin_user
        response = client.get(
            "/api/overlord/memory", cookies={"session_token": token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert data["count"] == 1

    def test_list_memory_with_filters(self, client, admin_user, mock_service):
        _, token = admin_user
        response = client.get(
            "/api/overlord/memory?category=decision&project=nebulus-core",
            cookies={"session_token": token},
        )
        assert response.status_code == 200

    def test_add_memory(self, client, admin_user, mock_service):
        _, token = admin_user
        response = client.post(
            "/api/overlord/memory",
            json={"category": "decision", "content": "Test memory"},
            cookies={"session_token": token},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "mem-new"

    def test_delete_memory(self, client, admin_user, mock_service):
        _, token = admin_user
        response = client.delete(
            "/api/overlord/memory/mem-1", cookies={"session_token": token}
        )
        assert response.status_code == 200

    def test_delete_nonexistent_memory_returns_404(
        self, client, admin_user, mock_service
    ):
        _, token = admin_user
        mock_service.delete_memory.return_value = False
        response = client.delete(
            "/api/overlord/memory/nonexistent", cookies={"session_token": token}
        )
        assert response.status_code == 404


# ── Tier 3: Dispatch Tests ──────────────────────────────────────────────────


class TestDispatchEndpoints:

    def test_parse_task(self, client, admin_user, mock_service):
        _, token = admin_user
        response = client.post(
            "/api/overlord/dispatch/parse",
            json={"task": "run tests in core"},
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task"] == "run tests in core"
        assert len(data["steps"]) == 1

    def test_parse_invalid_task_returns_400(self, client, admin_user, mock_service):
        _, token = admin_user
        mock_service.parse_task.side_effect = ValueError("Cannot parse task")
        response = client.post(
            "/api/overlord/dispatch/parse",
            json={"task": "invalid gibberish"},
            cookies={"session_token": token},
        )
        assert response.status_code == 400

    def test_execute_task(self, client, admin_user, mock_service):
        _, token = admin_user
        response = client.post(
            "/api/overlord/dispatch/execute",
            json={"task": "run tests in core", "auto_approve": True},
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_list_proposals(self, client, admin_user, mock_service):
        _, token = admin_user
        response = client.get(
            "/api/overlord/proposals", cookies={"session_token": token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "proposals" in data
        assert len(data["proposals"]) == 1

    def test_approve_proposal(self, client, admin_user, mock_service):
        _, token = admin_user
        response = client.post(
            "/api/overlord/proposals/prop-1/approve",
            cookies={"session_token": token},
        )
        assert response.status_code == 200

    def test_approve_nonexistent_proposal_returns_404(
        self, client, admin_user, mock_service
    ):
        _, token = admin_user
        mock_service.approve_proposal.side_effect = KeyError("Not found")
        response = client.post(
            "/api/overlord/proposals/nonexistent/approve",
            cookies={"session_token": token},
        )
        assert response.status_code == 404

    def test_deny_proposal(self, client, admin_user, mock_service):
        _, token = admin_user
        response = client.post(
            "/api/overlord/proposals/prop-1/deny",
            json={"reason": "Not needed"},
            cookies={"session_token": token},
        )
        assert response.status_code == 200

    def test_deny_nonexistent_proposal_returns_404(
        self, client, admin_user, mock_service
    ):
        _, token = admin_user
        mock_service.deny_proposal.side_effect = KeyError("Not found")
        response = client.post(
            "/api/overlord/proposals/nonexistent/deny",
            json={"reason": "test"},
            cookies={"session_token": token},
        )
        assert response.status_code == 404


# ── Tier 4: Audit Tests ─────────────────────────────────────────────────────


class TestAuditEndpoints:

    def test_audit_proposals(self, client, admin_user, mock_service):
        _, token = admin_user
        response = client.get(
            "/api/overlord/audit/proposals", cookies={"session_token": token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "proposals" in data

    def test_audit_proposals_filtered(self, client, admin_user, mock_service):
        _, token = admin_user
        response = client.get(
            "/api/overlord/audit/proposals?state=completed",
            cookies={"session_token": token},
        )
        assert response.status_code == 200

    def test_detections(self, client, admin_user, mock_service):
        _, token = admin_user
        response = client.get(
            "/api/overlord/audit/detections", cookies={"session_token": token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "detections" in data
        assert len(data["detections"]) == 1
        assert data["detections"][0]["severity"] == "medium"

    def test_notification_stats(self, client, admin_user, mock_service):
        _, token = admin_user
        response = client.get(
            "/api/overlord/audit/notifications", cookies={"session_token": token}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["urgent_count"] == 1
        assert data["buffered_count"] == 3


# ── Graceful Degradation Tests ───────────────────────────────────────────────


class TestGracefulDegradation:

    def test_503_when_overlord_unavailable(self, client, admin_user):
        """Endpoints return 503 when Overlord modules are not available."""
        _, token = admin_user
        # Don't set up mock_service — let the real get_overlord_service fail
        with patch(
            "backend.services.overlord_service._OVERLORD_AVAILABLE", False
        ), patch(
            "backend.services.overlord_service._IMPORT_ERROR",
            "No module named 'nebulus_swarm'",
        ):
            reset_overlord_service()
            response = client.get(
                "/api/overlord/dashboard", cookies={"session_token": token}
            )
            assert response.status_code == 503
            assert "not available" in response.json()["detail"].lower()

    def test_503_when_config_missing(self, client, admin_user):
        """Endpoints return 503 when overlord.yml is missing."""
        _, token = admin_user
        # Simulate a config-missing error by setting the cached error
        with patch(
            "backend.services.overlord_service._service_instance", None
        ), patch(
            "backend.services.overlord_service._service_error",
            "Overlord config not found at /root/.atom/overlord.yml",
        ):
            response = client.get(
                "/api/overlord/dashboard", cookies={"session_token": token}
            )
            assert response.status_code == 503
            assert "not found" in response.json()["detail"].lower()
