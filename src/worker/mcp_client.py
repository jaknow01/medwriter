"""MCP Client for connecting to MCP server via HTTP."""

from typing import Any
from loguru import logger
from llama_index.core.tools import FunctionTool
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


class MCPClient:
    """MCP client using FastMCP with HTTP transport."""

    def __init__(self, server_url: str, timeout: int = 30):
        """
        Initialize MCP client.

        Args:
            server_url: URL of the MCP server
            timeout: Request timeout in seconds
        """
        self.server_url = server_url
        self.timeout = timeout
        self.client: Client | None = None
        self.tools: dict[str, Any] = {}
        self._connected = False

        logger.info(f"Initialized MCP client for {self.server_url}")

    async def connect(self) -> bool:
        """
        Connect to MCP server and discover available tools.

        Returns:
            True if connection successful, False otherwise
        """
        logger.info(f"Connecting to MCP server at {self.server_url}")

        try:
            # Create HTTP transport
            transport = StreamableHttpTransport(
                url=self.server_url,
                headers={
                    "Content-Type": "application/json",
                }
            )

            # Create FastMCP client with HTTP transport
            self.client = Client(transport)

            # Enter the async context manager
            await self.client.__aenter__()

            logger.info("Successfully connected to MCP server")

            # Discover tools
            await self._discover_tools()
            self._connected = True
            logger.info(f"Discovered {len(self.tools)} tools")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self._connected = False
            if self.client:
                try:
                    await self.client.__aexit__(None, None, None)
                except:
                    pass
                self.client = None
            return False

    async def _discover_tools(self) -> None:
        """Discover available tools from the MCP server."""
        logger.debug("Discovering tools from MCP server")

        try:
            if not self.client:
                raise RuntimeError("Client not initialized")

            # List tools using MCP protocol - returns a list of Tool objects
            tools_list = await self.client.list_tools()

            # Store tools by name
            for tool in tools_list:
                self.tools[tool.name] = {
                    "name": tool.name,
                    "description": tool.description if tool.description else "",
                    "inputSchema": tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                }
                logger.debug(f"Discovered tool: {tool.name}")

        except Exception as e:
            logger.error(f"Error discovering tools: {e}")
            raise

    def get_tools(self) -> list[FunctionTool]:
        """
        Get available tools as LlamaIndex FunctionTool objects.

        Returns:
            List of FunctionTool objects
        """
        if not self._connected:
            logger.warning("Client not connected. Call connect() first.")
            return []

        llama_tools = []

        for tool_name, tool_info in self.tools.items():
            # Create an async callable function for this tool
            def create_tool_function(name: str):
                async def async_tool_function(**kwargs) -> Any:
                    """Dynamically created async tool function."""
                    logger.debug(f"async_tool_function called for {name} with kwargs: {kwargs}")

                    # LlamaIndex sometimes passes a single 'kwargs' parameter
                    # instead of unpacking the parameters
                    if len(kwargs) == 1 and 'kwargs' in kwargs:
                        actual_kwargs = dict(kwargs['kwargs'])
                        logger.debug(f"Unwrapping nested kwargs: {actual_kwargs}")
                    else:
                        actual_kwargs = kwargs

                    return await self.call_tool(name, actual_kwargs)

                return async_tool_function

            # Create async FunctionTool
            fn = create_tool_function(tool_name)
            fn.__name__ = tool_name
            fn.__doc__ = tool_info.get("description", f"Tool: {tool_name}")

            # LlamaIndex supports async tools - just pass the async function directly
            llama_tool = FunctionTool.from_defaults(
                fn=fn,
                name=tool_name,
                description=tool_info.get("description", f"Tool: {tool_name}"),
                async_fn=fn,  # Specify as async tool
            )

            llama_tools.append(llama_tool)
            logger.debug(f"Created LlamaIndex async tool: {tool_name}")

        logger.info(f"Converted {len(llama_tools)} MCP tools to LlamaIndex format")
        return llama_tools

    async def call_tool(self, name: str, parameters: dict[str, Any]) -> Any:
        """
        Execute a specific tool with parameters.

        Args:
            name: Tool name
            parameters: Tool parameters

        Returns:
            Tool execution result
        """
        if not self._connected or not self.client:
            raise ValueError("Client not connected. Call connect() first.")

        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not found. Available tools: {list(self.tools.keys())}")

        logger.info(f"Calling tool: {name} with parameters: {parameters}")

        try:
            # Call tool using FastMCP client
            result = await self.client.call_tool(name, parameters)

            # Extract content from result
            if hasattr(result, 'content'):
                # Result is a CallToolResult object
                content_list = result.content
                if content_list and len(content_list) > 0:
                    first_content = content_list[0]
                    if hasattr(first_content, 'text'):
                        # It's a text content
                        import json
                        try:
                            # Try to parse as JSON
                            result_data = json.loads(first_content.text)
                        except:
                            # If not JSON, return as string
                            result_data = first_content.text
                    else:
                        # Return the content object
                        result_data = first_content
                else:
                    result_data = {}
            else:
                # Return result as-is
                result_data = result

            logger.debug(f"Tool {name} returned: {result_data}")
            return result_data

        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}")
            raise

    async def disconnect(self) -> None:
        """Clean up client connection."""
        logger.info("Disconnecting MCP client")
        try:
            if self.client:
                await self.client.__aexit__(None, None, None)
            self._connected = False
            self.client = None
            logger.info("MCP client disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting MCP client: {e}")

    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
