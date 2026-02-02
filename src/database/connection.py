"""Database connection management with async connection pool."""

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from loguru import logger


class DatabaseManager:
    """Manages database connections and session lifecycle."""

    def __init__(self, database_url: str):
        """Initialize database manager.

        Args:
            database_url: PostgreSQL async connection string
        """
        self.database_url = database_url
        self.engine = create_async_engine(
            database_url,
            echo=False,  # Set to True for SQL logging
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # Verify connections before using
        )
        self.async_session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info("DatabaseManager initialized")

    @asynccontextmanager
    async def get_session(self):
        """Get database session with automatic commit/rollback.

        Yields:
            AsyncSession: Database session
        """
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
                logger.debug("Database session committed")
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session rolled back due to error: {e}")
                raise

    async def initialize_db(self):
        """Create all tables if they don't exist."""
        from src.database.models import Base

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified")

    async def close(self):
        """Close database connection pool."""
        await self.engine.dispose()
        logger.info("Database connection pool closed")
