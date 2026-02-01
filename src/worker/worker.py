"""Main worker module orchestrating agent and MCP client."""

import asyncio
from typing import Literal
from loguru import logger

from src.worker.mcp_client import MCPClient
from src.worker.agent import MedicalArticleAgent
from src.config.settings import Settings


class Worker:
    """Worker that orchestrates MCP client and LlamaIndex agent."""

    def __init__(self, settings: Settings):
        """
        Initialize worker.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.mcp_client: MCPClient | None = None
        self.agent: MedicalArticleAgent | None = None
        self._initialized = False

        logger.info("Worker instance created")

    async def initialize(self) -> None:
        """Initialize MCP client and agent."""
        logger.info("Initializing worker...")

        try:
            # Validate API keys
            self.settings.validate_api_keys()

            # Initialize MCP client
            logger.info(f"Connecting to MCP server at {self.settings.mcp_server_url}")
            self.mcp_client = MCPClient(
                server_url=self.settings.mcp_server_url,
                timeout=30,
            )

            # Connect and discover tools
            connected = await self.mcp_client.connect()
            if not connected:
                raise RuntimeError("Failed to connect to MCP server")

            # Get tools from MCP client
            tools = self.mcp_client.get_tools()
            logger.info(f"Retrieved {len(tools)} tools from MCP server")

            # Get model configuration
            model_config = self.settings.get_model_defaults()
            api_key = (
                self.settings.openai_api_key
                if self.settings.llm_provider == "openai"
                else self.settings.anthropic_api_key
            )

            # Initialize agent
            logger.info(f"Creating agent with {self.settings.llm_provider} ({model_config['model']})")
            self.agent = MedicalArticleAgent(
                tools=tools,
                llm_provider=self.settings.llm_provider,
                model_name=model_config["model"],
                api_key=api_key,
                temperature=model_config["temperature"],
                max_tokens=model_config["max_tokens"],
            )

            self._initialized = True
            logger.info("Worker initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize worker: {e}")
            await self.shutdown()
            raise

    async def process_query(self, query: str) -> str:
        """
        Process a user query and return response.

        Args:
            query: User query

        Returns:
            Agent response

        Raises:
            RuntimeError: If worker not initialized
        """
        if not self._initialized or not self.agent:
            raise RuntimeError("Worker not initialized. Call initialize() first.")

        logger.info(f"Processing query: {query[:100]}...")

        try:
            response = await self.agent.chat(query)
            logger.info("Query processed successfully")
            return response

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            raise

    async def stream_query(self, query: str):
        """
        Process a user query and stream response.

        Args:
            query: User query

        Yields:
            Response chunks

        Raises:
            RuntimeError: If worker not initialized
        """
        if not self._initialized or not self.agent:
            raise RuntimeError("Worker not initialized. Call initialize() first.")

        logger.info(f"Streaming response for query: {query[:100]}...")

        try:
            async for chunk in self.agent.stream_chat(query):
                yield chunk
            logger.info("Streaming query processed successfully")

        except Exception as e:
            logger.error(f"Error streaming query: {e}")
            raise

    def reset_conversation(self) -> None:
        """Reset the conversation history."""
        if not self.agent:
            logger.warning("Cannot reset conversation - agent not initialized")
            return

        logger.info("Resetting conversation history")
        self.agent.reset_chat_history()

    async def switch_llm_provider(
        self,
        provider: Literal["openai", "anthropic"],
        model_name: str | None = None,
    ) -> None:
        """
        Switch to a different LLM provider.

        Args:
            provider: New LLM provider
            model_name: Optional model name (uses default if not provided)
        """
        if not self._initialized or not self.agent:
            raise RuntimeError("Worker not initialized")

        logger.info(f"Switching LLM provider to {provider}")

        # Update settings
        self.settings.llm_provider = provider
        if model_name:
            self.settings.model_name = model_name

        # Validate new API key
        self.settings.validate_api_keys()

        # Get new model config
        model_config = self.settings.get_model_defaults()
        api_key = (
            self.settings.openai_api_key
            if provider == "openai"
            else self.settings.anthropic_api_key
        )

        # Switch agent's LLM
        self.agent.switch_llm(
            llm_provider=provider,
            model_name=model_config["model"],
            api_key=api_key,
            temperature=model_config["temperature"],
            max_tokens=model_config["max_tokens"],
        )

        logger.info(f"Successfully switched to {provider}")

    async def shutdown(self) -> None:
        """Clean up worker resources."""
        logger.info("Shutting down worker...")

        try:
            if self.mcp_client:
                await self.mcp_client.disconnect()
                self.mcp_client = None

            self.agent = None
            self._initialized = False

            logger.info("Worker shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    def is_initialized(self) -> bool:
        """Check if worker is initialized."""
        return self._initialized

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
