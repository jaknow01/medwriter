"""Main worker module orchestrating agent and MCP client."""

import asyncio
from typing import Literal, List
from uuid import UUID
from loguru import logger

from src.worker.mcp_client import MCPClient
from src.worker.agent import MedicalArticleAgent
from src.worker.title_generator import TitleGenerator
from src.config.settings import Settings
from src.database import DatabaseManager, ConversationRepository, Message
from src.pdf.store import DocumentStore
from src.redis import RedisManager, JobQueue


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

        # Database and Redis components
        self.db_manager: DatabaseManager | None = None
        self.redis_manager: RedisManager | None = None
        self.job_queue: JobQueue | None = None
        self.title_generator: TitleGenerator | None = None
        self.document_store: DocumentStore | None = None

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

            # Initialize database
            logger.info(f"Connecting to database at {self.settings.database_url}")
            self.db_manager = DatabaseManager(self.settings.database_url)
            await self.db_manager.initialize_db()

            # Initialize Redis
            logger.info(f"Connecting to Redis at {self.settings.redis_url}")
            self.redis_manager = RedisManager(self.settings.redis_url)
            await self.redis_manager.connect()
            self.job_queue = JobQueue(self.redis_manager.client)

            # Initialize document store for PDF chunks
            logger.info(f"Connecting to ChromaDB at {self.settings.chromadb_host}:{self.settings.chromadb_port}")
            self.document_store = DocumentStore(
                host=self.settings.chromadb_host, port=self.settings.chromadb_port
            )

            # Initialize title generator
            logger.info("Initializing title generator")
            self.title_generator = TitleGenerator(
                llm_provider=self.settings.llm_provider,
                api_key=api_key,
                model_name="gpt-4o-mini",  # Use cheaper model for titles
            )

            self._initialized = True
            logger.info("Worker initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize worker: {e}")
            await self.shutdown()
            raise

    async def process_query(self, query: str) -> str:
        """
        Process a user query and return response (without conversation context).

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

    def index_pdf_chunks(self, conv_id: UUID, chunks: list[dict]) -> None:
        """Index PDF chunks into ChromaDB grouped by filename.

        Args:
            conv_id: Conversation UUID
            chunks: List of {"text": str, "filename": str}
        """
        if not self.document_store:
            raise RuntimeError("DocumentStore not initialized. Call initialize() first.")
        # Group chunks by filename
        by_file: dict[str, list[str]] = {}
        for chunk in chunks:
            by_file.setdefault(chunk["filename"], []).append(chunk["text"])

        for filename, texts in by_file.items():
            self.document_store.add_chunks(conv_id, texts, filename)
            logger.info(f"Indexed {len(texts)} chunks from '{filename}' for conv {conv_id}")

    def _get_pdf_context(self, conv_id: UUID, query: str) -> str:
        """Retrieve relevant PDF chunks and format as context.

        Args:
            conv_id: Conversation UUID
            query: User query for similarity search

        Returns:
            Formatted context string, or empty string if no documents
        """
        if not self.document_store.has_documents(conv_id):
            return ""

        results = self.document_store.query(
            conv_id, query, top_k=self.settings.pdf_top_k
        )

        if not results:
            return ""

        formatted = "\n\n---\n\n".join(results)
        return f"Relevant context from uploaded PDF documents:\n\n{formatted}"

    async def process_query_with_context(
        self,
        query: str,
        conv_id: UUID,
        save_user_message: bool = True,
    ) -> str:
        """
        Process query with conversation history from database.

        PDF chunks should be indexed separately via index_pdf_chunks()
        before calling this method.

        Args:
            query: User query
            conv_id: Conversation UUID
            save_user_message: Whether to save user message to DB (default True).
                              Set to False when using with API (API saves it first).

        Returns:
            Agent response

        Raises:
            RuntimeError: If worker not initialized
        """
        if not self._initialized or not self.agent:
            raise RuntimeError("Worker not initialized. Call initialize() first.")

        logger.info(f"Processing query with context for conversation {conv_id}")

        async with self.db_manager.get_session() as session:
            repo = ConversationRepository(session)

            # Get or create conversation
            conversation = await repo.get_conversation(conv_id)
            if not conversation:
                logger.info(f"Creating new conversation {conv_id}")
                conversation = await repo.create_conversation(conv_id=conv_id)

            # Get previous messages for context
            messages = await repo.get_messages(conv_id)

            # Build context from previous messages
            context = self._build_context(messages)

            # Add user message to database (if not already saved by API)
            if save_user_message:
                await repo.add_message(conv_id, role="User", content=query)
                logger.debug("Saved user message to database")

            # Retrieve relevant PDF context if documents exist
            pdf_context = ""
            if self.document_store:
                pdf_context = self._get_pdf_context(conv_id, query)

            # Process query with agent (with context)
            full_query = query
            if context:
                full_query = f"{context}\n\nUser: {query}"
            if pdf_context:
                full_query = f"{pdf_context}\n\n{full_query}"

            logger.info(f"Processing with {len(messages)} previous messages as context")
            if pdf_context:
                logger.info("PDF context included in query")
            response = await self.agent.chat(full_query)

            # Add AI response to database
            await repo.add_message(conv_id, role="AI", content=response)

            # Generate title if this is the first message and no title exists
            if not conversation.title and len(messages) <= 1:
                logger.info("Generating title for new conversation")
                title = await self.title_generator.generate_title(query)
                await repo.update_title(conv_id, title)

            logger.info("Query with context processed successfully")
            return response

    def _build_context(self, messages: List[Message]) -> str:
        """
        Build context string from previous messages.

        Args:
            messages: List of previous messages

        Returns:
            Context string
        """
        if not messages:
            return ""

        context_parts = ["Previous conversation:"]
        for msg in messages:
            context_parts.append(f"{msg.role}: {msg.content}")

        return "\n".join(context_parts)

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

            if self.db_manager:
                await self.db_manager.close()
                self.db_manager = None

            if self.redis_manager:
                await self.redis_manager.close()
                self.redis_manager = None

            self.agent = None
            self.job_queue = None
            self.title_generator = None
            self.document_store = None
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
