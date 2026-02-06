"""
Persona Service for managing reusable personas.

Provides:
- Persona CRUD operations
- Access control (users can only manage their own personas)
- System personas (admin-managed, user_id=NULL)
- Conversation persona assignment
"""
import logging
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import or_

from backend.models.persona import Persona
from backend.models.conversation import Conversation

logger = logging.getLogger(__name__)


class PersonaService:
    """Service for managing personas."""

    def __init__(self, db: DBSession):
        self.db = db

    def create_persona(
        self,
        user_id: int | None,
        name: str,
        system_prompt: str,
        description: str | None = None,
        temperature: float = 0.7,
        model_id: str | None = None,
        is_default: bool = False,
    ) -> Persona:
        """Create a new persona.

        Args:
            user_id: User ID (None for system personas)
            name: Persona name
            system_prompt: The system prompt for this persona
            description: Optional description
            temperature: LLM temperature (0.0-2.0)
            model_id: Optional preferred model ID
            is_default: Whether this is the default persona
        """
        persona = Persona(
            user_id=user_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
            temperature=temperature,
            model_id=model_id,
            is_default=is_default,
        )
        self.db.add(persona)
        self.db.commit()
        self.db.refresh(persona)
        return persona

    def list_personas(self, user_id: int) -> list[Persona]:
        """List all personas available to a user (own + system)."""
        return (
            self.db.query(Persona)
            .filter(
                or_(
                    Persona.user_id == user_id,
                    Persona.user_id.is_(None),  # System personas
                )
            )
            .order_by(Persona.is_default.desc(), Persona.created_at.desc())
            .all()
        )

    def list_system_personas(self) -> list[Persona]:
        """List all system personas (admin only)."""
        return (
            self.db.query(Persona)
            .filter(Persona.user_id.is_(None))
            .order_by(Persona.is_default.desc(), Persona.created_at.desc())
            .all()
        )

    def get_persona(self, persona_id: int, user_id: int) -> Persona | None:
        """Get a persona by ID (must be owned by user or be a system persona)."""
        return (
            self.db.query(Persona)
            .filter(
                Persona.id == persona_id,
                or_(
                    Persona.user_id == user_id,
                    Persona.user_id.is_(None),
                ),
            )
            .first()
        )

    def get_persona_by_id(self, persona_id: int) -> Persona | None:
        """Get a persona by ID without access control (for internal use)."""
        return self.db.query(Persona).filter(Persona.id == persona_id).first()

    def update_persona(
        self,
        persona_id: int,
        user_id: int,
        name: str | None = None,
        description: str | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
        model_id: str | None = None,
    ) -> Persona | None:
        """Update a persona (only own personas, not system)."""
        persona = (
            self.db.query(Persona)
            .filter(
                Persona.id == persona_id,
                Persona.user_id == user_id,  # Must own the persona
            )
            .first()
        )
        if not persona:
            return None

        if name is not None:
            persona.name = name
        if description is not None:
            persona.description = description
        if system_prompt is not None:
            persona.system_prompt = system_prompt
        if temperature is not None:
            persona.temperature = temperature
        if model_id is not None:
            persona.model_id = model_id

        self.db.commit()
        self.db.refresh(persona)
        return persona

    def update_system_persona(
        self,
        persona_id: int,
        name: str | None = None,
        description: str | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
        model_id: str | None = None,
        is_default: bool | None = None,
    ) -> Persona | None:
        """Update a system persona (admin only)."""
        persona = (
            self.db.query(Persona)
            .filter(
                Persona.id == persona_id,
                Persona.user_id.is_(None),
            )
            .first()
        )
        if not persona:
            return None

        if name is not None:
            persona.name = name
        if description is not None:
            persona.description = description
        if system_prompt is not None:
            persona.system_prompt = system_prompt
        if temperature is not None:
            persona.temperature = temperature
        if model_id is not None:
            persona.model_id = model_id
        if is_default is not None:
            persona.is_default = is_default

        self.db.commit()
        self.db.refresh(persona)
        return persona

    def delete_persona(self, persona_id: int, user_id: int) -> bool:
        """Delete a persona (only own personas, not system)."""
        persona = (
            self.db.query(Persona)
            .filter(
                Persona.id == persona_id,
                Persona.user_id == user_id,
            )
            .first()
        )
        if not persona:
            return False

        # Clear persona from any conversations using it
        self.db.query(Conversation).filter(
            Conversation.persona_id == persona_id
        ).update({"persona_id": None})

        self.db.delete(persona)
        self.db.commit()
        return True

    def delete_system_persona(self, persona_id: int) -> bool:
        """Delete a system persona (admin only)."""
        persona = (
            self.db.query(Persona)
            .filter(
                Persona.id == persona_id,
                Persona.user_id.is_(None),
            )
            .first()
        )
        if not persona:
            return False

        # Clear persona from any conversations using it
        self.db.query(Conversation).filter(
            Conversation.persona_id == persona_id
        ).update({"persona_id": None})

        self.db.delete(persona)
        self.db.commit()
        return True

    def set_conversation_persona(
        self, conversation_id: int, persona_id: int | None, user_id: int
    ) -> Conversation | None:
        """Set the persona for a conversation."""
        conversation = (
            self.db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .first()
        )
        if not conversation:
            return None

        # Validate persona exists and is accessible
        if persona_id is not None:
            persona = self.get_persona(persona_id, user_id)
            if not persona:
                return None

        conversation.persona_id = persona_id
        self.db.commit()
        self.db.refresh(conversation)
        return conversation
