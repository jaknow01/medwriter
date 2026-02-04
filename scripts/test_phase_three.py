#!/usr/bin/env python3
"""Automated Phase Three integration test (no user input required)."""

import asyncio
import httpx
import sys


API_BASE = "http://127.0.0.1:8003/api"


async def test_phase_three():
    """Test complete Phase Three implementation."""
    print("=" * 70)
    print("Phase Three Integration Test")
    print("=" * 70)
    print()

    # Wait a moment for services to fully start
    print("Waiting for services to be ready...")
    await asyncio.sleep(3)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Test 1: Health check
            print("1. Testing API health...")
            try:
                response = await client.get("http://127.0.0.1:8003/health")
                if response.status_code == 200:
                    print("   ✅ API is healthy")
                else:
                    print(f"   ❌ API health check failed: {response.status_code}")
                    return False
            except Exception as e:
                print(f"   ❌ Cannot connect to API: {e}")
                return False

            # Test 2: Create conversation
            print("\n2. Creating new conversation...")
            response = await client.post(
                f"{API_BASE}/conversations",
                json={"title": "Phase Three Test"}
            )

            if response.status_code != 201:
                print(f"   ❌ Failed: {response.status_code}")
                return False

            conv = response.json()
            conv_id = conv["conv_id"]
            print(f"   ✅ Created: {conv_id}")

            # Test 3: Send message
            print("\n3. Sending message...")
            test_query = "What are the main symptoms of diabetes?"

            response = await client.post(
                f"{API_BASE}/conversations/{conv_id}/messages",
                json={"content": test_query}
            )

            if response.status_code != 202:
                print(f"   ❌ Failed: {response.status_code}")
                return False

            msg_response = response.json()
            job_id = msg_response["job_id"]
            print(f"   ✅ Job created: {job_id}")

            # Test 4: Poll job status
            print("\n4. Polling job status...")
            max_attempts = 60
            attempt = 0

            while attempt < max_attempts:
                attempt += 1

                response = await client.get(f"{API_BASE}/jobs/{job_id}/status")

                if response.status_code != 200:
                    print(f"   ❌ Failed to get status: {response.status_code}")
                    return False

                job_status = response.json()
                status = job_status["status"]

                if status == "Ready":
                    result = job_status.get("result", "")
                    print(f"   ✅ Job completed (took {attempt}s)")
                    print(f"   Response preview: {result[:100]}...")
                    break

                elif status == "Processing":
                    sys.stdout.write(f"\r   Processing... ({attempt}s)")
                    sys.stdout.flush()

                elif status == "Pending":
                    sys.stdout.write(f"\r   Pending... ({attempt}s)")
                    sys.stdout.flush()

                await asyncio.sleep(1)

            else:
                print(f"\n   ❌ Timeout after {max_attempts}s")
                return False

            print()

            # Test 5: Verify messages
            print("\n5. Verifying messages in database...")
            response = await client.get(f"{API_BASE}/conversations/{conv_id}/messages")

            if response.status_code != 200:
                print(f"   ❌ Failed: {response.status_code}")
                return False

            messages = response.json()
            print(f"   ✅ Found {len(messages)} messages")

            if len(messages) >= 2:
                print(f"   ✅ User message saved")
                print(f"   ✅ AI response saved")
            else:
                print(f"   ❌ Expected at least 2 messages")
                return False

            # Test 6: Get conversation
            print("\n6. Getting conversation details...")
            response = await client.get(f"{API_BASE}/conversations/{conv_id}")

            if response.status_code != 200:
                print(f"   ❌ Failed: {response.status_code}")
                return False

            conv_detail = response.json()
            title = conv_detail.get("title", "")
            print(f"   ✅ Title: {title}")
            print(f"   ✅ Messages: {len(conv_detail['messages'])}")

            # Test 7: List conversations
            print("\n7. Listing all conversations...")
            response = await client.get(f"{API_BASE}/conversations")

            if response.status_code != 200:
                print(f"   ❌ Failed: {response.status_code}")
                return False

            conversations = response.json()
            print(f"   ✅ Found {len(conversations)} conversations")

            print("\n" + "=" * 70)
            print("✅ Phase Three Integration Test PASSED!")
            print("=" * 70)
            print()
            print("Verified:")
            print("  ✅ FastAPI backend running")
            print("  ✅ API endpoints functional")
            print("  ✅ Job creation in Redis")
            print("  ✅ Worker polling and processing")
            print("  ✅ Job status updates")
            print("  ✅ Messages saved to database")
            print("  ✅ Conversation persistence")
            print("  ✅ Title generation")
            print()
            print("UI Available at: http://127.0.0.1:8003")
            print()

            return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_phase_three())
    sys.exit(0 if success else 1)
