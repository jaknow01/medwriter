#!/usr/bin/env python3
"""Test script for FastAPI endpoints."""

import asyncio
import httpx
from uuid import uuid4


API_BASE = "http://127.0.0.1:8003/api"


async def test_api():
    """Test all API endpoints."""
    print("=" * 60)
    print("Testing MedWriter API")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Test 1: Health check
        print("\n1. Testing health endpoint...")
        response = await client.get("http://127.0.0.1:8003/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        assert response.status_code == 200

        # Test 2: List conversations (should be empty initially or have previous ones)
        print("\n2. Testing list conversations...")
        response = await client.get(f"{API_BASE}/conversations")
        print(f"   Status: {response.status_code}")
        conversations = response.json()
        print(f"   Found {len(conversations)} conversations")
        assert response.status_code == 200

        # Test 3: Create new conversation
        print("\n3. Testing create conversation...")
        response = await client.post(
            f"{API_BASE}/conversations",
            json={"title": "Test Conversation"}
        )
        print(f"   Status: {response.status_code}")
        new_conv = response.json()
        conv_id = new_conv["conv_id"]
        print(f"   Created conversation: {conv_id}")
        assert response.status_code == 201

        # Test 4: Get conversation details
        print("\n4. Testing get conversation...")
        response = await client.get(f"{API_BASE}/conversations/{conv_id}")
        print(f"   Status: {response.status_code}")
        conv_detail = response.json()
        print(f"   Title: {conv_detail['title']}")
        print(f"   Messages: {len(conv_detail['messages'])}")
        assert response.status_code == 200

        # Test 5: Send message (creates job)
        print("\n5. Testing send message...")
        response = await client.post(
            f"{API_BASE}/conversations/{conv_id}/messages",
            json={"content": "What are the symptoms of COVID-19?"}
        )
        print(f"   Status: {response.status_code}")
        msg_response = response.json()
        job_id = msg_response["job_id"]
        print(f"   Message ID: {msg_response['mess_id']}")
        print(f"   Job ID: {job_id}")
        print(f"   Status: {msg_response['status']}")
        assert response.status_code == 202

        # Test 6: Check job status
        print("\n6. Testing job status...")
        response = await client.get(f"{API_BASE}/jobs/{job_id}/status")
        print(f"   Status: {response.status_code}")
        job_status = response.json()
        print(f"   Job status: {job_status['status']}")
        print(f"   Conversation ID: {job_status['conversation_id']}")
        assert response.status_code == 200

        # Test 7: Get messages for conversation
        print("\n7. Testing get messages...")
        response = await client.get(f"{API_BASE}/conversations/{conv_id}/messages")
        print(f"   Status: {response.status_code}")
        messages = response.json()
        print(f"   Found {len(messages)} messages")
        if messages:
            print(f"   Latest message: {messages[-1]['role']}: {messages[-1]['content'][:50]}...")
        assert response.status_code == 200
        assert len(messages) >= 1  # At least the user message we sent

        # Test 8: Delete conversation
        print("\n8. Testing delete conversation...")
        response = await client.delete(f"{API_BASE}/conversations/{conv_id}")
        print(f"   Status: {response.status_code}")
        assert response.status_code == 204

        # Test 9: Verify conversation deleted
        print("\n9. Verifying conversation deleted...")
        response = await client.get(f"{API_BASE}/conversations/{conv_id}")
        print(f"   Status: {response.status_code}")
        assert response.status_code == 404

    print("\n" + "=" * 60)
    print("✅ All API tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_api())
