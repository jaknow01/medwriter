#!/usr/bin/env python3
"""Verification script for Phase Two implementation."""

import asyncio
from uuid import uuid4
from loguru import logger

from src.config.settings import Settings
from src.database import DatabaseManager, ConversationRepository
from src.redis import RedisManager, JobQueue


async def verify_database():
    """Verify database connection and operations."""
    logger.info("=" * 50)
    logger.info("Testing Database Connection")
    logger.info("=" * 50)

    try:
        settings = Settings()
        db_manager = DatabaseManager(settings.database_url)

        # Initialize database
        await db_manager.initialize_db()
        logger.info("✓ Database initialized successfully")

        # Test creating conversation
        async with db_manager.get_session() as session:
            repo = ConversationRepository(session)

            # Create conversation
            conv = await repo.create_conversation(title="Test Conversation")
            logger.info(f"✓ Created conversation: {conv.conv_id}")

            # Add messages
            await repo.add_message(conv.conv_id, role="User", content="Test query")
            await repo.add_message(conv.conv_id, role="AI", content="Test response")
            logger.info("✓ Added messages to conversation")

            # Retrieve messages
            messages = await repo.get_messages(conv.conv_id)
            logger.info(f"✓ Retrieved {len(messages)} messages")

            # Update title
            await repo.update_title(conv.conv_id, "Updated Title")
            logger.info("✓ Updated conversation title")

        await db_manager.close()
        logger.info("✓ Database connection closed")
        return True

    except Exception as e:
        logger.error(f"✗ Database test failed: {e}")
        return False


async def verify_redis():
    """Verify Redis connection and job queue."""
    logger.info("\n" + "=" * 50)
    logger.info("Testing Redis Connection")
    logger.info("=" * 50)

    try:
        settings = Settings()
        redis_manager = RedisManager(settings.redis_url)

        # Connect to Redis
        await redis_manager.connect()
        logger.info("✓ Connected to Redis")

        # Test ping
        ping_result = await redis_manager.ping()
        logger.info(f"✓ Redis ping: {ping_result}")

        # Test job queue
        job_queue = JobQueue(redis_manager.client)

        # Create job
        conv_id = uuid4()
        job_id = await job_queue.create_job(conv_id, "Test query")
        logger.info(f"✓ Created job: {job_id}")

        # Get job status
        job_data = await job_queue.get_job_status(job_id)
        logger.info(f"✓ Job status: {job_data['status']}")

        # Acquire job
        worker_id = "test-worker"
        acquired = await job_queue.acquire_job(worker_id)
        logger.info(f"✓ Acquired job by worker: {acquired['worker_id']}")

        # Complete job
        await job_queue.complete_job(job_id, "Test result")
        final_status = await job_queue.get_job_status(job_id)
        logger.info(f"✓ Job completed with status: {final_status['status']}")

        # Clean up
        await redis_manager.client.flushdb()
        await redis_manager.close()
        logger.info("✓ Redis connection closed")
        return True

    except Exception as e:
        logger.error(f"✗ Redis test failed: {e}")
        return False


async def verify_integration():
    """Verify database and Redis work together."""
    logger.info("\n" + "=" * 50)
    logger.info("Testing Integration")
    logger.info("=" * 50)

    try:
        settings = Settings()

        # Initialize components
        db_manager = DatabaseManager(settings.database_url)
        await db_manager.initialize_db()

        redis_manager = RedisManager(settings.redis_url)
        await redis_manager.connect()
        job_queue = JobQueue(redis_manager.client)

        # Simulate workflow
        conv_id = uuid4()

        # Create job in Redis
        job_id = await job_queue.create_job(conv_id, "What is diabetes?")
        logger.info(f"✓ Created job {job_id} in Redis")

        # Create conversation in database
        async with db_manager.get_session() as session:
            repo = ConversationRepository(session)
            conv = await repo.create_conversation()
            logger.info(f"✓ Created conversation {conv.conv_id} in database")

            # Add messages
            await repo.add_message(conv.conv_id, role="User", content="What is diabetes?")
            await repo.add_message(conv.conv_id, role="AI", content="Diabetes is...")
            logger.info("✓ Added messages to database")

        # Update job status
        await job_queue.complete_job(job_id, "Diabetes is...")
        logger.info("✓ Marked job as complete in Redis")

        # Verify
        job_data = await job_queue.get_job_status(job_id)
        assert job_data["status"] == "Ready"
        logger.info("✓ Integration test passed")

        # Clean up
        await redis_manager.client.flushdb()
        await redis_manager.close()
        await db_manager.close()

        return True

    except Exception as e:
        logger.error(f"✗ Integration test failed: {e}")
        return False


async def main():
    """Run all verification tests."""
    logger.info("Phase Two Verification")
    logger.info("=" * 50)

    results = []

    # Test database
    results.append(("Database", await verify_database()))

    # Test Redis
    results.append(("Redis", await verify_redis()))

    # Test integration
    results.append(("Integration", await verify_integration()))

    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("Verification Summary")
    logger.info("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        logger.info("\n🎉 All Phase Two tests passed!")
    else:
        logger.error("\n❌ Some tests failed. Please check the logs above.")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
