"""Worker polling loop for processing jobs from Redis queue."""

import asyncio
from uuid import UUID
from loguru import logger

from src.config.settings import Settings
from src.worker.worker import Worker
from src.redis import RedisManager, JobQueue


class WorkerPoller:
    """Worker that continuously polls Redis for jobs and processes them."""

    def __init__(self, settings: Settings):
        """
        Initialize worker poller.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.worker: Worker | None = None
        self.redis_manager: RedisManager | None = None
        self.job_queue: JobQueue | None = None
        self.running = False

    async def initialize(self) -> None:
        """Initialize worker and Redis connection."""
        logger.info(f"Initializing worker poller (ID: {self.settings.worker_id})")

        # Initialize worker (connects to MCP, DB, Redis)
        self.worker = Worker(self.settings)
        await self.worker.initialize()
        logger.info("Worker initialized")

        # Get Redis connection from worker
        self.redis_manager = self.worker.redis_manager
        self.job_queue = self.worker.job_queue

        logger.info("Worker poller initialization complete")

    async def poll_and_process(self) -> None:
        """
        Main polling loop. Continuously checks Redis for jobs and processes them.
        """
        if not self.worker or not self.job_queue:
            raise RuntimeError("Worker not initialized. Call initialize() first.")

        self.running = True
        logger.info("Starting job polling loop...")

        consecutive_empty_polls = 0
        max_consecutive_empty = 10

        while self.running:
            try:
                # Try to acquire a pending job
                job_data = await self.job_queue.acquire_job(self.settings.worker_id)

                if job_data:
                    # Reset empty poll counter
                    consecutive_empty_polls = 0

                    # Process the job
                    await self._process_job(job_data)

                else:
                    # No jobs available
                    consecutive_empty_polls += 1

                    # Exponential backoff for empty polls
                    if consecutive_empty_polls <= max_consecutive_empty:
                        wait_time = min(0.5 * (2 ** (consecutive_empty_polls - 1)), 5)
                    else:
                        wait_time = 5  # Max 5 seconds

                    logger.debug(
                        f"No jobs available (empty polls: {consecutive_empty_polls}), "
                        f"waiting {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)

            except asyncio.CancelledError:
                logger.info("Polling loop cancelled")
                break

            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                logger.exception("Full traceback:")
                # Wait a bit before retrying
                await asyncio.sleep(2)

        logger.info("Polling loop stopped")

    async def _process_job(self, job_data: dict) -> None:
        """
        Process a single job.

        Args:
            job_data: Job data from Redis
        """
        job_id = job_data["conversation_id"]
        query = job_data["query"]
        conv_id = UUID(job_data["conversation_id"])

        logger.info(f"Processing job {job_id} for conversation {conv_id}")
        logger.info(f"Query: {query[:100]}...")

        try:
            # Process query with worker
            # save_user_message=False because API already saved it
            response = await self.worker.process_query_with_context(
                query=query,
                conv_id=conv_id,
                save_user_message=False
            )

            logger.info(f"Job {job_id} processed successfully")
            logger.debug(f"Response: {response[:200]}...")

            # Update job status to Ready with result
            await self.job_queue.complete_job(job_id, response)
            logger.info(f"Job {job_id} marked as Ready in Redis")

        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            logger.exception("Full traceback:")

            # Update job with error status
            error_message = f"Error: {str(e)}"
            await self.job_queue.complete_job(job_id, error_message)
            logger.info(f"Job {job_id} marked as Ready with error message")

    async def shutdown(self) -> None:
        """Stop polling and clean up resources."""
        logger.info("Shutting down worker poller...")

        self.running = False

        if self.worker:
            await self.worker.shutdown()

        logger.info("Worker poller shutdown complete")

    async def run(self) -> None:
        """Run the worker poller (initialize, poll, cleanup)."""
        try:
            await self.initialize()
            await self.poll_and_process()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Fatal error in worker poller: {e}")
            logger.exception("Full traceback:")
        finally:
            await self.shutdown()


async def main():
    """Main entry point for worker polling."""
    settings = Settings()
    poller = WorkerPoller(settings)
    await poller.run()


if __name__ == "__main__":
    asyncio.run(main())
