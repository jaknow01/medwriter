"""
Phase Four: Concurrent load testing.

Tests multiple workers processing multiple conversations simultaneously.
"""

import asyncio
import httpx
from uuid import UUID
from typing import List, Dict
from loguru import logger
import time

API_BASE = "http://localhost:8003/api"
TIMEOUT = 120  # 2 minutes timeout for each request


async def create_conversation() -> Dict:
    """Create a new conversation."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(f"{API_BASE}/conversations", json={"title": None})
        response.raise_for_status()
        return response.json()


async def send_message(conv_id: str, message: str) -> Dict:
    """Send a message and return job info."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            f"{API_BASE}/conversations/{conv_id}/messages",
            json={"content": message}
        )
        response.raise_for_status()
        return response.json()


async def poll_job_status(job_id: str, max_attempts: int = 120) -> Dict:
    """Poll job status until complete."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for attempt in range(max_attempts):
            response = await client.get(f"{API_BASE}/jobs/{job_id}/status")
            response.raise_for_status()
            status_data = response.json()

            if status_data["status"] == "Ready":
                return status_data

            await asyncio.sleep(1)

    raise TimeoutError(f"Job {job_id} did not complete in time")


async def get_conversation(conv_id: str) -> Dict:
    """Get conversation with messages."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(f"{API_BASE}/conversations/{conv_id}")
        response.raise_for_status()
        return response.json()


async def process_conversation(conv_num: int, messages: List[str]) -> Dict:
    """
    Process a full conversation with multiple messages.

    Args:
        conv_num: Conversation number for logging
        messages: List of messages to send

    Returns:
        Dict with results
    """
    start_time = time.time()
    logger.info(f"[Conv {conv_num}] Starting conversation")

    try:
        # Create conversation
        conversation = await create_conversation()
        conv_id = conversation["conv_id"]
        logger.info(f"[Conv {conv_num}] Created conversation {conv_id}")

        results = []

        # Send messages sequentially in this conversation
        for msg_num, message in enumerate(messages, 1):
            msg_start = time.time()
            logger.info(f"[Conv {conv_num}] Sending message {msg_num}: {message[:50]}...")

            # Send message
            response = await send_message(conv_id, message)
            job_id = response["job_id"]

            # Poll for completion
            logger.info(f"[Conv {conv_num}] Polling job {job_id}")
            status = await poll_job_status(job_id)

            msg_duration = time.time() - msg_start
            logger.info(f"[Conv {conv_num}] Message {msg_num} completed in {msg_duration:.2f}s")

            results.append({
                "message_num": msg_num,
                "message": message,
                "duration": msg_duration,
                "result_length": len(status["result"])
            })

        # Get final conversation state
        final_conv = await get_conversation(conv_id)
        total_messages = len(final_conv["messages"])

        total_duration = time.time() - start_time
        logger.success(f"[Conv {conv_num}] Completed in {total_duration:.2f}s with {total_messages} messages")

        return {
            "conversation_num": conv_num,
            "conv_id": conv_id,
            "total_duration": total_duration,
            "message_count": total_messages,
            "messages": results,
            "success": True
        }

    except Exception as e:
        total_duration = time.time() - start_time
        logger.error(f"[Conv {conv_num}] Failed after {total_duration:.2f}s: {e}")
        return {
            "conversation_num": conv_num,
            "total_duration": total_duration,
            "success": False,
            "error": str(e)
        }


async def run_concurrent_load_test():
    """
    Run concurrent load test with multiple conversations.

    Test scenarios:
    1. 2 conversations with 2 messages each (simultaneous)
    2. 3 conversations with 1 message each (simultaneous)
    3. 4 conversations with 1 message each (stress test)
    """
    logger.info("=" * 80)
    logger.info("PHASE FOUR: CONCURRENT LOAD TEST")
    logger.info("=" * 80)

    # Test data
    test_conversations = [
        {
            "name": "COVID Symptoms",
            "messages": [
                "What are the main symptoms of COVID-19?",
                "How long do COVID symptoms typically last?"
            ]
        },
        {
            "name": "Diabetes Management",
            "messages": [
                "What are the best practices for managing type 2 diabetes?",
                "What foods should diabetics avoid?"
            ]
        },
        {
            "name": "Heart Health",
            "messages": [
                "What are the early signs of heart disease?"
            ]
        },
        {
            "name": "Mental Health",
            "messages": [
                "What are effective treatments for anxiety?"
            ]
        },
    ]

    # Scenario 1: 2 conversations with multiple messages
    logger.info("\n" + "=" * 80)
    logger.info("SCENARIO 1: 2 Conversations × 2 Messages Each (Parallel)")
    logger.info("=" * 80)

    start_time = time.time()
    tasks = [
        process_conversation(i + 1, conv["messages"])
        for i, conv in enumerate(test_conversations[:2])
    ]
    results_1 = await asyncio.gather(*tasks)
    duration_1 = time.time() - start_time

    logger.info(f"\nScenario 1 completed in {duration_1:.2f}s")
    logger.info(f"Successful: {sum(1 for r in results_1 if r['success'])}/{len(results_1)}")

    # Scenario 2: 3 conversations with 1 message each
    logger.info("\n" + "=" * 80)
    logger.info("SCENARIO 2: 3 Conversations × 1 Message Each (Parallel)")
    logger.info("=" * 80)

    start_time = time.time()
    tasks = [
        process_conversation(i + 3, [conv["messages"][0]])
        for i, conv in enumerate(test_conversations[:3])
    ]
    results_2 = await asyncio.gather(*tasks)
    duration_2 = time.time() - start_time

    logger.info(f"\nScenario 2 completed in {duration_2:.2f}s")
    logger.info(f"Successful: {sum(1 for r in results_2 if r['success'])}/{len(results_2)}")

    # Scenario 3: 4 conversations simultaneously (stress test)
    logger.info("\n" + "=" * 80)
    logger.info("SCENARIO 3: 4 Conversations × 1 Message Each (Stress Test)")
    logger.info("=" * 80)

    start_time = time.time()
    tasks = [
        process_conversation(i + 6, [conv["messages"][0]])
        for i, conv in enumerate(test_conversations)
    ]
    results_3 = await asyncio.gather(*tasks)
    duration_3 = time.time() - start_time

    logger.info(f"\nScenario 3 completed in {duration_3:.2f}s")
    logger.info(f"Successful: {sum(1 for r in results_3 if r['success'])}/{len(results_3)}")

    # Summary
    all_results = results_1 + results_2 + results_3
    successful = sum(1 for r in all_results if r["success"])
    total = len(all_results)

    logger.info("\n" + "=" * 80)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total conversations: {total}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {total - successful}")
    logger.info(f"Success rate: {successful/total*100:.1f}%")
    logger.info(f"Total time: {duration_1 + duration_2 + duration_3:.2f}s")

    if successful == total:
        logger.success("\n✓ ALL TESTS PASSED!")
        logger.success("Phase Four: Multiple workers handling concurrent conversations successfully!")
    else:
        logger.error(f"\n✗ {total - successful} TESTS FAILED")
        for result in all_results:
            if not result["success"]:
                logger.error(f"  - Conversation {result['conversation_num']}: {result.get('error', 'Unknown error')}")

    return successful == total


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Run test
    success = asyncio.run(run_concurrent_load_test())
    exit(0 if success else 1)
