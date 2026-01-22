from sqlalchemy import (
    JSON,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..database import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, default="Untitled")
    content = Column(String, default="")
    category = Column(String, default="Uncategorized", nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="notes")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    role = Column(String, default="user")
    current_model = Column(String, default="Llama 3.1")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    chats = relationship("Chat", back_populates="user")
    folders = relationship("Folder", back_populates="user")
    notes = relationship("Note", back_populates="user")


class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="folders")
    chats = relationship("Chat", back_populates="folder")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, index=True)  # Chainlit Session ID
    user_id = Column(Integer, ForeignKey("users.id"))
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)
    title = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=True)  # Store thread metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="chats")
    folder = relationship("Folder", back_populates="chats")
    messages = relationship(
        "Message", back_populates="chat", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    cl_id = Column(String, unique=True, nullable=True)  # Chainlit Message UUID
    chat_id = Column(String, ForeignKey("chats.id"))
    author = Column(String)  # User or Assistant
    content = Column(String)
    entities = Column(JSON, nullable=True)  # Store extracted entities
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    chat = relationship("Chat", back_populates="messages")
    feedback = relationship("Feedback", back_populates="message", uselist=False)


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    chat_id = Column(String, ForeignKey("chats.id"))
    message_id = Column(Integer, ForeignKey("messages.id"))
    model = Column(String)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost = Column(Integer, default=0)  # Cost in micro-units
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")
    chat = relationship("Chat")
    message = relationship("Message")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"))
    score = Column(Integer)  # 1 for up, -1 for down (or 0)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    message = relationship("Message", back_populates="feedback")
