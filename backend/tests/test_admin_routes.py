"""Tests for admin routes and role-based access control."""
import os
from unittest.mock import patch

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
def admin_user(db):
    """Create an admin user and return (user, session_token)."""
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
    """Create a regular user and return (user, session_token)."""
    auth = AuthService(db)
    user = auth.create_user(
        email="user@test.com",
        password="userpass123",
        display_name="Regular User",
        role="user",
    )
    token = auth.create_session(user.id)
    return user, token


# ── Authentication tests ─────────────────────────────────────────────────────


class TestAdminAuthentication:
    """Test that unauthenticated requests are rejected with 401."""

    def test_list_users_unauthenticated(self, client):
        response = client.get("/api/admin/users")
        assert response.status_code == 401

    def test_create_user_unauthenticated(self, client):
        response = client.post("/api/admin/users", json={
            "email": "new@test.com",
            "password": "pass123",
            "display_name": "New User",
        })
        assert response.status_code == 401

    def test_delete_user_unauthenticated(self, client):
        response = client.delete("/api/admin/users/1")
        assert response.status_code == 401

    def test_list_services_unauthenticated(self, client):
        response = client.get("/api/admin/services")
        assert response.status_code == 401

    def test_restart_service_unauthenticated(self, client):
        response = client.post("/api/admin/services/web/restart")
        assert response.status_code == 401

    def test_list_models_unauthenticated(self, client):
        response = client.get("/api/admin/models")
        assert response.status_code == 401

    def test_switch_model_unauthenticated(self, client):
        response = client.post("/api/admin/models/switch", json={"model_id": "gpt-4"})
        assert response.status_code == 401

    def test_stream_logs_unauthenticated(self, client):
        response = client.get("/api/admin/logs/web")
        assert response.status_code == 401


# ── Authorization tests (non-admin rejected with 403) ────────────────────────


class TestAdminAuthorization:
    """Test that non-admin users are rejected with 403."""

    def test_list_users_non_admin(self, client, regular_user):
        _, token = regular_user
        response = client.get(
            "/api/admin/users",
            cookies={"session_token": token},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Admin access required"

    def test_create_user_non_admin(self, client, regular_user):
        _, token = regular_user
        response = client.post(
            "/api/admin/users",
            json={
                "email": "new@test.com",
                "password": "pass123",
                "display_name": "New User",
            },
            cookies={"session_token": token},
        )
        assert response.status_code == 403

    def test_delete_user_non_admin(self, client, regular_user):
        _, token = regular_user
        response = client.delete(
            "/api/admin/users/1",
            cookies={"session_token": token},
        )
        assert response.status_code == 403

    def test_list_services_non_admin(self, client, regular_user):
        _, token = regular_user
        response = client.get(
            "/api/admin/services",
            cookies={"session_token": token},
        )
        assert response.status_code == 403

    def test_restart_service_non_admin(self, client, regular_user):
        _, token = regular_user
        response = client.post(
            "/api/admin/services/web/restart",
            cookies={"session_token": token},
        )
        assert response.status_code == 403

    def test_list_models_non_admin(self, client, regular_user):
        _, token = regular_user
        response = client.get(
            "/api/admin/models",
            cookies={"session_token": token},
        )
        assert response.status_code == 403

    def test_switch_model_non_admin(self, client, regular_user):
        _, token = regular_user
        response = client.post(
            "/api/admin/models/switch",
            json={"model_id": "gpt-4"},
            cookies={"session_token": token},
        )
        assert response.status_code == 403

    def test_stream_logs_non_admin(self, client, regular_user):
        _, token = regular_user
        response = client.get(
            "/api/admin/logs/web",
            cookies={"session_token": token},
        )
        assert response.status_code == 403


# ── Admin access tests (admin users allowed) ─────────────────────────────────


class TestAdminAccess:
    """Test that admin users can access admin endpoints."""

    def test_list_users_admin(self, client, admin_user):
        _, token = admin_user
        response = client.get(
            "/api/admin/users",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert isinstance(data["users"], list)

    def test_list_services_admin(self, client, admin_user):
        _, token = admin_user
        response = client.get(
            "/api/admin/services",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "services" in data
        assert isinstance(data["services"], list)

    def test_restart_service_admin_responds(self, client, admin_user):
        _, token = admin_user
        response = client.post(
            "/api/admin/services/web/restart",
            cookies={"session_token": token},
        )
        # Depending on Docker availability and container existence:
        # 200 = restarted, 404 = not found, 503 = Docker unavailable
        assert response.status_code in (200, 404, 503)

    def test_list_models_admin(self, client, admin_user):
        _, token = admin_user
        response = client.get(
            "/api/admin/models",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)

    def test_switch_model_admin_tabby_unavailable(self, client, admin_user):
        """POST /admin/models/switch returns 503 when TabbyAPI is unreachable."""
        _, token = admin_user
        response = client.post(
            "/api/admin/models/switch",
            json={"model_id": "gpt-4"},
            cookies={"session_token": token},
        )
        # TabbyAPI not running in test environment -> 503
        assert response.status_code == 503

    def test_stream_logs_admin(self, client, admin_user):
        _, token = admin_user
        with patch("backend.routers.admin._docker_service") as mock_ds:
            mock_ds.available = True

            def fake_stream(name, tail=100):
                yield "test log line"

            mock_ds.stream_logs = fake_stream

            response = client.get(
                "/api/admin/logs/web",
                cookies={"session_token": token},
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

    def test_stream_logs_returns_sse_data(self, client, admin_user):
        """GET /admin/logs/{name} streams SSE-formatted log lines."""
        _, token = admin_user
        with patch("backend.routers.admin._docker_service") as mock_ds:
            mock_ds.available = True

            def fake_stream(name, tail=100):
                yield "2026-02-03 INFO Starting server"
                yield "2026-02-03 INFO Ready"

            mock_ds.stream_logs = fake_stream

            response = client.get(
                "/api/admin/logs/gantry-api",
                cookies={"session_token": token},
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            body = response.text
            assert "data: " in body
            assert "Starting server" in body

    def test_stream_logs_docker_unavailable(self, client, admin_user):
        """GET /admin/logs/{name} returns 503 when Docker is unavailable."""
        _, token = admin_user
        with patch("backend.routers.admin._docker_service") as mock_ds:
            mock_ds.available = False

            response = client.get(
                "/api/admin/logs/gantry-api",
                cookies={"session_token": token},
            )
            assert response.status_code == 503


# ── Invalid session tests ────────────────────────────────────────────────────


class TestInvalidSession:
    """Test that invalid/expired session tokens are rejected."""

    def test_invalid_token(self, client):
        response = client.get(
            "/api/admin/users",
            cookies={"session_token": "invalid-token-value"},
        )
        assert response.status_code == 401

    def test_empty_token(self, client):
        response = client.get(
            "/api/admin/users",
            cookies={"session_token": ""},
        )
        assert response.status_code == 401


# ── User Management CRUD tests ───────────────────────────────────────────────


class TestUserManagementCRUD:
    """Test the user management API (Task 24)."""

    def test_list_users_returns_existing(self, client, admin_user, regular_user):
        """GET /admin/users should return all users in the database."""
        _, token = admin_user
        response = client.get(
            "/api/admin/users",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        users = data["users"]
        assert len(users) == 2
        emails = {u["email"] for u in users}
        assert "admin@test.com" in emails
        assert "user@test.com" in emails
        # Ensure password hashes are NOT exposed
        for u in users:
            assert "password_hash" not in u
            assert "password" not in u

    def test_list_users_contains_expected_fields(self, client, admin_user):
        """Each user object should have id, email, display_name, role."""
        _, token = admin_user
        response = client.get(
            "/api/admin/users",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        users = response.json()["users"]
        assert len(users) >= 1
        user = users[0]
        assert "id" in user
        assert "email" in user
        assert "display_name" in user
        assert "role" in user

    def test_create_user_success(self, client, admin_user):
        """POST /admin/users should create a new user and return 201."""
        _, token = admin_user
        response = client.post(
            "/api/admin/users",
            json={
                "email": "new@test.com",
                "password": "newpass123",
                "display_name": "New User",
                "role": "user",
            },
            cookies={"session_token": token},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@test.com"
        assert data["display_name"] == "New User"
        assert data["role"] == "user"
        assert "id" in data
        assert "password_hash" not in data
        assert "password" not in data

    def test_create_user_default_role(self, client, admin_user):
        """Creating a user without specifying role should default to 'user'."""
        _, token = admin_user
        response = client.post(
            "/api/admin/users",
            json={
                "email": "default@test.com",
                "password": "pass123",
                "display_name": "Default Role User",
            },
            cookies={"session_token": token},
        )
        assert response.status_code == 201
        assert response.json()["role"] == "user"

    def test_create_user_admin_role(self, client, admin_user):
        """Creating a user with admin role should succeed."""
        _, token = admin_user
        response = client.post(
            "/api/admin/users",
            json={
                "email": "admin2@test.com",
                "password": "adminpass",
                "display_name": "Another Admin",
                "role": "admin",
            },
            cookies={"session_token": token},
        )
        assert response.status_code == 201
        assert response.json()["role"] == "admin"

    def test_create_user_duplicate_email_409(self, client, admin_user):
        """POST /admin/users with an existing email should return 409."""
        _, token = admin_user
        # admin@test.com already exists from admin_user fixture
        response = client.post(
            "/api/admin/users",
            json={
                "email": "admin@test.com",
                "password": "anotherpass",
                "display_name": "Duplicate",
            },
            cookies={"session_token": token},
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_create_user_shows_in_list(self, client, admin_user):
        """A newly created user should appear in GET /admin/users."""
        _, token = admin_user
        # Create user
        client.post(
            "/api/admin/users",
            json={
                "email": "listed@test.com",
                "password": "pass123",
                "display_name": "Listed User",
            },
            cookies={"session_token": token},
        )
        # Verify appears in list
        response = client.get(
            "/api/admin/users",
            cookies={"session_token": token},
        )
        emails = {u["email"] for u in response.json()["users"]}
        assert "listed@test.com" in emails

    def test_delete_user_success(self, client, admin_user, regular_user):
        """DELETE /admin/users/:id should remove the user."""
        user_obj, _ = regular_user
        _, admin_token = admin_user
        response = client.delete(
            f"/api/admin/users/{user_obj.id}",
            cookies={"session_token": admin_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "deleted" in data["message"].lower()
        # Verify user no longer in list
        list_resp = client.get(
            "/api/admin/users",
            cookies={"session_token": admin_token},
        )
        emails = {u["email"] for u in list_resp.json()["users"]}
        assert "user@test.com" not in emails

    def test_delete_user_not_found_404(self, client, admin_user):
        """DELETE /admin/users/:id with non-existent id returns 404."""
        _, token = admin_user
        response = client.delete(
            "/api/admin/users/99999",
            cookies={"session_token": token},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_self_rejected(self, client, admin_user):
        """Admin cannot delete themselves."""
        user_obj, token = admin_user
        response = client.delete(
            f"/api/admin/users/{user_obj.id}",
            cookies={"session_token": token},
        )
        assert response.status_code == 400
        assert "yourself" in response.json()["detail"].lower()
