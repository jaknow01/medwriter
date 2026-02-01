"""Tests for MCP client."""

import pytest
from pytest_httpx import HTTPXMock

from src.worker.mcp_client import MCPClient


@pytest.fixture
def mock_server_url():
    """Fixture for mock server URL."""
    return "http://localhost:8000"


@pytest.fixture
def mcp_client(mock_server_url):
    """Fixture for MCP client."""
    return MCPClient(server_url=mock_server_url, timeout=5, max_retries=2)


@pytest.mark.asyncio
async def test_client_initialization(mcp_client, mock_server_url):
    """Test MCP client initialization."""
    assert mcp_client.server_url == mock_server_url
    assert mcp_client.timeout == 5
    assert mcp_client.max_retries == 2
    assert not mcp_client.is_connected()


@pytest.mark.asyncio
async def test_connect_success(mcp_client, httpx_mock: HTTPXMock):
    """Test successful connection to MCP server."""
    # Mock tools endpoint
    httpx_mock.add_response(
        url="http://localhost:8000/tools",
        json={
            "tools": [
                {"name": "web_search", "description": "Search the web"},
                {"name": "medical_knowledge", "description": "Get medical knowledge"},
            ]
        },
    )

    result = await mcp_client.connect()

    assert result is True
    assert mcp_client.is_connected()
    assert len(mcp_client.tools) == 2
    assert "web_search" in mcp_client.tools
    assert "medical_knowledge" in mcp_client.tools


@pytest.mark.asyncio
async def test_connect_failure(mcp_client, httpx_mock: HTTPXMock):
    """Test connection failure."""
    # Mock failed response
    httpx_mock.add_response(
        url="http://localhost:8000/tools",
        status_code=500,
    )

    result = await mcp_client.connect()

    assert result is False
    assert not mcp_client.is_connected()


@pytest.mark.asyncio
async def test_get_tools_not_connected(mcp_client):
    """Test get_tools when not connected."""
    tools = mcp_client.get_tools()
    assert tools == []


@pytest.mark.asyncio
async def test_get_tools_connected(mcp_client, httpx_mock: HTTPXMock):
    """Test get_tools when connected."""
    # Mock connection
    httpx_mock.add_response(
        url="http://localhost:8000/tools",
        json={
            "tools": [
                {"name": "tool1", "description": "First tool"},
                {"name": "tool2", "description": "Second tool"},
            ]
        },
    )

    await mcp_client.connect()
    tools = mcp_client.get_tools()

    assert len(tools) == 2
    assert all(hasattr(t, "metadata") for t in tools)


@pytest.mark.asyncio
async def test_call_tool_success(mcp_client, httpx_mock: HTTPXMock):
    """Test successful tool call."""
    # Mock connection
    httpx_mock.add_response(
        url="http://localhost:8000/tools",
        json={
            "tools": [
                {"name": "test_tool", "description": "Test tool"},
            ]
        },
    )

    await mcp_client.connect()

    # Mock tool call
    httpx_mock.add_response(
        url="http://localhost:8000/tools/test_tool",
        json={"result": "success", "data": "test data"},
    )

    result = mcp_client.call_tool("test_tool", {"param": "value"})

    assert result["result"] == "success"
    assert result["data"] == "test data"


@pytest.mark.asyncio
async def test_call_tool_not_found(mcp_client, httpx_mock: HTTPXMock):
    """Test calling non-existent tool."""
    # Mock connection
    httpx_mock.add_response(
        url="http://localhost:8000/tools",
        json={"tools": []},
    )

    await mcp_client.connect()

    with pytest.raises(ValueError, match="Tool 'nonexistent' not found"):
        mcp_client.call_tool("nonexistent", {})


@pytest.mark.asyncio
async def test_call_tool_http_error(mcp_client, httpx_mock: HTTPXMock):
    """Test tool call with HTTP error."""
    # Mock connection
    httpx_mock.add_response(
        url="http://localhost:8000/tools",
        json={
            "tools": [
                {"name": "test_tool", "description": "Test tool"},
            ]
        },
    )

    await mcp_client.connect()

    # Mock failed tool calls (all retries)
    for _ in range(2):  # max_retries = 2 means 2 attempts total
        httpx_mock.add_response(
            url="http://localhost:8000/tools/test_tool",
            status_code=500,
        )

    with pytest.raises(Exception):
        mcp_client.call_tool("test_tool", {})


@pytest.mark.asyncio
async def test_call_tool_retry(mcp_client, httpx_mock: HTTPXMock):
    """Test tool call retry logic."""
    # Mock connection
    httpx_mock.add_response(
        url="http://localhost:8000/tools",
        json={
            "tools": [
                {"name": "test_tool", "description": "Test tool"},
            ]
        },
    )

    await mcp_client.connect()

    # Mock first call fails, second succeeds
    httpx_mock.add_response(
        url="http://localhost:8000/tools/test_tool",
        status_code=500,
    )
    httpx_mock.add_response(
        url="http://localhost:8000/tools/test_tool",
        json={"result": "success"},
    )

    result = mcp_client.call_tool("test_tool", {})
    assert result["result"] == "success"


@pytest.mark.asyncio
async def test_disconnect(mcp_client, httpx_mock: HTTPXMock):
    """Test disconnecting from server."""
    # Mock connection
    httpx_mock.add_response(
        url="http://localhost:8000/tools",
        json={"tools": []},
    )

    await mcp_client.connect()
    assert mcp_client.is_connected()

    mcp_client.disconnect()
    assert not mcp_client.is_connected()


@pytest.mark.asyncio
async def test_context_manager():
    """Test using client as context manager."""
    # Context manager for MCPClient doesn't auto-connect,
    # it just ensures cleanup on exit
    with MCPClient("http://localhost:8000") as client:
        assert client is not None
        assert not client.is_connected()  # Not connected yet

    # Client should still be disconnected after context
    assert not client.is_connected()
