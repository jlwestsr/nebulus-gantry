"""Tests for conversation export functionality."""
import os
import json
import zipfile
import io

# Set test database URL before any backend imports
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402
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
from backend.models.message import Message  # noqa: E402
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


@pytest.fixture
def admin_user(db):
    """Create an admin user and return (user, session_token)."""
    auth = AuthService(db)
    user = auth.create_user(
        email="admin@test.com",
        password="adminpass",
        display_name="Admin User",
        role="admin",
    )
    token = auth.create_session(user.id)
    return user, token


@pytest.fixture
def conversation_with_messages(db, test_user):
    """Create a conversation with some messages."""
    user, _ = test_user
    conv = Conversation(user_id=user.id, title="Test Conversation", pinned=False)
    db.add(conv)
    db.commit()

    msg1 = Message(conversation_id=conv.id, role="user", content="Hello there!")
    msg2 = Message(conversation_id=conv.id, role="assistant", content="Hi! How can I help?")
    msg3 = Message(conversation_id=conv.id, role="user", content="What's the weather?")
    db.add_all([msg1, msg2, msg3])
    db.commit()

    return conv


# ── JSON Export tests ────────────────────────────────────────────────────────


class TestJSONExport:
    """Tests for JSON export functionality."""

    def test_export_json_success(self, client, test_user, conversation_with_messages):
        """Test successful JSON export."""
        _, token = test_user
        conv = conversation_with_messages

        response = client.get(
            f"/api/chat/conversations/{conv.id}/export?format=json",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers.get("content-disposition", "")

        data = response.json()
        assert "conversation" in data
        assert "messages" in data
        assert "exported_at" in data
        assert data["conversation"]["id"] == conv.id
        assert data["conversation"]["title"] == "Test Conversation"
        assert len(data["messages"]) == 3

    def test_export_json_not_found(self, client, test_user):
        """Test JSON export of non-existent conversation returns 404."""
        _, token = test_user
        response = client.get(
            "/api/chat/conversations/99999/export?format=json",
            cookies={"session_token": token},
        )
        assert response.status_code == 404

    def test_export_json_wrong_user(self, client, test_user, db):
        """Test JSON export of another user's conversation returns 404."""
        _, token = test_user

        # Create a conversation belonging to a different user
        auth = AuthService(db)
        other_user = auth.create_user(
            email="other@test.com",
            password="otherpass",
            display_name="Other User",
            role="user",
        )
        conv = Conversation(user_id=other_user.id, title="Other Conv", pinned=False)
        db.add(conv)
        db.commit()

        response = client.get(
            f"/api/chat/conversations/{conv.id}/export?format=json",
            cookies={"session_token": token},
        )
        assert response.status_code == 404

    def test_export_json_unauthenticated(self, client):
        """Test JSON export without authentication returns 401."""
        response = client.get("/api/chat/conversations/1/export?format=json")
        assert response.status_code == 401


# ── PDF Export tests ─────────────────────────────────────────────────────────


# Check if fpdf2 is available
try:
    import fpdf  # noqa: F401
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False


class TestPDFExport:
    """Tests for PDF export functionality."""

    @pytest.mark.skipif(not FPDF_AVAILABLE, reason="fpdf2 not installed")
    def test_export_pdf_success(self, client, test_user, conversation_with_messages):
        """Test successful PDF export."""
        _, token = test_user
        conv = conversation_with_messages

        response = client.get(
            f"/api/chat/conversations/{conv.id}/export?format=pdf",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers.get("content-disposition", "")
        # Check it starts with PDF magic bytes
        assert response.content[:4] == b"%PDF"

    def test_export_pdf_not_found(self, client, test_user):
        """Test PDF export of non-existent conversation returns 404."""
        _, token = test_user
        response = client.get(
            "/api/chat/conversations/99999/export?format=pdf",
            cookies={"session_token": token},
        )
        assert response.status_code == 404

    def test_export_pdf_unauthenticated(self, client):
        """Test PDF export without authentication returns 401."""
        response = client.get("/api/chat/conversations/1/export?format=pdf")
        assert response.status_code == 401


# ── Bulk Export tests ────────────────────────────────────────────────────────


class TestBulkExport:
    """Tests for admin bulk export functionality."""

    def test_bulk_export_all(self, client, admin_user, db):
        """Test bulk export of all conversations."""
        admin, token = admin_user

        # Create some conversations
        conv1 = Conversation(user_id=admin.id, title="Conv 1", pinned=False)
        conv2 = Conversation(user_id=admin.id, title="Conv 2", pinned=False)
        db.add_all([conv1, conv2])
        db.commit()

        msg1 = Message(conversation_id=conv1.id, role="user", content="Hello 1")
        msg2 = Message(conversation_id=conv2.id, role="user", content="Hello 2")
        db.add_all([msg1, msg2])
        db.commit()

        response = client.post(
            "/api/admin/export/bulk",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"

        # Verify ZIP contents
        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            files = zf.namelist()
            assert len(files) == 2
            # Check content of one file
            content = json.loads(zf.read(files[0]))
            assert "conversation" in content
            assert "messages" in content

    def test_bulk_export_filter_by_user(self, client, admin_user, db):
        """Test bulk export filtered by user_id."""
        admin, token = admin_user

        # Create conversations for different users
        auth = AuthService(db)
        other_user = auth.create_user(
            email="other@test.com",
            password="otherpass",
            display_name="Other User",
            role="user",
        )

        conv1 = Conversation(user_id=admin.id, title="Admin Conv", pinned=False)
        conv2 = Conversation(user_id=other_user.id, title="Other Conv", pinned=False)
        db.add_all([conv1, conv2])
        db.commit()

        # Filter by admin's user_id
        response = client.post(
            f"/api/admin/export/bulk?user_id={admin.id}",
            cookies={"session_token": token},
        )
        assert response.status_code == 200

        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            files = zf.namelist()
            assert len(files) == 1
            content = json.loads(zf.read(files[0]))
            assert content["conversation"]["title"] == "Admin Conv"

    def test_bulk_export_filter_by_date(self, client, admin_user, db):
        """Test bulk export filtered by date range."""
        admin, token = admin_user
        now = datetime.now(timezone.utc)

        # Create conversations with different dates
        conv1 = Conversation(
            user_id=admin.id,
            title="Old Conv",
            pinned=False,
            created_at=now - timedelta(days=30),
        )
        conv2 = Conversation(
            user_id=admin.id,
            title="New Conv",
            pinned=False,
            created_at=now - timedelta(days=1),
        )
        db.add_all([conv1, conv2])
        db.commit()

        # Filter by date range (last 7 days) - use simple datetime format without TZ
        date_from = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
        response = client.post(
            f"/api/admin/export/bulk?date_from={date_from}",
            cookies={"session_token": token},
        )
        assert response.status_code == 200

        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            files = zf.namelist()
            assert len(files) == 1
            content = json.loads(zf.read(files[0]))
            assert content["conversation"]["title"] == "New Conv"

    def test_bulk_export_admin_only(self, client, test_user):
        """Test bulk export requires admin role."""
        _, token = test_user  # Regular user, not admin
        response = client.post(
            "/api/admin/export/bulk",
            cookies={"session_token": token},
        )
        assert response.status_code == 403

    def test_bulk_export_unauthenticated(self, client):
        """Test bulk export without authentication returns 401."""
        response = client.post("/api/admin/export/bulk")
        assert response.status_code == 401
