"""Tests for database operations."""

import pytest
from uuid import uuid4

from src.database import DatabaseManager, ConversationRepository, Conversation, Message


@pytest.fixture
async def db_manager():
    """Create database manager for testing."""
    # Use in-memory SQLite for testing (requires sqlite+aiosqlite)
    # For now, we'll use a test PostgreSQL database
    db_url = "postgresql+asyncpg://medwriter:password@localhost:5432/medwriter_test_db"
    manager = DatabaseManager(db_url)
    await manager.initialize_db()
    yield manager
    await manager.close()


@pytest.fixture
async def db_session(db_manager):
    """Create database session for testing."""
    async with db_manager.get_session() as session:
        yield session


class TestDatabaseConnection:
    """Test database connection and initialization."""

    async def test_database_initialization(self, db_manager):
        """Test database initializes successfully."""
        assert db_manager.engine is not None
        assert db_manager.async_session_factory is not None

    async def test_get_session(self, db_manager):
        """Test getting database session."""
        async with db_manager.get_session() as session:
            assert session is not None


class TestConversationRepository:
    """Test conversation repository operations."""

    async def test_create_conversation(self, db_session):
        """Test creating a new conversation."""
        repo = ConversationRepository(db_session)
        conv = await repo.create_conversation(title="Test Conversation")

        assert conv is not None
        assert conv.conv_id is not None
        assert conv.title == "Test Conversation"

    async def test_create_conversation_without_title(self, db_session):
        """Test creating conversation without title."""
        repo = ConversationRepository(db_session)
        conv = await repo.create_conversation()

        assert conv is not None
        assert conv.conv_id is not None
        assert conv.title is None

    async def test_create_conversation_with_specific_id(self, db_session):
        """Test creating conversation with specific ID."""
        repo = ConversationRepository(db_session)
        specific_id = uuid4()
        conv = await repo.create_conversation(conv_id=specific_id)

        assert conv is not None
        assert conv.conv_id == specific_id
        assert conv.title is None

    async def test_get_conversation(self, db_session):
        """Test retrieving conversation by ID."""
        repo = ConversationRepository(db_session)

        # Create conversation
        conv = await repo.create_conversation(title="Test")

        # Retrieve it
        retrieved = await repo.get_conversation(conv.conv_id)

        assert retrieved is not None
        assert retrieved.conv_id == conv.conv_id
        assert retrieved.title == "Test"

    async def test_get_nonexistent_conversation(self, db_session):
        """Test retrieving non-existent conversation."""
        repo = ConversationRepository(db_session)
        fake_id = uuid4()

        result = await repo.get_conversation(fake_id)

        assert result is None

    async def test_update_title(self, db_session):
        """Test updating conversation title."""
        repo = ConversationRepository(db_session)

        # Create conversation without title
        conv = await repo.create_conversation()

        # Update title
        new_title = "Updated Title"
        await repo.update_title(conv.conv_id, new_title)

        # Retrieve and verify
        updated = await repo.get_conversation(conv.conv_id)
        assert updated.title == new_title

    async def test_add_message(self, db_session):
        """Test adding message to conversation."""
        repo = ConversationRepository(db_session)

        # Create conversation
        conv = await repo.create_conversation()

        # Add message
        msg = await repo.add_message(
            conv.conv_id, role="User", content="Test message"
        )

        assert msg is not None
        assert msg.mess_id is not None
        assert msg.conv_id == conv.conv_id
        assert msg.role == "User"
        assert msg.content == "Test message"

    async def test_get_messages(self, db_session):
        """Test retrieving messages for conversation."""
        repo = ConversationRepository(db_session)

        # Create conversation
        conv = await repo.create_conversation()

        # Add multiple messages
        await repo.add_message(conv.conv_id, role="User", content="Message 1")
        await repo.add_message(conv.conv_id, role="AI", content="Response 1")
        await repo.add_message(conv.conv_id, role="User", content="Message 2")

        # Retrieve messages
        messages = await repo.get_messages(conv.conv_id)

        assert len(messages) == 3
        assert messages[0].content == "Message 1"
        assert messages[1].content == "Response 1"
        assert messages[2].content == "Message 2"

    async def test_get_messages_empty_conversation(self, db_session):
        """Test retrieving messages from conversation with no messages."""
        repo = ConversationRepository(db_session)

        # Create conversation
        conv = await repo.create_conversation()

        # Get messages
        messages = await repo.get_messages(conv.conv_id)

        assert len(messages) == 0

    async def test_messages_ordered_by_timestamp(self, db_session):
        """Test messages are returned in timestamp order."""
        repo = ConversationRepository(db_session)

        # Create conversation
        conv = await repo.create_conversation()

        # Add messages
        msg1 = await repo.add_message(conv.conv_id, role="User", content="First")
        msg2 = await repo.add_message(conv.conv_id, role="AI", content="Second")
        msg3 = await repo.add_message(conv.conv_id, role="User", content="Third")

        # Retrieve messages
        messages = await repo.get_messages(conv.conv_id)

        # Verify order
        assert messages[0].mess_id == msg1.mess_id
        assert messages[1].mess_id == msg2.mess_id
        assert messages[2].mess_id == msg3.mess_id
