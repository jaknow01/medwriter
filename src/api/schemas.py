"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


# Request schemas
class MessageCreate(BaseModel):
    """Request to create a new message."""

    content: str = Field(..., min_length=1, max_length=5000)


class ConversationCreate(BaseModel):
    """Request to create a new conversation."""

    title: str | None = Field(None, max_length=200)


# Response schemas
class MessageResponse(BaseModel):
    """Message response."""

    mess_id: UUID
    role: str
    content: str
    message_type: str = "simple"
    summary: str | None = None
    timestamp: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Conversation response with message count."""

    conv_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    """Detailed conversation response with messages."""

    conv_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []

    class Config:
        from_attributes = True


class JobStatusResponse(BaseModel):
    """Job status response."""

    job_id: str
    conversation_id: str
    status: str  # "Pending", "Processing", "Ready"
    result: str | None = None
    query: str | None = None


class MessageSubmitResponse(BaseModel):
    """Response after submitting a message."""

    mess_id: UUID
    job_id: str
    status: str = "Pending"


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str
