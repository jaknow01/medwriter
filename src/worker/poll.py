"""Worker polling loop for processing jobs from Redis queue."""

import asyncio
from uuid import UUID
from loguru import logger

from src.config.settings import Settings
from src.worker.worker import Worker
from src.redis import RedisManager, JobQueue


class WorkerPoller:
    """Worker that continuously polls Redis for jobs and processes them."""

    def __init__(self, settings: Settings, worker_id: str | None = None):
        """
        Initialize worker poller.

        Args:
            settings: Application settings
            worker_id: Optional custom worker ID (overrides settings.worker_id)
        """
        # Create a copy of settings to avoid modifying shared instance
        from copy import copy
        self.settings = copy(settings)

        if worker_id:
            # Override worker_id in this worker's settings copy
            self.settings.worker_id = worker_id

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

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """
        Check if error is a rate limit error.

        Args:
            error: Exception to check

        Returns:
            True if rate limit error, False otherwise
        """
        error_str = str(error).lower()
        return (
            "429" in error_str
            or "rate limit" in error_str
            or "rate_limit_exceeded" in error_str
            or "quota" in error_str
        )

    async def _process_with_retry(
        self, query: str, conv_id: UUID, max_retries: int = 3
    ) -> str:
        """
        Process query with exponential backoff retry logic.

        Handles only LLM API calls — PDF indexing must be done before
        calling this method.

        Args:
            query: User query
            conv_id: Conversation UUID
            max_retries: Maximum number of retry attempts

        Returns:
            Response or error message

        Raises:
            Exception: If all retries fail
        """
        base_delay = 10  # Start with 10 seconds

        for attempt in range(max_retries):
            try:
                response = await self.worker.process_query_with_context(
                    query=query,
                    conv_id=conv_id,
                    save_user_message=False,
                )
                return response

            except Exception as e:
                is_rate_limit = self._is_rate_limit_error(e)

                if is_rate_limit and attempt < max_retries - 1:
                    # Exponential backoff: 10s, 20s, 40s
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Rate limit hit (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    continue

                # Not a rate limit error or final attempt - raise
                raise

    async def _process_job(self, job_data: dict) -> None:
        """
        Process a single job with retry logic for rate limits.

        Args:
            job_data: Job data from Redis
        """
        job_id = job_data["conversation_id"]
        query = job_data["query"]
        conv_id = UUID(job_data["conversation_id"])
        pdf_chunks = job_data.get("pdf_chunks")

        logger.info(f"Processing job {job_id} for conversation {conv_id}")
        logger.info(f"Query: {query[:100]}...")

        try:
            # Index PDF chunks before LLM processing (one-time, not retried)
            if pdf_chunks:
                logger.info(f"Indexing {len(pdf_chunks)} PDF chunks for conv {conv_id}")
                self.worker.index_pdf_chunks(conv_id, pdf_chunks)

            # Process query with retry logic (only LLM calls are retried)
            response = await self._process_with_retry(
                query=query,
                conv_id=conv_id,
                max_retries=3,
            )

            logger.info(f"Job {job_id} processed successfully")
            logger.debug(f"Response: {response[:200]}...")

            # Update job status to Ready with result
            await self.job_queue.complete_job(job_id, response)
            logger.info(f"Job {job_id} marked as Ready in Redis")

        except Exception as e:
            logger.error(f"Error processing job {job_id} after retries: {e}")
            logger.exception("Full traceback:")

            # Check if it's a rate limit error for user-friendly message
            if self._is_rate_limit_error(e):
                error_message = (
                    "Przepraszamy, obecnie doświadczamy dużego obciążenia. "
                    "Prosimy spróbować ponownie za kilka minut. "
                    "Jeśli problem będzie się powtarzał, skontaktuj się z administratorem."
                )
                logger.warning(f"Rate limit error for job {job_id}, returning Polish message")
            else:
                error_message = (
                    "Wystąpił błąd podczas przetwarzania zapytania. "
                    "Prosimy spróbować ponownie lub skontaktować się z administratorem."
                )

            # Update job with error status
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
    """Main entry point for worker polling with multiple concurrent workers."""
    import os

    settings = Settings()

    # Get number of workers from environment (default 3, max 6)
    num_workers = int(os.getenv("NUM_WORKERS", "3"))
    num_workers = min(max(num_workers, 1), 6)  # Clamp between 1 and 6

    logger.info(f"Starting {num_workers} concurrent async workers")

    # Create multiple worker pollers with unique IDs
    pollers = [
        WorkerPoller(settings, worker_id=f"worker-{i+1}")
        for i in range(num_workers)
    ]

    # Run all workers concurrently
    try:
        await asyncio.gather(*[poller.run() for poller in pollers])
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down all workers")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        logger.exception("Full traceback:")


if __name__ == "__main__":
    asyncio.run(main())
