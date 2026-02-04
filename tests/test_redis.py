"""Tests for Redis job queue operations."""

import pytest
from uuid import uuid4
import asyncio

from src.redis import RedisManager, JobQueue


@pytest.fixture
async def redis_manager():
    """Create Redis manager for testing."""
    redis_url = "redis://localhost:6379/1"  # Use database 1 for testing
    manager = RedisManager(redis_url)
    await manager.connect()

    # Clean up test database before tests
    await manager.client.flushdb()

    yield manager

    # Clean up after tests
    await manager.client.flushdb()
    await manager.close()


@pytest.fixture
async def job_queue(redis_manager):
    """Create job queue for testing."""
    return JobQueue(redis_manager.client)


class TestRedisConnection:
    """Test Redis connection."""

    async def test_redis_connection(self, redis_manager):
        """Test Redis connects successfully."""
        assert redis_manager.client is not None

    async def test_redis_ping(self, redis_manager):
        """Test Redis ping."""
        result = await redis_manager.ping()
        assert result is True


class TestJobQueue:
    """Test job queue operations."""

    async def test_create_job(self, job_queue):
        """Test creating a job."""
        conv_id = uuid4()
        query = "What is diabetes?"

        job_id = await job_queue.create_job(conv_id, query)

        assert job_id == str(conv_id)

        # Verify job exists in Redis
        job_data = await job_queue.get_job_status(job_id)
        assert job_data is not None
        assert job_data["conversation_id"] == str(conv_id)
        assert job_data["query"] == query
        assert job_data["status"] == "Pending"
        assert job_data["result"] == "Pending"

    async def test_acquire_job(self, job_queue):
        """Test acquiring a pending job."""
        conv_id = uuid4()
        await job_queue.create_job(conv_id, "Test query")

        # Acquire job
        worker_id = "worker-test-1"
        job_data = await job_queue.acquire_job(worker_id)

        assert job_data is not None
        assert job_data["conversation_id"] == str(conv_id)
        assert job_data["status"] == "Processing"
        assert job_data["worker_id"] == worker_id

    async def test_acquire_job_no_pending(self, job_queue):
        """Test acquiring job when none are pending."""
        worker_id = "worker-test-1"
        job_data = await job_queue.acquire_job(worker_id)

        assert job_data is None

    async def test_acquire_job_locking(self, job_queue):
        """Test that only one worker can acquire a job."""
        conv_id = uuid4()
        await job_queue.create_job(conv_id, "Test query")

        # Two workers try to acquire
        worker1 = "worker-1"
        worker2 = "worker-2"

        job1 = await job_queue.acquire_job(worker1)
        job2 = await job_queue.acquire_job(worker2)

        # Only one should succeed
        assert job1 is not None
        assert job2 is None
        assert job1["worker_id"] == worker1

    async def test_complete_job(self, job_queue):
        """Test completing a job."""
        conv_id = uuid4()
        job_id = await job_queue.create_job(conv_id, "Test query")

        # Acquire and complete
        worker_id = "worker-test-1"
        await job_queue.acquire_job(worker_id)

        result = "Test result from agent"
        await job_queue.complete_job(job_id, result)

        # Verify job status
        job_data = await job_queue.get_job_status(job_id)
        assert job_data["status"] == "Ready"
        assert job_data["result"] == result

    async def test_get_job_status(self, job_queue):
        """Test getting job status."""
        conv_id = uuid4()
        job_id = await job_queue.create_job(conv_id, "Test query")

        status = await job_queue.get_job_status(job_id)

        assert status is not None
        assert status["conversation_id"] == str(conv_id)
        assert status["status"] == "Pending"

    async def test_get_nonexistent_job_status(self, job_queue):
        """Test getting status of non-existent job."""
        fake_id = str(uuid4())
        status = await job_queue.get_job_status(fake_id)

        assert status is None

    async def test_concurrent_job_acquisition(self, job_queue):
        """Test concurrent job acquisition by multiple workers."""
        # Create multiple jobs
        job_ids = []
        for i in range(3):
            conv_id = uuid4()
            job_id = await job_queue.create_job(conv_id, f"Query {i}")
            job_ids.append(job_id)

        # Multiple workers try to acquire jobs concurrently
        async def acquire_for_worker(worker_id):
            return await job_queue.acquire_job(worker_id)

        results = await asyncio.gather(
            acquire_for_worker("worker-1"),
            acquire_for_worker("worker-2"),
            acquire_for_worker("worker-3"),
            acquire_for_worker("worker-4"),
        )

        # Only 3 should succeed (one per job)
        successful = [r for r in results if r is not None]
        assert len(successful) == 3

        # Each job should be acquired by different worker
        worker_ids = [r["worker_id"] for r in successful]
        assert len(set(worker_ids)) == 3

    async def test_job_expiration(self, job_queue):
        """Test that jobs expire after TTL."""
        # Note: This test would require waiting 3600 seconds
        # For now, we just verify the TTL is set correctly
        # In production, you'd mock time or use a shorter TTL for testing
        conv_id = uuid4()
        job_id = await job_queue.create_job(conv_id, "Test query")

        # Verify job exists
        job_data = await job_queue.get_job_status(job_id)
        assert job_data is not None

        # Check TTL is set (should be around 3600 seconds)
        ttl = await job_queue.redis.ttl(f"job:{job_id}")
        assert ttl > 0
        assert ttl <= 3600
