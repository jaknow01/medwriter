"""LLM-based article summarization for context window management."""

from typing import Literal

from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic
from loguru import logger


class ArticleSummarizer:
    """Summarize long article responses for use in conversation context."""

    def __init__(
        self,
        llm_provider: Literal["openai", "anthropic"],
        api_key: str,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_tokens: int = 200,
    ):
        """Initialize article summarizer.

        Args:
            llm_provider: LLM provider ("openai" or "anthropic")
            api_key: API key for the provider
            model_name: Model name to use (cheap/fast model recommended)
            temperature: Sampling temperature (low for factual summaries)
            max_tokens: Maximum tokens for summary output
        """
        self.llm_provider = llm_provider

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

        logger.info(f"ArticleSummarizer initialized with {llm_provider} ({model_name})")

    async def summarize(self, article: str) -> str:
        """Generate a concise summary of a medical article.

        The summary is used in conversation history instead of the full article
        to keep the context window compact.

        Args:
            article: Full article text

        Returns:
            Summary (1-3 sentences)
        """
        prompt = f"""Summarize the following medical article in 3-8 sentences.
Focus on: the main topic, key conclusions, and number of sources cited.
Write in the SAME LANGUAGE as the article.
Return ONLY the summary, nothing else.

Article:
{article}"""

        try:
            response = await self.llm.acomplete(prompt)
            summary = str(response).strip()

            logger.info(f"Generated summary: {summary[:100]}...")
            return summary

        except Exception as e:
            logger.error(f"Error summarizing article: {e}")
            # Fallback: first 2 sentences
            sentences = article.replace("\n", " ").split(".")
            fallback = ". ".join(s.strip() for s in sentences[:2] if s.strip()) + "."
            logger.info(f"Using fallback summary: {fallback[:100]}...")
            return fallback
