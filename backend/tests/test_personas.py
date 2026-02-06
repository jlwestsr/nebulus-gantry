"""Tests for PersonaService and persona routes."""
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
from backend.models.collection import Collection  # noqa: E402, F401
from backend.models.document import Document  # noqa: E402, F401
from backend.models.persona import Persona  # noqa: E402, F401
from backend.services.auth_service import AuthService  # noqa: E402
from backend.services.persona_service import PersonaService  # noqa: E402
from backend.services.chat_service import ChatService  # noqa: E402


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
    """Helper to create a test user."""
    auth = AuthService(db)
    return auth.create_user(
        email=email,
        password="testpass",
        display_name=email.split("@")[0].capitalize(),
    )


# -- Test Persona CRUD --------------------------------------------------------


class TestPersonaCRUD:
    """Test persona CRUD operations."""

    def test_create_user_persona(self, db):
        """Creates a user persona with correct fields."""
        user = _make_user(db)
        service = PersonaService(db)

        persona = service.create_persona(
            user_id=user.id,
            name="Helpful Assistant",
            system_prompt="You are a helpful assistant.",
            description="A friendly helper",
            temperature=0.8,
        )

        assert persona.id is not None
        assert persona.user_id == user.id
        assert persona.name == "Helpful Assistant"
        assert persona.system_prompt == "You are a helpful assistant."
        assert persona.temperature == 0.8

    def test_create_system_persona(self, db):
        """Creates a system persona (user_id=None)."""
        service = PersonaService(db)

        persona = service.create_persona(
            user_id=None,  # System persona
            name="Default Assistant",
            system_prompt="You are the default assistant.",
        )

        assert persona.id is not None
        assert persona.user_id is None

    def test_list_personas_includes_user_and_system(self, db):
        """User sees their own personas plus system personas."""
        user = _make_user(db)
        service = PersonaService(db)

        # Create system persona
        service.create_persona(None, "System", "System prompt")
        # Create user persona
        service.create_persona(user.id, "User's", "User prompt")

        personas = service.list_personas(user.id)

        assert len(personas) == 2
        names = [p.name for p in personas]
        assert "System" in names
        assert "User's" in names

    def test_user_cannot_see_other_users_personas(self, db):
        """Users cannot see other users' personas."""
        user_a = _make_user(db, "a@example.com")
        user_b = _make_user(db, "b@example.com")
        service = PersonaService(db)

        service.create_persona(user_a.id, "A's Persona", "Prompt A")

        personas_b = service.list_personas(user_b.id)
        names = [p.name for p in personas_b]

        assert "A's Persona" not in names

    def test_get_persona_own(self, db):
        """User can get their own persona."""
        user = _make_user(db)
        service = PersonaService(db)

        persona = service.create_persona(user.id, "Test", "Prompt")
        result = service.get_persona(persona.id, user.id)

        assert result is not None
        assert result.name == "Test"

    def test_get_persona_system(self, db):
        """User can get system personas."""
        user = _make_user(db)
        service = PersonaService(db)

        persona = service.create_persona(None, "System", "Prompt")
        result = service.get_persona(persona.id, user.id)

        assert result is not None
        assert result.name == "System"

    def test_get_persona_other_user(self, db):
        """Cannot get another user's persona."""
        user_a = _make_user(db, "a@example.com")
        user_b = _make_user(db, "b@example.com")
        service = PersonaService(db)

        persona = service.create_persona(user_a.id, "Private", "Prompt")
        result = service.get_persona(persona.id, user_b.id)

        assert result is None

    def test_update_own_persona(self, db):
        """User can update their own persona."""
        user = _make_user(db)
        service = PersonaService(db)

        persona = service.create_persona(user.id, "Original", "Original prompt")
        updated = service.update_persona(
            persona.id,
            user.id,
            name="Updated",
            system_prompt="New prompt",
            temperature=0.5,
        )

        assert updated is not None
        assert updated.name == "Updated"
        assert updated.system_prompt == "New prompt"
        assert updated.temperature == 0.5

    def test_cannot_update_other_users_persona(self, db):
        """Cannot update another user's persona."""
        user_a = _make_user(db, "a@example.com")
        user_b = _make_user(db, "b@example.com")
        service = PersonaService(db)

        persona = service.create_persona(user_a.id, "A's", "Prompt")
        result = service.update_persona(persona.id, user_b.id, name="Hacked")

        assert result is None

    def test_cannot_update_system_persona_as_user(self, db):
        """Regular users cannot update system personas."""
        user = _make_user(db)
        service = PersonaService(db)

        persona = service.create_persona(None, "System", "Prompt")
        result = service.update_persona(persona.id, user.id, name="Hacked")

        assert result is None

    def test_delete_own_persona(self, db):
        """User can delete their own persona."""
        user = _make_user(db)
        service = PersonaService(db)

        persona = service.create_persona(user.id, "To Delete", "Prompt")
        result = service.delete_persona(persona.id, user.id)

        assert result is True
        assert service.get_persona(persona.id, user.id) is None

    def test_cannot_delete_other_users_persona(self, db):
        """Cannot delete another user's persona."""
        user_a = _make_user(db, "a@example.com")
        user_b = _make_user(db, "b@example.com")
        service = PersonaService(db)

        persona = service.create_persona(user_a.id, "A's", "Prompt")
        result = service.delete_persona(persona.id, user_b.id)

        assert result is False

    def test_cannot_delete_system_persona_as_user(self, db):
        """Regular users cannot delete system personas."""
        user = _make_user(db)
        service = PersonaService(db)

        persona = service.create_persona(None, "System", "Prompt")
        result = service.delete_persona(persona.id, user.id)

        assert result is False


# -- Test Admin System Persona Operations -------------------------------------


class TestAdminSystemPersonas:
    """Test admin operations on system personas."""

    def test_list_system_personas(self, db):
        """Lists only system personas."""
        service = PersonaService(db)
        user = _make_user(db)

        service.create_persona(None, "System 1", "Prompt 1")
        service.create_persona(None, "System 2", "Prompt 2")
        service.create_persona(user.id, "User's", "User prompt")

        system_personas = service.list_system_personas()

        assert len(system_personas) == 2
        names = [p.name for p in system_personas]
        assert "System 1" in names
        assert "System 2" in names
        assert "User's" not in names

    def test_update_system_persona(self, db):
        """Admin can update system personas."""
        service = PersonaService(db)

        persona = service.create_persona(None, "System", "Original")
        updated = service.update_system_persona(
            persona.id,
            name="Updated System",
            system_prompt="New prompt",
        )

        assert updated is not None
        assert updated.name == "Updated System"

    def test_delete_system_persona(self, db):
        """Admin can delete system personas."""
        service = PersonaService(db)

        persona = service.create_persona(None, "System", "Prompt")
        result = service.delete_system_persona(persona.id)

        assert result is True


# -- Test Conversation Persona Assignment -------------------------------------


class TestConversationPersona:
    """Test assigning personas to conversations."""

    def test_set_conversation_persona(self, db):
        """Assigns a persona to a conversation."""
        user = _make_user(db)
        persona_service = PersonaService(db)
        chat_service = ChatService(db)

        persona = persona_service.create_persona(user.id, "Helper", "Be helpful")
        conversation = chat_service.create_conversation(user.id)

        result = persona_service.set_conversation_persona(
            conversation.id, persona.id, user.id
        )

        assert result is not None
        assert result.persona_id == persona.id

    def test_unset_conversation_persona(self, db):
        """Removes persona from a conversation."""
        user = _make_user(db)
        persona_service = PersonaService(db)
        chat_service = ChatService(db)

        persona = persona_service.create_persona(user.id, "Helper", "Be helpful")
        conversation = chat_service.create_conversation(user.id)

        # Set then unset
        persona_service.set_conversation_persona(conversation.id, persona.id, user.id)
        result = persona_service.set_conversation_persona(conversation.id, None, user.id)

        assert result is not None
        assert result.persona_id is None

    def test_cannot_assign_other_users_persona(self, db):
        """Cannot assign another user's persona to own conversation."""
        user_a = _make_user(db, "a@example.com")
        user_b = _make_user(db, "b@example.com")
        persona_service = PersonaService(db)
        chat_service = ChatService(db)

        persona_a = persona_service.create_persona(user_a.id, "A's", "Prompt")
        conversation_b = chat_service.create_conversation(user_b.id)

        result = persona_service.set_conversation_persona(
            conversation_b.id, persona_a.id, user_b.id
        )

        assert result is None

    def test_can_assign_system_persona(self, db):
        """Can assign a system persona to a conversation."""
        user = _make_user(db)
        persona_service = PersonaService(db)
        chat_service = ChatService(db)

        system_persona = persona_service.create_persona(None, "System", "System prompt")
        conversation = chat_service.create_conversation(user.id)

        result = persona_service.set_conversation_persona(
            conversation.id, system_persona.id, user.id
        )

        assert result is not None
        assert result.persona_id == system_persona.id

    def test_delete_persona_clears_from_conversations(self, db):
        """Deleting a persona clears it from conversations."""
        user = _make_user(db)
        persona_service = PersonaService(db)
        chat_service = ChatService(db)

        persona = persona_service.create_persona(user.id, "Temp", "Prompt")
        conversation = chat_service.create_conversation(user.id)
        persona_service.set_conversation_persona(conversation.id, persona.id, user.id)

        # Delete persona
        persona_service.delete_persona(persona.id, user.id)

        # Refresh conversation
        db.refresh(conversation)
        assert conversation.persona_id is None


# -- Test Persona Temperature -------------------------------------------------


class TestPersonaTemperature:
    """Test persona temperature settings."""

    def test_default_temperature(self, db):
        """Default temperature is 0.7."""
        user = _make_user(db)
        service = PersonaService(db)

        persona = service.create_persona(user.id, "Default", "Prompt")

        assert persona.temperature == 0.7

    def test_custom_temperature(self, db):
        """Can set custom temperature."""
        user = _make_user(db)
        service = PersonaService(db)

        persona = service.create_persona(
            user.id, "Creative", "Be creative", temperature=1.5
        )

        assert persona.temperature == 1.5

    def test_update_temperature(self, db):
        """Can update temperature."""
        user = _make_user(db)
        service = PersonaService(db)

        persona = service.create_persona(user.id, "Test", "Prompt", temperature=0.5)
        updated = service.update_persona(persona.id, user.id, temperature=1.0)

        assert updated.temperature == 1.0


# -- Test Default Persona -----------------------------------------------------


class TestDefaultPersona:
    """Test default persona flag."""

    def test_is_default_flag(self, db):
        """Can set is_default flag on persona."""
        service = PersonaService(db)

        persona = service.create_persona(
            None, "Default System", "Prompt", is_default=True
        )

        assert persona.is_default is True

    def test_default_sorted_first(self, db):
        """Default personas are sorted first."""
        user = _make_user(db)
        service = PersonaService(db)

        service.create_persona(None, "Regular", "Prompt", is_default=False)
        service.create_persona(None, "Default", "Prompt", is_default=True)

        personas = service.list_personas(user.id)

        # Default should be first
        assert personas[0].name == "Default"
