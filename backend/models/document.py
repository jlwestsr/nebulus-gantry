from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class Document(Base):
    """A document in the knowledge vault."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    collection_id = Column(
        Integer, ForeignKey("collections.id", ondelete="SET NULL"), nullable=True
    )
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)  # pdf, txt, csv, docx
    file_size = Column(Integer, nullable=False)  # bytes
    chunk_count = Column(Integer, default=0)
    status = Column(String(20), default="processing")  # processing, ready, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="documents")
    collection = relationship("Collection", back_populates="documents")
