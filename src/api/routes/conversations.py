"""Conversation endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.api.dependencies import get_db_session, get_repository
from src.api.schemas import (
    ConversationResponse,
    ConversationDetailResponse,
    ConversationCreate,
    MessageResponse,
)
from src.database import ConversationRepository
from src.database.models import Conversation, Message

router = APIRouter()


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
):
    """
    List all conversations with pagination.

    Args:
        skip: Number of conversations to skip
        limit: Maximum number of conversations to return
        session: Database session

    Returns:
        List of conversations with message counts
    """
    logger.info(f"Listing conversations (skip={skip}, limit={limit})")

    # Query conversations with message counts
    query = (
        select(
            Conversation,
            func.count(Message.mess_id).label("message_count")
        )
        .outerjoin(Message, Conversation.conv_id == Message.conv_id)
        .group_by(Conversation.conv_id)
        .order_by(desc(Conversation.updated_at))
        .offset(skip)
        .limit(limit)
    )

    result = await session.execute(query)
    conversations_with_counts = result.all()

    # Build response
    response = []
    for conv, msg_count in conversations_with_counts:
        response.append(
            ConversationResponse(
                conv_id=conv.conv_id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=msg_count or 0,
            )
        )

    logger.info(f"Retrieved {len(response)} conversations")
    return response


@router.get("/conversations/{conv_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conv_id: UUID,
    repo: ConversationRepository = Depends(get_repository),
):
    """
    Get conversation details with messages.

    Args:
        conv_id: Conversation UUID
        repo: Conversation repository

    Returns:
        Conversation with all messages

    Raises:
        HTTPException: If conversation not found
    """
    logger.info(f"Getting conversation {conv_id}")

    # Get conversation
    conversation = await repo.get_conversation(conv_id)
    if not conversation:
        logger.warning(f"Conversation {conv_id} not found")
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get messages
    messages = await repo.get_messages(conv_id)

    # Build response
    response = ConversationDetailResponse(
        conv_id=conversation.conv_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            MessageResponse(
                mess_id=msg.mess_id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
            )
            for msg in messages
        ],
    )

    logger.info(f"Retrieved conversation {conv_id} with {len(messages)} messages")
    return response


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    conversation: ConversationCreate,
    repo: ConversationRepository = Depends(get_repository),
):
    """
    Create a new conversation.

    Args:
        conversation: Conversation creation data
        repo: Conversation repository

    Returns:
        Created conversation
    """
    logger.info(f"Creating new conversation with title: {conversation.title}")

    # Create conversation
    new_conv = await repo.create_conversation(title=conversation.title)

    response = ConversationResponse(
        conv_id=new_conv.conv_id,
        title=new_conv.title,
        created_at=new_conv.created_at,
        updated_at=new_conv.updated_at,
        message_count=0,
    )

    logger.info(f"Created conversation {new_conv.conv_id}")
    return response


@router.delete("/conversations/{conv_id}", status_code=204)
async def delete_conversation(
    conv_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Delete a conversation and all its messages.

    Args:
        conv_id: Conversation UUID
        session: Database session

    Raises:
        HTTPException: If conversation not found
    """
    logger.info(f"Deleting conversation {conv_id}")

    # Check if conversation exists
    result = await session.execute(
        select(Conversation).where(Conversation.conv_id == conv_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        logger.warning(f"Conversation {conv_id} not found")
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Delete conversation (messages cascade delete automatically)
    await session.delete(conversation)
    await session.commit()

    logger.info(f"Deleted conversation {conv_id}")
