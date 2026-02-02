"""SQLAlchemy models for conversations and messages."""

from datetime import datetime
import uuid

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Conversation(Base):
    """Conversation model representing a chat session."""

    __tablename__ = "conversations"

    conv_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Conversation(conv_id={self.conv_id}, title={self.title})>"


class Message(Base):
    """Message model representing a single message in a conversation."""

    __tablename__ = "messages"

    mess_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conv_id = Column(
        UUID(as_uuid=True), ForeignKey("conversations.conv_id"), nullable=False
    )
    role = Column(String(20), nullable=False)  # "User" or "AI"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(mess_id={self.mess_id}, role={self.role})>"
