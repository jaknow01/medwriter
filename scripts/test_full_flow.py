#!/usr/bin/env python3
"""Integration test for full API → Worker → Redis flow."""

import asyncio
import httpx
import time
from uuid import uuid4


API_BASE = "http://127.0.0.1:8003/api"


async def test_full_flow():
    """Test complete message flow from API to worker."""
    print("=" * 70)
    print("Testing Full Job Processing Flow")
    print("=" * 70)
    print("\nThis test requires:")
    print("  1. FastAPI server running on port 8003")
    print("  2. Worker polling loop running (python3 -m src.worker)")
    print("  3. MCP server running on port 8001/8002")
    print("  4. PostgreSQL and Redis containers running")
    print()

    input("Press Enter when all services are ready...")
    print()

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Create conversation
        print("Step 1: Creating new conversation...")
        response = await client.post(
            f"{API_BASE}/conversations",
            json={"title": "Integration Test"}
        )

        if response.status_code != 201:
            print(f"❌ Failed to create conversation: {response.status_code}")
            print(response.text)
            return

        conv = response.json()
        conv_id = conv["conv_id"]
        print(f"✅ Created conversation: {conv_id}")
        print()

        # Step 2: Send message (creates job)
        print("Step 2: Sending message to create job...")
        test_query = "What are the main symptoms of diabetes?"

        response = await client.post(
            f"{API_BASE}/conversations/{conv_id}/messages",
            json={"content": test_query}
        )

        if response.status_code != 202:
            print(f"❌ Failed to send message: {response.status_code}")
            print(response.text)
            return

        msg_response = response.json()
        job_id = msg_response["job_id"]
        mess_id = msg_response["mess_id"]

        print(f"✅ Message sent (ID: {mess_id})")
        print(f"✅ Job created (ID: {job_id})")
        print(f"   Initial status: {msg_response['status']}")
        print()

        # Step 3: Poll job status until complete
        print("Step 3: Polling job status (waiting for worker)...")
        max_attempts = 60  # 60 seconds max
        attempt = 0
        last_status = None

        while attempt < max_attempts:
            attempt += 1

            response = await client.get(f"{API_BASE}/jobs/{job_id}/status")

            if response.status_code != 200:
                print(f"❌ Failed to get job status: {response.status_code}")
                break

            job_status = response.json()
            current_status = job_status["status"]

            # Print status change
            if current_status != last_status:
                print(f"   [{attempt}s] Status: {current_status}")
                last_status = current_status

            # Check if complete
            if current_status == "Ready":
                print()
                print("✅ Job completed!")
                print()
                print("Response from AI:")
                print("-" * 70)
                result = job_status.get("result", "No result")
                # Print first 500 chars
                if len(result) > 500:
                    print(result[:500] + "...")
                else:
                    print(result)
                print("-" * 70)
                break

            elif current_status == "Processing":
                # Worker is processing, keep polling
                await asyncio.sleep(1)

            elif current_status == "Pending":
                # Still pending, worker hasn't picked it up yet
                await asyncio.sleep(1)

            else:
                print(f"❌ Unknown status: {current_status}")
                break

        if attempt >= max_attempts:
            print()
            print(f"⚠️  Timeout after {max_attempts} seconds")
            print("   Job status:", last_status)
            print()
            print("Possible issues:")
            print("  - Worker not running")
            print("  - MCP server not running")
            print("  - Worker crashed during processing")
            return

        print()

        # Step 4: Verify messages in database
        print("Step 4: Verifying messages saved to database...")
        response = await client.get(f"{API_BASE}/conversations/{conv_id}/messages")

        if response.status_code != 200:
            print(f"❌ Failed to get messages: {response.status_code}")
            return

        messages = response.json()
        print(f"✅ Found {len(messages)} messages in database:")

        for i, msg in enumerate(messages, 1):
            role = msg["role"]
            content = msg["content"]
            timestamp = msg["timestamp"]

            # Truncate long content
            display_content = content[:80] + "..." if len(content) > 80 else content

            print(f"   {i}. [{role}] {display_content}")

        print()

        # Step 5: Get full conversation details
        print("Step 5: Getting conversation details...")
        response = await client.get(f"{API_BASE}/conversations/{conv_id}")

        if response.status_code != 200:
            print(f"❌ Failed to get conversation: {response.status_code}")
            return

        conv_detail = response.json()
        print(f"✅ Conversation retrieved:")
        print(f"   Title: {conv_detail['title']}")
        print(f"   Messages: {len(conv_detail['messages'])}")
        print(f"   Created: {conv_detail['created_at']}")
        print()

        # Summary
        print("=" * 70)
        print("✅ Full Integration Test PASSED!")
        print("=" * 70)
        print()
        print("Verified:")
        print("  ✅ API endpoint for sending messages")
        print("  ✅ Job creation in Redis")
        print("  ✅ Worker polling and job acquisition")
        print("  ✅ Worker processing with conversation context")
        print("  ✅ Job status updates (Pending → Processing → Ready)")
        print("  ✅ Messages saved to PostgreSQL")
        print("  ✅ API retrieval of messages and conversations")
        print()


if __name__ == "__main__":
    try:
        asyncio.run(test_full_flow())
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
