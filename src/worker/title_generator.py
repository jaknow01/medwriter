"""LLM-based conversation title generation."""

from typing import Literal

from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic
from loguru import logger


class TitleGenerator:
    """Generate conversation titles using LLM (separate from agent)."""

    def __init__(
        self,
        llm_provider: Literal["openai", "anthropic"],
        api_key: str,
        model_name: str = "gpt-4o-mini",
    ):
        """Initialize title generator.

        Args:
            llm_provider: LLM provider ("openai" or "anthropic")
            api_key: API key for the provider
            model_name: Model name to use
        """
        self.llm_provider = llm_provider

        if llm_provider == "openai":
            self.llm = OpenAI(
                model=model_name,
                api_key=api_key,
                temperature=0.7,
                max_tokens=50,  # Very short for titles
            )
        elif llm_provider == "anthropic":
            self.llm = Anthropic(
                model=model_name,
                api_key=api_key,
                temperature=0.7,
                max_tokens=50,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")

        logger.info(f"TitleGenerator initialized with {llm_provider}")

    async def generate_title(self, first_message: str) -> str:
        """Generate a short descriptive title from the first user message.

        Args:
            first_message: First user message in conversation

        Returns:
            Generated title (max 200 chars)
        """
        prompt = f"""Generate a very short (max 8 words) descriptive title for a medical article conversation that starts with this question:

"{first_message}"

Return ONLY the title, nothing else. No quotes, no explanations."""

        try:
            response = await self.llm.acomplete(prompt)
            title = str(response).strip().strip('"\'')

            # Truncate to 200 chars max
            if len(title) > 200:
                title = title[:197] + "..."

            logger.info(f"Generated title: {title}")
            return title

        except Exception as e:
            logger.error(f"Error generating title: {e}")
            # Fallback to first few words of message
            words = first_message.split()[:8]
            fallback = " ".join(words) + "..."
            logger.info(f"Using fallback title: {fallback}")
            return fallback
