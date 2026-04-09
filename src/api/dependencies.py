"""FastAPI dependencies for database and Redis connections."""

from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import Settings
from src.database import DatabaseManager, ConversationRepository
from src.pdf.store import DocumentStore
from src.redis import RedisManager, JobQueue


# Global instances (initialized in main.py startup)
db_manager: DatabaseManager | None = None
redis_manager: RedisManager | None = None
job_queue: JobQueue | None = None
document_store: DocumentStore | None = None


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session.

    Yields:
        AsyncSession: Database session
    """
    if db_manager is None:
        raise RuntimeError("Database not initialized")

    async with db_manager.get_session() as session:
        yield session


async def get_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ConversationRepository:
    """
    Get conversation repository.

    Args:
        session: Database session

    Returns:
        ConversationRepository instance
    """
    return ConversationRepository(session)


def get_job_queue() -> JobQueue:
    """
    Get job queue.

    Returns:
        JobQueue instance

    Raises:
        RuntimeError: If Redis not initialized
    """
    if job_queue is None:
        raise RuntimeError("Redis not initialized")
    return job_queue


def get_document_store() -> DocumentStore:
    """
    Get document store.

    Returns:
        DocumentStore instance

    Raises:
        RuntimeError: If DocumentStore not initialized
    """
    if document_store is None:
        raise RuntimeError("DocumentStore not initialized")
    return document_store
