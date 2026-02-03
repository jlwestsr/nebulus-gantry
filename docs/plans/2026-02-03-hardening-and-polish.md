# Hardening & Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close all test coverage gaps for auth and chat, remove the legacy v1 source directory, and apply polish fixes (title, version, .env.example, lint cleanup) to bring Gantry v2 to a fully hardened, production-ready state.

**Architecture:** Test files follow the existing pattern in `backend/tests/test_admin_routes.py` — each uses an in-memory SQLite database with `StaticPool`, overrides `get_db`, and creates users via `AuthService`. Service tests operate directly on `AuthService`/`ChatService` classes with real DB sessions. Route tests use `FastAPI.TestClient`. The LLM service tests mock `httpx` since TabbyAPI isn't available in CI.

**Tech Stack:** pytest, FastAPI TestClient, SQLAlchemy (SQLite in-memory), unittest.mock, httpx (mocked), bcrypt

---

## Task 1: Auth Service Tests

**Files:**

- Create: `backend/tests/test_auth_service.py`

**Context:** `AuthService` (in `backend/services/auth_service.py`) handles user creation, password hashing/verification, session creation, session validation, and session deletion. It uses `bcrypt` directly (not passlib). Sessions expire based on `Settings.session_expire_hours` (default 24h).

**Step 1: Write the test file**

```python
"""Tests for AuthService business logic."""
import os
from datetime import datetime, timedelta
from unittest.mock import patch

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


@pytest.fixture(autouse=True)
def setup_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    yield TestSession
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
def auth(db):
    return AuthService(db)


class TestPasswordHashing:
    def test_hash_password_returns_string(self):
        result = hash_password("secret")
        assert isinstance(result, str)
        assert result != "secret"

    def test_verify_password_correct(self):
        hashed = hash_password("secret")
        assert verify_password("secret", hashed) is True

    def test_verify_password_wrong(self):
        hashed = hash_password("secret")
        assert verify_password("wrong", hashed) is False


class TestCreateUser:
    def test_create_user_returns_user(self, auth):
        user = auth.create_user("a@b.com", "pass", "Alice")
        assert user.email == "a@b.com"
        assert user.display_name == "Alice"
        assert user.role == "user"
        assert user.id is not None

    def test_create_user_hashes_password(self, auth):
        user = auth.create_user("a@b.com", "pass", "Alice")
        assert user.password_hash != "pass"
        assert verify_password("pass", user.password_hash)

    def test_create_user_custom_role(self, auth):
        user = auth.create_user("admin@b.com", "pass", "Admin", role="admin")
        assert user.role == "admin"


class TestAuthenticate:
    def test_authenticate_success(self, auth):
        auth.create_user("a@b.com", "pass", "Alice")
        result = auth.authenticate("a@b.com", "pass")
        assert result is not None
        assert result.email == "a@b.com"

    def test_authenticate_wrong_password(self, auth):
        auth.create_user("a@b.com", "pass", "Alice")
        assert auth.authenticate("a@b.com", "wrong") is None

    def test_authenticate_unknown_email(self, auth):
        assert auth.authenticate("unknown@b.com", "pass") is None


class TestSessions:
    def test_create_session_returns_token(self, auth):
        user = auth.create_user("a@b.com", "pass", "Alice")
        token = auth.create_session(user.id)
        assert isinstance(token, str)
        assert len(token) > 20

    def test_validate_session_returns_user(self, auth):
        user = auth.create_user("a@b.com", "pass", "Alice")
        token = auth.create_session(user.id)
        result = auth.validate_session(token)
        assert result is not None
        assert result.id == user.id

    def test_validate_session_invalid_token(self, auth):
        assert auth.validate_session("nonexistent") is None

    def test_validate_session_expired(self, auth, db):
        user = auth.create_user("a@b.com", "pass", "Alice")
        token = auth.create_session(user.id)
        # Manually expire the session
        session_obj = db.query(Session).filter(Session.token == token).first()
        session_obj.expires_at = datetime.utcnow() - timedelta(hours=1)
        db.commit()
        assert auth.validate_session(token) is None

    def test_delete_session_success(self, auth):
        user = auth.create_user("a@b.com", "pass", "Alice")
        token = auth.create_session(user.id)
        assert auth.delete_session(token) is True
        assert auth.validate_session(token) is None

    def test_delete_session_nonexistent(self, auth):
        assert auth.delete_session("nonexistent") is False
```

**Step 2: Run tests to verify they pass**

Run: `cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry && python -m pytest backend/tests/test_auth_service.py -v`

Expected: All 13 tests PASS

**Step 3: Commit**

```bash
git add backend/tests/test_auth_service.py
git commit -m "test: add AuthService unit tests (password hashing, sessions, auth)"
```

---

## Task 2: Auth Routes Tests

**Files:**

- Create: `backend/tests/test_auth_routes.py`

**Context:** The auth router (`backend/routers/auth.py`) exposes three endpoints: `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`. Login sets an httponly cookie. Logout deletes it. `/me` returns the current user via `get_current_user` dependency.

**Step 1: Write the test file**

```python
"""Tests for auth route endpoints (login, logout, me)."""
import os

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


@pytest.fixture(autouse=True)
def setup_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestSession
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
def user_with_password(db):
    """Create a user and return (user, plaintext_password)."""
    auth = AuthService(db)
    user = auth.create_user(
        email="alice@test.com",
        password="correctpassword",
        display_name="Alice",
        role="user",
    )
    return user, "correctpassword"


@pytest.fixture
def authed_client(client, db, user_with_password):
    """Return a TestClient with a valid session cookie set."""
    user, password = user_with_password
    auth = AuthService(db)
    token = auth.create_session(user.id)
    client.cookies.set("session_token", token)
    return client


class TestLogin:
    def test_login_success(self, client, user_with_password):
        user, password = user_with_password
        response = client.post(
            "/api/auth/login",
            json={"email": user.email, "password": password},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Login successful"
        assert "session_token" in response.cookies

    def test_login_wrong_password(self, client, user_with_password):
        user, _ = user_with_password
        response = client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_unknown_email(self, client):
        response = client.post(
            "/api/auth/login",
            json={"email": "nobody@test.com", "password": "anything"},
        )
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 422


class TestLogout:
    def test_logout_clears_cookie(self, authed_client):
        response = authed_client.post("/api/auth/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Logout successful"

    def test_logout_without_cookie(self, client):
        response = client.post("/api/auth/logout")
        assert response.status_code == 200  # Logout is always 200


class TestGetMe:
    def test_me_returns_user(self, authed_client, user_with_password):
        user, _ = user_with_password
        response = authed_client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user.email
        assert data["display_name"] == "Alice"
        assert data["role"] == "user"
        assert "password_hash" not in data
        assert "password" not in data

    def test_me_unauthenticated(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_invalid_token(self, client):
        response = client.get(
            "/api/auth/me",
            cookies={"session_token": "invalid-token"},
        )
        assert response.status_code == 401
```

**Step 2: Run tests to verify they pass**

Run: `cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry && python -m pytest backend/tests/test_auth_routes.py -v`

Expected: All 9 tests PASS

**Step 3: Commit**

```bash
git add backend/tests/test_auth_routes.py
git commit -m "test: add auth route tests (login, logout, /me)"
```

---

## Task 3: Chat Service Tests

**Files:**

- Create: `backend/tests/test_chat_service.py`

**Context:** `ChatService` (in `backend/services/chat_service.py`) provides CRUD for conversations and messages. Key behaviors: `create_conversation` defaults title to "New Conversation", `add_message` updates `conversation.updated_at` and auto-titles from the first user message (truncates at 60 chars with "..." on word boundary), `delete_conversation` cascades to messages, `get_conversation` filters by both `conversation_id` AND `user_id` for ownership.

**Step 1: Write the test file**

```python
"""Tests for ChatService business logic."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.database import Base  # noqa: E402
from backend.models.user import User  # noqa: E402, F401
from backend.models.session import Session  # noqa: E402, F401
from backend.models.conversation import Conversation  # noqa: E402, F401
from backend.models.message import Message  # noqa: E402, F401
from backend.services.auth_service import AuthService  # noqa: E402
from backend.services.chat_service import ChatService  # noqa: E402


@pytest.fixture(autouse=True)
def setup_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    yield TestSession
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
def user(db):
    auth = AuthService(db)
    return auth.create_user("test@test.com", "pass", "Tester")


@pytest.fixture
def chat(db):
    return ChatService(db)


class TestCreateConversation:
    def test_creates_with_default_title(self, chat, user):
        conv = chat.create_conversation(user.id)
        assert conv.title == "New Conversation"
        assert conv.user_id == user.id
        assert conv.id is not None

    def test_creates_with_custom_title(self, chat, user):
        conv = chat.create_conversation(user.id, title="My Chat")
        assert conv.title == "My Chat"


class TestGetConversations:
    def test_returns_user_conversations_ordered(self, chat, user):
        c1 = chat.create_conversation(user.id, title="First")
        c2 = chat.create_conversation(user.id, title="Second")
        result = chat.get_conversations(user.id)
        assert len(result) == 2
        # Most recently updated first
        assert result[0].id == c2.id

    def test_returns_empty_for_no_conversations(self, chat, user):
        assert chat.get_conversations(user.id) == []

    def test_does_not_return_other_users_conversations(self, chat, user, db):
        auth = AuthService(db)
        other = auth.create_user("other@test.com", "pass", "Other")
        chat.create_conversation(other.id, title="Other's Chat")
        assert chat.get_conversations(user.id) == []


class TestGetConversation:
    def test_returns_conversation(self, chat, user):
        conv = chat.create_conversation(user.id)
        result = chat.get_conversation(conv.id, user.id)
        assert result is not None
        assert result.id == conv.id

    def test_returns_none_for_wrong_user(self, chat, user, db):
        auth = AuthService(db)
        other = auth.create_user("other@test.com", "pass", "Other")
        conv = chat.create_conversation(user.id)
        assert chat.get_conversation(conv.id, other.id) is None

    def test_returns_none_for_nonexistent(self, chat, user):
        assert chat.get_conversation(99999, user.id) is None


class TestDeleteConversation:
    def test_deletes_conversation(self, chat, user):
        conv = chat.create_conversation(user.id)
        assert chat.delete_conversation(conv.id, user.id) is True
        assert chat.get_conversation(conv.id, user.id) is None

    def test_returns_false_for_wrong_user(self, chat, user, db):
        auth = AuthService(db)
        other = auth.create_user("other@test.com", "pass", "Other")
        conv = chat.create_conversation(user.id)
        assert chat.delete_conversation(conv.id, other.id) is False

    def test_returns_false_for_nonexistent(self, chat, user):
        assert chat.delete_conversation(99999, user.id) is False


class TestAddMessage:
    def test_adds_message(self, chat, user):
        conv = chat.create_conversation(user.id)
        msg = chat.add_message(conv.id, "user", "Hello")
        assert msg.content == "Hello"
        assert msg.role == "user"
        assert msg.conversation_id == conv.id

    def test_auto_titles_on_first_user_message(self, chat, user):
        conv = chat.create_conversation(user.id)
        assert conv.title == "New Conversation"
        chat.add_message(conv.id, "user", "What is Python?")
        # Refresh
        updated = chat.get_conversation(conv.id, user.id)
        assert updated.title == "What is Python?"

    def test_auto_title_truncates_long_message(self, chat, user):
        conv = chat.create_conversation(user.id)
        long_msg = "This is a very long message that should be truncated because it exceeds sixty characters easily"
        chat.add_message(conv.id, "user", long_msg)
        updated = chat.get_conversation(conv.id, user.id)
        assert len(updated.title) <= 63  # 60 + "..."
        assert updated.title.endswith("...")

    def test_does_not_retitle_on_second_message(self, chat, user):
        conv = chat.create_conversation(user.id)
        chat.add_message(conv.id, "user", "First message")
        chat.add_message(conv.id, "user", "Second message")
        updated = chat.get_conversation(conv.id, user.id)
        assert updated.title == "First message"

    def test_does_not_title_on_assistant_message(self, chat, user):
        conv = chat.create_conversation(user.id)
        chat.add_message(conv.id, "assistant", "Hello there")
        updated = chat.get_conversation(conv.id, user.id)
        assert updated.title == "New Conversation"


class TestGetMessages:
    def test_returns_messages_in_order(self, chat, user):
        conv = chat.create_conversation(user.id)
        chat.add_message(conv.id, "user", "First")
        chat.add_message(conv.id, "assistant", "Second")
        msgs = chat.get_messages(conv.id)
        assert len(msgs) == 2
        assert msgs[0].content == "First"
        assert msgs[1].content == "Second"

    def test_returns_empty_for_no_messages(self, chat, user):
        conv = chat.create_conversation(user.id)
        assert chat.get_messages(conv.id) == []


class TestUpdateTitle:
    def test_updates_title(self, chat, user):
        conv = chat.create_conversation(user.id)
        chat.update_title(conv.id, "New Title")
        updated = chat.get_conversation(conv.id, user.id)
        assert updated.title == "New Title"

    def test_ignores_nonexistent_conversation(self, chat):
        # Should not raise
        chat.update_title(99999, "Title")
```

**Step 2: Run tests to verify they pass**

Run: `cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry && python -m pytest backend/tests/test_chat_service.py -v`

Expected: All 17 tests PASS

**Step 3: Commit**

```bash
git add backend/tests/test_chat_service.py
git commit -m "test: add ChatService unit tests (CRUD, auto-title, ownership)"
```

---

## Task 4: Chat Routes Tests

**Files:**

- Create: `backend/tests/test_chat_routes.py`

**Context:** The chat router (`backend/routers/chat.py`) exposes: `POST /conversations`, `GET /conversations`, `GET /conversations/{id}`, `DELETE /conversations/{id}`, and `POST /conversations/{id}/messages` (streaming). The streaming endpoint depends on `LLMService`, `MemoryService`, and `GraphService` — all must be mocked to avoid external service calls. Search is already tested in `test_search.py`.

**Step 1: Write the test file**

```python
"""Tests for chat route endpoints."""
import os
from unittest.mock import patch, AsyncMock, MagicMock

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
from backend.models.conversation import Conversation  # noqa: E402, F401
from backend.models.message import Message  # noqa: E402, F401
from backend.services.auth_service import AuthService  # noqa: E402
from backend.services.chat_service import ChatService  # noqa: E402


@pytest.fixture(autouse=True)
def setup_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestSession
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
def user_and_token(db):
    auth = AuthService(db)
    user = auth.create_user("chat@test.com", "pass", "ChatUser")
    token = auth.create_session(user.id)
    return user, token


@pytest.fixture
def authed_client(client, user_and_token):
    _, token = user_and_token
    client.cookies.set("session_token", token)
    return client


class TestCreateConversation:
    def test_create_conversation(self, authed_client):
        response = authed_client.post("/api/chat/conversations")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Conversation"
        assert "id" in data

    def test_create_conversation_unauthenticated(self, client):
        response = client.post("/api/chat/conversations")
        assert response.status_code == 401


class TestListConversations:
    def test_list_conversations(self, authed_client):
        authed_client.post("/api/chat/conversations")
        authed_client.post("/api/chat/conversations")
        response = authed_client.get("/api/chat/conversations")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_conversations_empty(self, authed_client):
        response = authed_client.get("/api/chat/conversations")
        assert response.status_code == 200
        assert response.json() == []


class TestGetConversation:
    def test_get_conversation_with_messages(self, authed_client, db, user_and_token):
        user, _ = user_and_token
        # Create via API
        create_resp = authed_client.post("/api/chat/conversations")
        conv_id = create_resp.json()["id"]
        # Add a message directly
        chat_svc = ChatService(db)
        chat_svc.add_message(conv_id, "user", "Hello")
        # Fetch
        response = authed_client.get(f"/api/chat/conversations/{conv_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["conversation"]["id"] == conv_id
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "Hello"

    def test_get_conversation_not_found(self, authed_client):
        response = authed_client.get("/api/chat/conversations/99999")
        assert response.status_code == 404


class TestDeleteConversation:
    def test_delete_conversation(self, authed_client):
        create_resp = authed_client.post("/api/chat/conversations")
        conv_id = create_resp.json()["id"]
        response = authed_client.delete(f"/api/chat/conversations/{conv_id}")
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()
        # Verify gone
        get_resp = authed_client.get(f"/api/chat/conversations/{conv_id}")
        assert get_resp.status_code == 404

    def test_delete_conversation_not_found(self, authed_client):
        response = authed_client.delete("/api/chat/conversations/99999")
        assert response.status_code == 404


class TestSendMessage:
    def test_send_message_streams_response(self, authed_client):
        """POST /conversations/{id}/messages returns a streaming response."""
        create_resp = authed_client.post("/api/chat/conversations")
        conv_id = create_resp.json()["id"]

        async def fake_stream(messages, model="default"):
            yield "Hello "
            yield "world"

        with patch(
            "backend.routers.chat.LLMService"
        ) as MockLLM, patch(
            "backend.routers.chat._create_memory_service"
        ) as mock_mem_factory, patch(
            "backend.routers.chat._create_graph_service"
        ) as mock_graph_factory:
            mock_mem = MagicMock()
            mock_mem.search_similar = AsyncMock(return_value=[])
            mock_mem.embed_message = AsyncMock()
            mock_mem_factory.return_value = mock_mem

            mock_graph = MagicMock()
            mock_graph.extract_entities.return_value = []
            mock_graph_factory.return_value = mock_graph

            mock_llm_instance = MagicMock()
            mock_llm_instance.stream_chat = fake_stream
            MockLLM.return_value = mock_llm_instance

            response = authed_client.post(
                f"/api/chat/conversations/{conv_id}/messages",
                json={"content": "Hi there"},
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            assert "Hello world" in response.text

    def test_send_message_to_nonexistent_conversation(self, authed_client):
        response = authed_client.post(
            "/api/chat/conversations/99999/messages",
            json={"content": "Hi"},
        )
        assert response.status_code == 404

    def test_send_message_unauthenticated(self, client):
        response = client.post(
            "/api/chat/conversations/1/messages",
            json={"content": "Hi"},
        )
        assert response.status_code == 401
```

**Step 2: Run tests to verify they pass**

Run: `cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry && python -m pytest backend/tests/test_chat_routes.py -v`

Expected: All 10 tests PASS

**Step 3: Commit**

```bash
git add backend/tests/test_chat_routes.py
git commit -m "test: add chat route tests (CRUD, streaming, ownership)"
```

---

## Task 5: LLM Service Tests

**Files:**

- Create: `backend/tests/test_llm_service.py`

**Context:** `LLMService` (in `backend/services/llm_service.py`) wraps `httpx.AsyncClient` for OpenAI-compatible chat completions via TabbyAPI. Has two methods: `stream_chat` (async generator yielding content chunks) and `chat` (non-streaming, returns full string). Both gracefully handle errors — yielding/returning error strings rather than raising. Uses `Settings.tabby_host` for the base URL.

**Step 1: Write the test file**

```python
"""Tests for LLMService (stream_chat and chat)."""
import os
import json
from unittest.mock import patch, AsyncMock, MagicMock

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402
import httpx  # noqa: E402

from backend.services.llm_service import LLMService  # noqa: E402


@pytest.fixture
def llm():
    return LLMService()


class TestStreamChat:
    @pytest.mark.asyncio
    async def test_stream_chat_yields_content(self, llm):
        chunk1 = {"choices": [{"delta": {"content": "Hello"}}]}
        chunk2 = {"choices": [{"delta": {"content": " world"}}]}
        lines = [
            f"data: {json.dumps(chunk1)}",
            f"data: {json.dumps(chunk2)}",
            "data: [DONE]",
        ]

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = AsyncMock(return_value=AsyncIterator(lines))

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.stream = MagicMock(return_value=AsyncContextManager(mock_response))

        with patch("backend.services.llm_service.httpx.AsyncClient", return_value=mock_client):
            chunks = []
            async for chunk in llm.stream_chat([{"role": "user", "content": "Hi"}]):
                chunks.append(chunk)
            assert chunks == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_stream_chat_connect_error(self, llm):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.stream = MagicMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with patch("backend.services.llm_service.httpx.AsyncClient", return_value=mock_client):
            chunks = []
            async for chunk in llm.stream_chat([{"role": "user", "content": "Hi"}]):
                chunks.append(chunk)
            assert len(chunks) == 1
            assert "Could not connect" in chunks[0]


class TestChat:
    @pytest.mark.asyncio
    async def test_chat_returns_content(self, llm):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "I am fine"}}]
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("backend.services.llm_service.httpx.AsyncClient", return_value=mock_client):
            result = await llm.chat([{"role": "user", "content": "How are you?"}])
            assert result == "I am fine"

    @pytest.mark.asyncio
    async def test_chat_returns_error_on_failure(self, llm):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=Exception("Timeout"))

        with patch("backend.services.llm_service.httpx.AsyncClient", return_value=mock_client):
            result = await llm.chat([{"role": "user", "content": "Hi"}])
            assert "[Error:" in result


# ── Helpers for async iteration ──────────────────────────────────────────────


class AsyncIterator:
    """Wraps a list into an async iterator for mocking aiter_lines."""
    def __init__(self, items):
        self._items = items
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item


class AsyncContextManager:
    """Wraps a mock response into an async context manager for mocking client.stream."""
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *args):
        pass
```

**Step 2: Run tests to verify they pass**

Run: `cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry && python -m pytest backend/tests/test_llm_service.py -v`

Expected: All 4 tests PASS

Note: Requires `pytest-asyncio`. Check it's installed: `pip show pytest-asyncio`. If not, install it in the backend venv.

**Step 3: Commit**

```bash
git add backend/tests/test_llm_service.py
git commit -m "test: add LLMService tests (streaming, non-streaming, error handling)"
```

---

## Task 6: Remove Legacy src/ Directory

**Files:**

- Remove: `src/nebulus_gantry/` (entire directory tree)
- Modify: `docs/bugs/issue_001_orm_split_brain.md` (mark as resolved)

**Context:** The `src/nebulus_gantry/` directory contains the v1 Chainlit-era codebase. It has duplicate ORM models that cause Pyrefly Language Server crashes (documented in `docs/bugs/issue_001_orm_split_brain.md`). The v2 rewrite lives entirely in `backend/` and `frontend/`. Nothing in the project imports from `src/`. Safe to delete.

**Step 1: Verify nothing imports from src/**

Run: `grep -r "from src" backend/ frontend/ --include="*.py" --include="*.ts" --include="*.tsx" | head -20`
Run: `grep -r "nebulus_gantry" backend/ frontend/ --include="*.py" --include="*.ts" --include="*.tsx" | head -20`

Expected: No matches (confirming no code depends on the legacy directory).

**Step 2: Remove the legacy directory**

```bash
rm -rf src/nebulus_gantry/
```

If `src/` is now empty, remove it too:

```bash
rmdir src/ 2>/dev/null || true
```

**Step 3: Update the bug report**

Replace the **Status** line in `docs/bugs/issue_001_orm_split_brain.md`:

Change: `**Status:** Open`
To: `**Status:** Resolved (2026-02-03) — Legacy src/nebulus_gantry/ directory deleted. v2 backend/ is the sole source of truth.`

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove legacy v1 src/nebulus_gantry/ directory (closes issue_001)"
```

---

## Task 7: Polish Fixes

**Files:**

- Modify: `frontend/index.html:7` (title)
- Modify: `frontend/package.json:4` (version)
- Create: `.env.example`

**Step 1: Fix the HTML title**

In `frontend/index.html`, change:

```html
<title>frontend</title>
```

to:

```html
<title>Nebulus Gantry</title>
```

**Step 2: Fix the package version**

In `frontend/package.json`, change:

```json
"version": "0.0.0",
```

to:

```json
"version": "2.0.0",
```

**Step 3: Create .env.example**

Create `.env.example` at the project root:

```bash
# Database
DATABASE_URL=sqlite:///./data/gantry.db

# Authentication
SECRET_KEY=change-me-in-production
SESSION_EXPIRE_HOURS=24

# ChromaDB (vector memory)
CHROMA_HOST=http://chromadb:8000

# TabbyAPI (LLM inference)
TABBY_HOST=http://tabby:5000

# Frontend (used in docker-compose for Vite)
VITE_API_URL=http://localhost:8000
```

**Step 4: Commit**

```bash
git add frontend/index.html frontend/package.json .env.example
git commit -m "chore: polish — fix page title, set version 2.0.0, add .env.example"
```

---

## Task 8: Run Full Validation

**Files:** None (verification only)

**Step 1: Run the full test suite**

Run: `cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry && bin/gantry validate`

Expected: `pytest` passes. Pre-existing failures in `djlint` and `flake8` (unused imports in conftest, test_model_service, test_graph_service) are acceptable — document them if new ones appear.

**Step 2: Verify test count increased**

Run: `cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry && python -m pytest backend/tests/ -v --co -q | tail -5`

Expected: Test count should be ~90+ (was 36, adding ~53 new tests across 4 files).

---

## Summary

| Task | What | Tests Added |
|------|------|-------------|
| 1 | AuthService unit tests | 13 |
| 2 | Auth route tests | 9 |
| 3 | ChatService unit tests | 17 |
| 4 | Chat route tests | 10 |
| 5 | LLMService tests | 4 |
| 6 | Remove legacy src/ | 0 |
| 7 | Polish (title, version, .env.example) | 0 |
| 8 | Full validation | 0 |
| **Total** | | **~53 new tests** |
