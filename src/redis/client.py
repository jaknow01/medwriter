"""Redis connection management."""

from typing import Optional

import redis.asyncio as redis
from loguru import logger


class RedisManager:
    """Manages Redis connection lifecycle."""

    def __init__(self, redis_url: str):
        """Initialize Redis manager.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None
        logger.info("RedisManager initialized")

    async def connect(self):
        """Connect to Redis server."""
        self.client = await redis.from_url(
            self.redis_url, encoding="utf-8", decode_responses=True
        )
        logger.info(f"Connected to Redis at {self.redis_url}")

    async def close(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

    async def ping(self) -> bool:
        """Check Redis connection health.

        Returns:
            True if connected, False otherwise
        """
        try:
            result = await self.client.ping()
            logger.debug(f"Redis ping successful: {result}")
            return result
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
