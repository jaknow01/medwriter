"""Tests for worker module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.worker.worker import Worker
from src.config.settings import Settings
from src.config.json_config import AppConfig, AgentConfig


@pytest.fixture
def mock_settings():
    """Fixture for mock settings."""
    settings = Settings(
        openai_api_key="test-openai-key",
        anthropic_api_key="test-anthropic-key",
        mcp_server_url="http://localhost:8000",
    )
    return settings


@pytest.fixture
def mock_config():
    """Fixture for mock app config."""
    return AppConfig(
        agent=AgentConfig(
            llm_provider="openai",
            model_name="gpt-3.5-turbo",
        ),
    )


@pytest.fixture
def worker(mock_settings, mock_config):
    """Fixture for worker instance."""
    return Worker(mock_settings, mock_config)


def test_worker_initialization(worker, mock_settings):
    """Test worker initialization."""
    assert worker.settings == mock_settings
    assert worker.mcp_client is None
    assert worker.agent is None
    assert not worker.is_initialized()


@pytest.mark.asyncio
async def test_worker_initialize_success(worker):
    """Test successful worker initialization."""
    with patch("src.worker.worker.MCPClient") as mock_mcp_class, \
         patch("src.worker.worker.MedicalArticleAgent") as mock_agent_class:

        # Mock MCP client
        mock_mcp = Mock()
        mock_mcp.connect = AsyncMock(return_value=True)
        mock_mcp.get_tools = Mock(return_value=[])
        mock_mcp_class.return_value = mock_mcp

        # Mock agent
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        await worker.initialize()

        assert worker.is_initialized()
        assert worker.mcp_client is not None
        assert worker.agent is not None


@pytest.mark.asyncio
async def test_worker_initialize_mcp_connection_failure(worker):
    """Test worker initialization when MCP connection fails."""
    with patch("src.worker.worker.MCPClient") as mock_mcp_class:

        # Mock MCP client that fails to connect
        mock_mcp = Mock()
        mock_mcp.connect = AsyncMock(return_value=False)
        mock_mcp_class.return_value = mock_mcp

        with pytest.raises(RuntimeError, match="Failed to connect to MCP server"):
            await worker.initialize()

        assert not worker.is_initialized()


@pytest.mark.asyncio
async def test_worker_process_query_not_initialized(worker):
    """Test processing query when worker not initialized."""
    with pytest.raises(RuntimeError, match="Worker not initialized"):
        worker.process_query("test query")


@pytest.mark.asyncio
async def test_worker_process_query_success(worker):
    """Test successful query processing."""
    # Initialize worker with mocks
    with patch("src.worker.worker.MCPClient") as mock_mcp_class, \
         patch("src.worker.worker.MedicalArticleAgent") as mock_agent_class:

        mock_mcp = Mock()
        mock_mcp.connect = AsyncMock(return_value=True)
        mock_mcp.get_tools = Mock(return_value=[])
        mock_mcp_class.return_value = mock_mcp

        mock_agent = Mock()
        mock_agent.chat = Mock(return_value="Agent response")
        mock_agent_class.return_value = mock_agent

        await worker.initialize()

        response = worker.process_query("test query")

        assert response == "Agent response"
        mock_agent.chat.assert_called_once_with("test query")


@pytest.mark.asyncio
async def test_worker_stream_query_not_initialized(worker):
    """Test streaming query when worker not initialized."""
    with pytest.raises(RuntimeError, match="Worker not initialized"):
        list(worker.stream_query("test query"))


@pytest.mark.asyncio
async def test_worker_stream_query_success(worker):
    """Test successful streaming query."""
    with patch("src.worker.worker.MCPClient") as mock_mcp_class, \
         patch("src.worker.worker.MedicalArticleAgent") as mock_agent_class:

        mock_mcp = Mock()
        mock_mcp.connect = AsyncMock(return_value=True)
        mock_mcp.get_tools = Mock(return_value=[])
        mock_mcp_class.return_value = mock_mcp

        mock_agent = Mock()
        mock_agent.stream_chat = Mock(return_value=iter(["chunk1", "chunk2", "chunk3"]))
        mock_agent_class.return_value = mock_agent

        await worker.initialize()

        chunks = list(worker.stream_query("test query"))

        assert chunks == ["chunk1", "chunk2", "chunk3"]


@pytest.mark.asyncio
async def test_worker_reset_conversation(worker):
    """Test resetting conversation."""
    with patch("src.worker.worker.MCPClient") as mock_mcp_class, \
         patch("src.worker.worker.MedicalArticleAgent") as mock_agent_class:

        mock_mcp = Mock()
        mock_mcp.connect = AsyncMock(return_value=True)
        mock_mcp.get_tools = Mock(return_value=[])
        mock_mcp_class.return_value = mock_mcp

        mock_agent = Mock()
        mock_agent.reset_chat_history = Mock()
        mock_agent_class.return_value = mock_agent

        await worker.initialize()
        worker.reset_conversation()

        mock_agent.reset_chat_history.assert_called_once()


@pytest.mark.asyncio
async def test_worker_switch_llm_provider(worker):
    """Test switching LLM provider."""
    with patch("src.worker.worker.MCPClient") as mock_mcp_class, \
         patch("src.worker.worker.MedicalArticleAgent") as mock_agent_class:

        mock_mcp = Mock()
        mock_mcp.connect = AsyncMock(return_value=True)
        mock_mcp.get_tools = Mock(return_value=[])
        mock_mcp_class.return_value = mock_mcp

        mock_agent = Mock()
        mock_agent.switch_llm = Mock()
        mock_agent_class.return_value = mock_agent

        await worker.initialize()
        await worker.switch_llm_provider("anthropic", "claude-3-opus-20240229")

        assert worker.config.agent.llm_provider == "anthropic"
        assert worker.config.agent.model_name == "claude-3-opus-20240229"
        mock_agent.switch_llm.assert_called_once()


@pytest.mark.asyncio
async def test_worker_switch_llm_not_initialized(worker):
    """Test switching LLM when worker not initialized."""
    with pytest.raises(RuntimeError, match="Worker not initialized"):
        await worker.switch_llm_provider("anthropic")


@pytest.mark.asyncio
async def test_worker_shutdown(worker):
    """Test worker shutdown."""
    with patch("src.worker.worker.MCPClient") as mock_mcp_class, \
         patch("src.worker.worker.MedicalArticleAgent") as mock_agent_class:

        mock_mcp = Mock()
        mock_mcp.connect = AsyncMock(return_value=True)
        mock_mcp.get_tools = Mock(return_value=[])
        mock_mcp.disconnect = Mock()
        mock_mcp_class.return_value = mock_mcp

        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        await worker.initialize()
        assert worker.is_initialized()

        await worker.shutdown()

        assert not worker.is_initialized()
        assert worker.mcp_client is None
        assert worker.agent is None
        mock_mcp.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_worker_context_manager():
    """Test worker as async context manager."""
    mock_settings = Settings(
        openai_api_key="test-key",
        mcp_server_url="http://localhost:8000",
    )
    mock_config = AppConfig()

    with patch("src.worker.worker.MCPClient") as mock_mcp_class, \
         patch("src.worker.worker.MedicalArticleAgent") as mock_agent_class:

        mock_mcp = Mock()
        mock_mcp.connect = AsyncMock(return_value=True)
        mock_mcp.get_tools = Mock(return_value=[])
        mock_mcp.disconnect = Mock()
        mock_mcp_class.return_value = mock_mcp

        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        async with Worker(mock_settings, mock_config) as worker:
            assert worker.is_initialized()

        # Should be shut down after context
        assert not worker.is_initialized()
