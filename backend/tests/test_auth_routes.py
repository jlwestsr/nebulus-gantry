"""Tests for auth routes (login, logout, /me)."""
import os

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


# ── Login tests ──────────────────────────────────────────────────────────────


class TestLogin:
    """Test POST /api/auth/login."""

    def test_login_success(self, client, test_user):
        """POST /api/auth/login with correct credentials returns 200 and sets cookie."""
        response = client.post(
            "/api/auth/login",
            json={"email": "user@test.com", "password": "correctpass"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Login successful"
        assert "session_token" in response.cookies

    def test_login_wrong_password(self, client, test_user):
        """POST /api/auth/login with wrong password returns 401."""
        response = client.post(
            "/api/auth/login",
            json={"email": "user@test.com", "password": "wrongpass"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"

    def test_login_unknown_email(self, client):
        """POST /api/auth/login with unknown email returns 401."""
        response = client.post(
            "/api/auth/login",
            json={"email": "nobody@test.com", "password": "whatever"},
        )
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        """POST /api/auth/login with empty JSON body returns 422."""
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 422


# ── Logout tests ─────────────────────────────────────────────────────────────


class TestLogout:
    """Test POST /api/auth/logout."""

    def test_logout_clears_cookie(self, client, test_user):
        """POST /api/auth/logout with session cookie returns 200."""
        _, token = test_user
        response = client.post(
            "/api/auth/logout",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Logout successful"

    def test_logout_without_cookie(self, client):
        """POST /api/auth/logout without a session cookie still returns 200."""
        response = client.post("/api/auth/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Logout successful"


# ── Get Me tests ─────────────────────────────────────────────────────────────


class TestGetMe:
    """Test GET /api/auth/me."""

    def test_me_returns_user(self, client, test_user):
        """GET /api/auth/me with valid cookie returns user data without password_hash."""
        user_obj, token = test_user
        response = client.get(
            "/api/auth/me",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user@test.com"
        assert data["display_name"] == "Test User"
        assert data["role"] == "user"
        assert "password_hash" not in data
        assert "password" not in data

    def test_me_unauthenticated(self, client):
        """GET /api/auth/me without a cookie returns 401."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_invalid_token(self, client):
        """GET /api/auth/me with an invalid token cookie returns 401."""
        response = client.get(
            "/api/auth/me",
            cookies={"session_token": "invalid-token-value"},
        )
        assert response.status_code == 401
