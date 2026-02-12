from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    username = Column(String, unique=True, nullable=True)
    role = Column(String, default="user")  # "user" or "admin"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
