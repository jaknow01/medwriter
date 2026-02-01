"""LlamaIndex agent for medical article drafting."""

from typing import Literal
from llama_index.core.agent import ReActAgent
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.tools import BaseTool
from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic
from loguru import logger


MEDICAL_ARTICLE_SYSTEM_PROMPT = """You are a medical article writing assistant. Your role is to help draft comprehensive, accurate medical articles for a healthcare website.

When drafting articles:
1. Use the available tools to research medical information
2. Structure articles with clear sections (Introduction, Main Content, Conclusion)
3. Include proper citations for medical facts
4. Write in clear, accessible language for general audience
5. Maintain scientific accuracy

Available tools allow you to search for information, access medical knowledge, and generate citations. Use them appropriately to create well-researched content.

Important guidelines:
- Always verify medical information using multiple sources when possible
- Use citations to back up medical claims
- Avoid medical jargon when simpler terms suffice
- Be thorough but concise
- Maintain a professional, informative tone
"""


class MedicalArticleAgent:
    """Agent for drafting medical articles using LlamaIndex."""

    def __init__(
        self,
        tools: list[BaseTool],
        llm_provider: Literal["openai", "anthropic"] = "openai",
        model_name: str = "gpt-4",
        api_key: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ):
        """
        Initialize the medical article agent.

        Args:
            tools: List of tools available to the agent
            llm_provider: LLM provider (openai or anthropic)
            model_name: Model name to use
            api_key: API key for the LLM provider
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        """
        self.tools = tools
        self.llm_provider = llm_provider
        self.model_name = model_name

        logger.info(f"Initializing agent with {llm_provider} ({model_name})")
        logger.debug(f"Agent has {len(tools)} tools available")

        # Initialize LLM based on provider
        if llm_provider == "openai":
            self.llm = OpenAI(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        elif llm_provider == "anthropic":
            self.llm = Anthropic(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")

        # Initialize ReAct agent
        self.agent = ReActAgent(
            name="MedicalArticleAgent",
            description="Agent for drafting medical articles",
            system_prompt=MEDICAL_ARTICLE_SYSTEM_PROMPT,
            tools=self.tools,
            llm=self.llm,
            verbose=True,
        )

        # Chat history
        self.chat_history: list[ChatMessage] = []

        logger.info("Agent initialized successfully")

    async def chat(self, message: str) -> str:
        """
        Process a user message and return agent response.

        Args:
            message: User message

        Returns:
            Agent response
        """
        logger.info(f"Processing user message: {message[:100]}...")

        try:
            # Add user message to history
            self.chat_history.append(
                ChatMessage(role=MessageRole.USER, content=message)
            )

            # Run agent workflow
            result = await self.agent.run(user_msg=message)

            # Extract response text
            response_text = str(result.get("response", result))

            # Add assistant response to history
            self.chat_history.append(
                ChatMessage(role=MessageRole.ASSISTANT, content=response_text)
            )

            logger.info("Agent response generated successfully")
            logger.debug(f"Response: {response_text[:200]}...")

            return response_text

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise

    async def stream_chat(self, message: str):
        """
        Process a user message and stream the response.

        Args:
            message: User message

        Yields:
            Response chunks
        """
        logger.info(f"Streaming response for message: {message[:100]}...")

        try:
            # Add user message to history
            self.chat_history.append(
                ChatMessage(role=MessageRole.USER, content=message)
            )

            # For now, run non-streaming and yield the result
            # (streaming in workflow agents requires async iteration)
            result = await self.agent.run(user_msg=message)
            response_text = str(result.get("response", result))

            # Yield the response (for now, as single chunk)
            yield response_text

            # Add complete response to history
            self.chat_history.append(
                ChatMessage(role=MessageRole.ASSISTANT, content=response_text)
            )

            logger.info("Streaming response completed")

        except Exception as e:
            logger.error(f"Error streaming message: {e}")
            raise

    def reset_chat_history(self) -> None:
        """Clear the chat history."""
        logger.info("Resetting chat history")
        self.chat_history = []

    def get_chat_history(self) -> list[ChatMessage]:
        """Get the current chat history."""
        return self.chat_history

    def switch_llm(
        self,
        llm_provider: Literal["openai", "anthropic"],
        model_name: str,
        api_key: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> None:
        """
        Switch to a different LLM provider/model.

        Args:
            llm_provider: New LLM provider
            model_name: New model name
            api_key: API key for the new provider
            temperature: Sampling temperature
            max_tokens: Maximum tokens
        """
        logger.info(f"Switching LLM to {llm_provider} ({model_name})")

        self.llm_provider = llm_provider
        self.model_name = model_name

        # Create new LLM
        if llm_provider == "openai":
            self.llm = OpenAI(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        elif llm_provider == "anthropic":
            self.llm = Anthropic(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")

        # Recreate agent with new LLM
        self.agent = ReActAgent(
            name="MedicalArticleAgent",
            description="Agent for drafting medical articles",
            system_prompt=MEDICAL_ARTICLE_SYSTEM_PROMPT,
            tools=self.tools,
            llm=self.llm,
            verbose=True,
        )

        logger.info(f"Successfully switched to {llm_provider} ({model_name})")
