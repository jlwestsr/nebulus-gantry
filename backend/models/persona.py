from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class Persona(Base):
    """A reusable persona with custom system prompt and preferences."""

    __tablename__ = "personas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )  # NULL = system persona
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    system_prompt = Column(Text, nullable=False)
    temperature = Column(Float, default=0.7)
    model_id = Column(String(100), nullable=True)  # Optional preferred model
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="personas")
