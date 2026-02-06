"""Tests for ChatService: CRUD conversations/messages, auto-title, user isolation."""
import os

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
from backend.models.conversation import Conversation  # noqa: E402, F401
from backend.models.message import Message  # noqa: E402, F401
from backend.services.auth_service import AuthService  # noqa: E402
from backend.services.chat_service import ChatService  # noqa: E402


# -- Test database setup ------------------------------------------------------


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


def _make_user(db, email: str = "alice@example.com") -> User:
    """Helper to create a test user via AuthService."""
    auth = AuthService(db)
    return auth.create_user(
        email=email,
        password="testpass",
        display_name=email.split("@")[0].capitalize(),
    )


# -- TestCreateConversation ---------------------------------------------------


class TestCreateConversation:
    """Test ChatService.create_conversation."""

    def test_creates_with_default_title(self, db):
        """Default title is 'New Thread', correct user_id, non-null id."""
        user = _make_user(db)
        chat = ChatService(db)
        conv = chat.create_conversation(user.id)

        assert conv.id is not None
        assert conv.user_id == user.id
        assert conv.title == "New Thread"

    def test_creates_with_custom_title(self, db):
        """Custom title parameter is stored correctly."""
        user = _make_user(db)
        chat = ChatService(db)
        conv = chat.create_conversation(user.id, title="My Custom Chat")

        assert conv.title == "My Custom Chat"


# -- TestGetConversations -----------------------------------------------------


class TestGetConversations:
    """Test ChatService.get_conversations."""

    def test_returns_user_conversations_ordered(self, db):
        """Returns conversations ordered by updated_at descending."""
        user = _make_user(db)
        chat = ChatService(db)

        conv1 = chat.create_conversation(user.id, title="First")
        conv2 = chat.create_conversation(user.id, title="Second")
        # Touch conv1 by adding a message so its updated_at is newer
        chat.add_message(conv1.id, "user", "hello")

        result = chat.get_conversations(user.id)

        assert len(result) == 2
        # conv1 was updated most recently, so it should come first
        assert result[0].id == conv1.id
        assert result[1].id == conv2.id

    def test_returns_empty_for_no_conversations(self, db):
        """Returns empty list when user has no conversations."""
        user = _make_user(db)
        chat = ChatService(db)

        result = chat.get_conversations(user.id)
        assert result == []

    def test_does_not_return_other_users_conversations(self, db):
        """User can only see their own conversations."""
        user_a = _make_user(db, email="a@example.com")
        user_b = _make_user(db, email="b@example.com")
        chat = ChatService(db)

        chat.create_conversation(user_a.id, title="A's chat")
        chat.create_conversation(user_b.id, title="B's chat")

        result_a = chat.get_conversations(user_a.id)
        result_b = chat.get_conversations(user_b.id)

        assert len(result_a) == 1
        assert result_a[0].title == "A's chat"
        assert len(result_b) == 1
        assert result_b[0].title == "B's chat"


# -- TestGetConversation ------------------------------------------------------


class TestGetConversation:
    """Test ChatService.get_conversation."""

    def test_returns_conversation(self, db):
        """Returns conversation by id and user_id."""
        user = _make_user(db)
        chat = ChatService(db)
        conv = chat.create_conversation(user.id, title="Test")

        result = chat.get_conversation(conv.id, user.id)
        assert result is not None
        assert result.id == conv.id
        assert result.title == "Test"

    def test_returns_none_for_wrong_user(self, db):
        """Returns None when a different user tries to access the conversation."""
        user_a = _make_user(db, email="a@example.com")
        user_b = _make_user(db, email="b@example.com")
        chat = ChatService(db)

        conv = chat.create_conversation(user_a.id)

        result = chat.get_conversation(conv.id, user_b.id)
        assert result is None

    def test_returns_none_for_nonexistent(self, db):
        """Returns None for an invalid conversation id."""
        user = _make_user(db)
        chat = ChatService(db)

        result = chat.get_conversation(99999, user.id)
        assert result is None


# -- TestDeleteConversation ---------------------------------------------------


class TestDeleteConversation:
    """Test ChatService.delete_conversation."""

    def test_deletes_conversation(self, db):
        """Deletes conversation and confirms it's gone."""
        user = _make_user(db)
        chat = ChatService(db)
        conv = chat.create_conversation(user.id)

        result = chat.delete_conversation(conv.id, user.id)
        assert result is True
        assert chat.get_conversation(conv.id, user.id) is None

    def test_returns_false_for_wrong_user(self, db):
        """Cannot delete another user's conversation."""
        user_a = _make_user(db, email="a@example.com")
        user_b = _make_user(db, email="b@example.com")
        chat = ChatService(db)

        conv = chat.create_conversation(user_a.id)

        result = chat.delete_conversation(conv.id, user_b.id)
        assert result is False
        # Confirm conversation still exists for original owner
        assert chat.get_conversation(conv.id, user_a.id) is not None

    def test_returns_false_for_nonexistent(self, db):
        """Returns False for an invalid conversation id."""
        user = _make_user(db)
        chat = ChatService(db)

        result = chat.delete_conversation(99999, user.id)
        assert result is False


# -- TestAddMessage -----------------------------------------------------------


class TestAddMessage:
    """Test ChatService.add_message."""

    def test_adds_message(self, db):
        """Creates message with correct content, role, and conversation_id."""
        user = _make_user(db)
        chat = ChatService(db)
        conv = chat.create_conversation(user.id)

        msg = chat.add_message(conv.id, "user", "Hello, world!")

        assert msg.id is not None
        assert msg.conversation_id == conv.id
        assert msg.role == "user"
        assert msg.content == "Hello, world!"

    def test_auto_titles_on_first_user_message(self, db):
        """First user message replaces 'New Thread' title."""
        user = _make_user(db)
        chat = ChatService(db)
        conv = chat.create_conversation(user.id)

        assert conv.title == "New Thread"
        chat.add_message(conv.id, "user", "Tell me about Python")
        db.refresh(conv)

        assert conv.title == "Tell me about Python"

    def test_auto_title_truncates_long_message(self, db):
        """Truncates title at 60 chars with '...' on word boundary."""
        user = _make_user(db)
        chat = ChatService(db)
        conv = chat.create_conversation(user.id)

        # A message longer than 60 characters
        long_msg = "This is a very long message that should be truncated at word boundary for the title"
        chat.add_message(conv.id, "user", long_msg)
        db.refresh(conv)

        assert len(conv.title) <= 63  # 60 chars max + "..."
        assert conv.title.endswith("...")
        assert conv.title != long_msg

    def test_does_not_retitle_on_second_message(self, db):
        """Title stays from first message; second message does not change it."""
        user = _make_user(db)
        chat = ChatService(db)
        conv = chat.create_conversation(user.id)

        chat.add_message(conv.id, "user", "First question")
        db.refresh(conv)
        first_title = conv.title

        chat.add_message(conv.id, "user", "Second question")
        db.refresh(conv)

        assert conv.title == first_title
        assert conv.title == "First question"

    def test_does_not_title_on_assistant_message(self, db):
        """Assistant messages don't trigger auto-title."""
        user = _make_user(db)
        chat = ChatService(db)
        conv = chat.create_conversation(user.id)

        chat.add_message(conv.id, "assistant", "I can help with that")
        db.refresh(conv)

        assert conv.title == "New Thread"


# -- TestGetMessages ----------------------------------------------------------


class TestGetMessages:
    """Test ChatService.get_messages."""

    def test_returns_messages_in_order(self, db):
        """Messages are returned ordered by created_at ascending."""
        user = _make_user(db)
        chat = ChatService(db)
        conv = chat.create_conversation(user.id)

        msg1 = chat.add_message(conv.id, "user", "First")
        msg2 = chat.add_message(conv.id, "assistant", "Second")
        msg3 = chat.add_message(conv.id, "user", "Third")

        messages = chat.get_messages(conv.id)

        assert len(messages) == 3
        assert messages[0].id == msg1.id
        assert messages[1].id == msg2.id
        assert messages[2].id == msg3.id
        assert messages[0].content == "First"
        assert messages[1].content == "Second"
        assert messages[2].content == "Third"

    def test_returns_empty_for_no_messages(self, db):
        """Returns empty list for a conversation with no messages."""
        user = _make_user(db)
        chat = ChatService(db)
        conv = chat.create_conversation(user.id)

        messages = chat.get_messages(conv.id)
        assert messages == []


# -- TestUpdateTitle ----------------------------------------------------------


class TestUpdateTitle:
    """Test ChatService.update_title."""

    def test_updates_title(self, db):
        """Changes the conversation title directly."""
        user = _make_user(db)
        chat = ChatService(db)
        conv = chat.create_conversation(user.id)

        chat.update_title(conv.id, "Renamed Chat")
        db.refresh(conv)

        assert conv.title == "Renamed Chat"

    def test_ignores_nonexistent_conversation(self, db):
        """Does not raise an error for an invalid conversation id."""
        chat = ChatService(db)
        # Should not raise
        chat.update_title(99999, "Ghost Title")
