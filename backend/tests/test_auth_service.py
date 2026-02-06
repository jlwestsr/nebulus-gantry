"""Tests for AuthService: password hashing, user creation, authentication, sessions."""
import os
from datetime import datetime, timedelta, timezone

# Set test database URL before any backend imports to avoid the module-level
# create_all in dependencies.py trying to open the default sqlite file.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.database import Base  # noqa: E402
from backend.models.user import User  # noqa: E402, F401
from backend.models.session import Session  # noqa: E402, F401
from backend.services.auth_service import (  # noqa: E402
    AuthService,
    hash_password,
    verify_password,
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
    yield TestSessionLocal
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


# ── Password hashing tests ───────────────────────────────────────────────────


class TestPasswordHashing:
    """Test the standalone hash_password / verify_password helpers."""

    def test_hash_password_returns_string(self):
        """hash_password returns a non-plaintext string."""
        plaintext = "my_secret_password"
        hashed = hash_password(plaintext)
        assert isinstance(hashed, str)
        assert hashed != plaintext

    def test_verify_password_correct(self):
        """verify_password returns True for the correct password."""
        plaintext = "correct_horse_battery"
        hashed = hash_password(plaintext)
        assert verify_password(plaintext, hashed) is True

    def test_verify_password_wrong(self):
        """verify_password returns False for the wrong password."""
        hashed = hash_password("right_password")
        assert verify_password("wrong_password", hashed) is False


# ── User creation tests ──────────────────────────────────────────────────────


class TestCreateUser:
    """Test AuthService.create_user."""

    def test_create_user_returns_user(self, db):
        """create_user returns a User with the correct fields and default role 'user'."""
        auth = AuthService(db)
        user = auth.create_user(
            email="alice@example.com",
            password="pass123",
            display_name="Alice",
        )
        assert isinstance(user, User)
        assert user.email == "alice@example.com"
        assert user.display_name == "Alice"
        assert user.role == "user"
        assert user.id is not None

    def test_create_user_hashes_password(self, db):
        """Stored password_hash is not plaintext and is verifiable."""
        auth = AuthService(db)
        plaintext = "super_secret"
        user = auth.create_user(
            email="bob@example.com",
            password=plaintext,
            display_name="Bob",
        )
        assert user.password_hash != plaintext
        assert verify_password(plaintext, user.password_hash) is True

    def test_create_user_custom_role(self, db):
        """create_user with role='admin' stores the admin role."""
        auth = AuthService(db)
        user = auth.create_user(
            email="admin@example.com",
            password="adminpass",
            display_name="Admin",
            role="admin",
        )
        assert user.role == "admin"


# ── Authentication tests ─────────────────────────────────────────────────────


class TestAuthenticate:
    """Test AuthService.authenticate."""

    def test_authenticate_success(self, db):
        """Correct email + password returns the User."""
        auth = AuthService(db)
        auth.create_user(
            email="carol@example.com",
            password="carolpass",
            display_name="Carol",
        )
        result = auth.authenticate("carol@example.com", "carolpass")
        assert isinstance(result, User)
        assert result.email == "carol@example.com"

    def test_authenticate_wrong_password(self, db):
        """Wrong password returns None."""
        auth = AuthService(db)
        auth.create_user(
            email="dave@example.com",
            password="davepass",
            display_name="Dave",
        )
        result = auth.authenticate("dave@example.com", "wrongpass")
        assert result is None

    def test_authenticate_unknown_email(self, db):
        """Non-existent email returns None."""
        auth = AuthService(db)
        result = auth.authenticate("nobody@example.com", "anypass")
        assert result is None


# ── Session tests ─────────────────────────────────────────────────────────────


class TestSessions:
    """Test AuthService session management: create, validate, expire, delete."""

    def _make_user(self, db) -> tuple[AuthService, User]:
        """Helper to create an AuthService and a test user."""
        auth = AuthService(db)
        user = auth.create_user(
            email="eve@example.com",
            password="evepass",
            display_name="Eve",
        )
        return auth, user

    def test_create_session_returns_token(self, db):
        """create_session returns a string token longer than 20 characters."""
        auth, user = self._make_user(db)
        token = auth.create_session(user.id)
        assert isinstance(token, str)
        assert len(token) > 20

    def test_validate_session_returns_user(self, db):
        """validate_session with a valid token returns the associated User."""
        auth, user = self._make_user(db)
        token = auth.create_session(user.id)
        result = auth.validate_session(token)
        assert isinstance(result, User)
        assert result.id == user.id

    def test_validate_session_invalid_token(self, db):
        """validate_session with a nonexistent token returns None."""
        auth, _ = self._make_user(db)
        result = auth.validate_session("nonexistent-token-value")
        assert result is None

    def test_validate_session_expired(self, db):
        """An expired session returns None from validate_session."""
        auth, user = self._make_user(db)
        token = auth.create_session(user.id)
        # Manually expire the session by setting expires_at to the past
        session_obj = db.query(Session).filter(Session.token == token).first()
        session_obj.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        db.commit()
        result = auth.validate_session(token)
        assert result is None

    def test_delete_session_success(self, db):
        """delete_session removes the session; subsequent validate returns None."""
        auth, user = self._make_user(db)
        token = auth.create_session(user.id)
        assert auth.delete_session(token) is True
        assert auth.validate_session(token) is None

    def test_delete_session_nonexistent(self, db):
        """delete_session with a nonexistent token returns False."""
        auth, _ = self._make_user(db)
        assert auth.delete_session("does-not-exist") is False
