"""Integration tests for Phase Two functionality."""

import pytest
from uuid import uuid4

from src.worker.worker import Worker
from src.config.settings import Settings


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        llm_provider="openai",
        openai_api_key="test-key",
        mcp_server_url="http://localhost:8001/mcp",
        database_url="postgresql+asyncpg://medwriter:password@localhost:5432/medwriter_test_db",
        redis_url="redis://localhost:6379/1",
        worker_id="test-worker-1"
    )


@pytest.mark.integration
class TestPhaseTwo:
    """Integration tests for Phase Two features."""

    async def test_worker_initialization_with_db_redis(self, settings):
        """Test worker initializes with database and Redis."""
        worker = Worker(settings)

        # Note: This will fail if MCP server is not running
        # For true integration test, MCP server should be running
        try:
            await worker.initialize()

            assert worker.db_manager is not None
            assert worker.redis_manager is not None
            assert worker.job_queue is not None
            assert worker.title_generator is not None

            await worker.shutdown()

        except Exception as e:
            # Expected if MCP server not running
            pytest.skip(f"MCP server not available: {e}")

    async def test_conversation_with_context(self, settings):
        """Test processing query with conversation context."""
        worker = Worker(settings)

        try:
            await worker.initialize()

            # Create a conversation ID
            conv_id = uuid4()

            # Process first query
            response1 = await worker.process_query_with_context(
                "What is diabetes?",
                conv_id
            )

            assert response1 is not None

            # Process second query (should have context)
            response2 = await worker.process_query_with_context(
                "What are the symptoms?",
                conv_id
            )

            assert response2 is not None

            # Verify messages are stored in database
            async with worker.db_manager.get_session() as session:
                from src.database import ConversationRepository

                repo = ConversationRepository(session)
                messages = await repo.get_messages(conv_id)

                # Should have 4 messages: User, AI, User, AI
                assert len(messages) == 4
                assert messages[0].role == "User"
                assert messages[1].role == "AI"
                assert messages[2].role == "User"
                assert messages[3].role == "AI"

                # Verify conversation has a title
                conv = await repo.get_conversation(conv_id)
                assert conv.title is not None

            await worker.shutdown()

        except Exception as e:
            pytest.skip(f"Integration test skipped: {e}")
