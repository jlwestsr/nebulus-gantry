from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from backend.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    pinned = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Knowledge Vault: document scope for RAG
    document_scope = Column(Text, nullable=True)  # JSON array of doc/collection IDs

    # Personas: assigned persona for this conversation
    persona_id = Column(
        Integer, ForeignKey("personas.id", ondelete="SET NULL"), nullable=True
    )

    user = relationship("User", backref="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
    persona = relationship("Persona")
