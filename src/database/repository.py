"""Data access layer for conversations and messages."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.database.models import Conversation, Message


class ConversationRepository:
    """Repository for database operations on conversations and messages."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: Async database session
        """
        self.session = session

    async def create_conversation(
        self, title: Optional[str] = None, conv_id: Optional[UUID] = None
    ) -> Conversation:
        """Create a new conversation.

        Args:
            title: Optional conversation title
            conv_id: Optional conversation ID (generates new UUID if not provided)

        Returns:
            Created Conversation object
        """
        if conv_id:
            conv = Conversation(conv_id=conv_id, title=title)
        else:
            conv = Conversation(title=title)
        self.session.add(conv)
        await self.session.flush()
        logger.info(f"Created conversation {conv.conv_id} with title: {title}")
        return conv

    async def get_conversation(self, conv_id: UUID) -> Optional[Conversation]:
        """Get conversation by ID.

        Args:
            conv_id: Conversation UUID

        Returns:
            Conversation object or None if not found
        """
        result = await self.session.execute(
            select(Conversation).where(Conversation.conv_id == conv_id)
        )
        conv = result.scalar_one_or_none()

        if conv:
            logger.debug(f"Retrieved conversation {conv_id}")
        else:
            logger.debug(f"Conversation {conv_id} not found")

        return conv

    async def update_title(self, conv_id: UUID, title: str):
        """Update conversation title.

        Args:
            conv_id: Conversation UUID
            title: New title
        """
        conv = await self.get_conversation(conv_id)
        if conv:
            conv.title = title
            await self.session.flush()
            logger.info(f"Updated title for conversation {conv_id}: {title}")
        else:
            logger.warning(f"Cannot update title: conversation {conv_id} not found")

    async def add_message(
        self, conv_id: UUID, role: str, content: str
    ) -> Message:
        """Add message to conversation.

        Args:
            conv_id: Conversation UUID
            role: Message role ("User" or "AI")
            content: Message content

        Returns:
            Created Message object
        """
        msg = Message(conv_id=conv_id, role=role, content=content)
        self.session.add(msg)
        await self.session.flush()
        logger.info(f"Added {role} message to conversation {conv_id}")
        return msg

    async def get_messages(self, conv_id: UUID) -> List[Message]:
        """Get all messages for a conversation, ordered by timestamp.

        Args:
            conv_id: Conversation UUID

        Returns:
            List of Message objects
        """
        result = await self.session.execute(
            select(Message)
            .where(Message.conv_id == conv_id)
            .order_by(Message.timestamp)
        )
        messages = list(result.scalars().all())
        logger.debug(f"Retrieved {len(messages)} messages for conversation {conv_id}")
        return messages
