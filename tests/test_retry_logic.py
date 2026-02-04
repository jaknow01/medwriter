"""Test retry logic for rate limit errors."""

import asyncio
import httpx
from loguru import logger

API_BASE = "http://localhost:8003/api"


async def test_single_message():
    """Test sending a single message to verify the system works."""
    logger.info("Testing single message...")

    async with httpx.AsyncClient(timeout=180) as client:
        # Create conversation
        response = await client.post(f"{API_BASE}/conversations", json={"title": None})
        response.raise_for_status()
        conv_id = response.json()["conv_id"]
        logger.info(f"Created conversation: {conv_id}")

        # Send message
        response = await client.post(
            f"{API_BASE}/conversations/{conv_id}/messages",
            json={"content": "What are the symptoms of flu?"}
        )
        response.raise_for_status()
        job_id = response.json()["job_id"]
        logger.info(f"Created job: {job_id}")

        # Poll for completion
        max_attempts = 180
        for attempt in range(max_attempts):
            response = await client.get(f"{API_BASE}/jobs/{job_id}/status")
            response.raise_for_status()
            status = response.json()

            if status["status"] == "Ready":
                result = status["result"]
                logger.success(f"Job completed!")
                logger.info(f"Result preview: {result[:200]}...")

                # Check if it's an error message
                if "Przepraszamy" in result or "Wystąpił błąd" in result:
                    logger.warning("Received error message (possibly rate limit)")
                    logger.warning(f"Full message: {result}")
                    return False
                else:
                    logger.success("Received successful response!")
                    return True

            logger.debug(f"Status: {status['status']} (attempt {attempt + 1}/{max_attempts})")
            await asyncio.sleep(1)

        logger.error("Job timed out")
        return False


if __name__ == "__main__":
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    success = asyncio.run(test_single_message())
    exit(0 if success else 1)
