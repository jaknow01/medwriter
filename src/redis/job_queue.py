"""Job queue operations with distributed locking."""

import json
from typing import Optional, Dict, Any
from uuid import UUID

from loguru import logger


class JobQueue:
    """Job queue manager with Redis-based locking."""

    def __init__(self, redis_client):
        """Initialize job queue.

        Args:
            redis_client: Connected Redis client
        """
        self.redis = redis_client
        self.job_prefix = "job:"
        self.lock_timeout = 300  # 5 minutes in seconds

    async def create_job(
        self,
        conv_id: UUID,
        query: str,
        pdf_chunks: list[dict] | None = None,
    ) -> str:
        """Create a new job in Redis.

        Args:
            conv_id: Conversation UUID
            query: User query
            pdf_chunks: Optional list of PDF chunks, each {"text": str, "filename": str}

        Returns:
            Job ID (same as conversation ID)
        """
        job_id = str(conv_id)
        job_data = {
            "conversation_id": str(conv_id),
            "query": query,
            "status": "Pending",
            "result": "Pending",
        }

        if pdf_chunks:
            job_data["pdf_chunks"] = pdf_chunks

        await self.redis.set(
            f"{self.job_prefix}{job_id}",
            json.dumps(job_data),
            ex=3600,  # Expire after 1 hour
        )

        logger.info(f"Created job {job_id} with status Pending")
        return job_id

    async def acquire_job(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Acquire a pending job with distributed lock.

        Args:
            worker_id: Unique worker identifier

        Returns:
            Job data dict if acquired, None if no jobs available
        """
        # Scan for pending jobs
        async for key in self.redis.scan_iter(f"{self.job_prefix}*"):
            job_data_str = await self.redis.get(key)
            if not job_data_str:
                continue

            job_data = json.loads(job_data_str)

            if job_data["status"] == "Pending":
                # Try to acquire lock
                lock_key = f"lock:{key}"
                acquired = await self.redis.set(
                    lock_key,
                    worker_id,
                    nx=True,  # Only set if not exists
                    ex=self.lock_timeout,
                )

                if acquired:
                    # Update job status to Processing
                    job_data["status"] = "Processing"
                    job_data["worker_id"] = worker_id
                    await self.redis.set(key, json.dumps(job_data))

                    logger.info(f"Worker {worker_id} acquired job from {key}")
                    return job_data

        logger.debug(f"No pending jobs found for worker {worker_id}")
        return None

    async def complete_job(self, job_id: str, result: str):
        """Mark job as completed with result.

        Args:
            job_id: Job identifier
            result: Processing result
        """
        key = f"{self.job_prefix}{job_id}"
        job_data_str = await self.redis.get(key)

        if job_data_str:
            job_data = json.loads(job_data_str)
            job_data["status"] = "Ready"
            job_data["result"] = result
            await self.redis.set(key, json.dumps(job_data))

            # Release lock
            await self.redis.delete(f"lock:{key}")

            logger.info(f"Job {job_id} completed with status Ready")
        else:
            logger.warning(f"Cannot complete job {job_id}: not found")

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status and result.

        Args:
            job_id: Job identifier

        Returns:
            Job data dict or None if not found
        """
        key = f"{self.job_prefix}{job_id}"
        job_data_str = await self.redis.get(key)

        if job_data_str:
            job_data = json.loads(job_data_str)
            logger.debug(f"Job {job_id} status: {job_data['status']}")
            return job_data

        logger.debug(f"Job {job_id} not found")
        return None
