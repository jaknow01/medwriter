"""LlamaIndex agent for medical article drafting."""

from typing import Literal
from llama_index.core.agent import ReActAgent
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.tools import BaseTool
from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic
from loguru import logger


MEDICAL_ARTICLE_SYSTEM_PROMPT = """\
You are a medical article writing assistant. Your job is to produce medium-length, \
well-sourced medical articles for a healthcare website. The articles will later be \
reviewed by real doctors before publication.

## How to handle the user's request

When you receive a message, decide which phase applies:

### Phase A — The user's request is VAGUE (e.g. just a broad topic, no details about focus or audience).
Respond IMMEDIATELY with 1-2 short clarifying questions. Do NOT call any tools. \
Just output the questions as your final answer so the user can reply. Examples of good questions:
- What specific aspect should the article focus on (treatment, diagnosis, prevention, pathophysiology)?
- Who is the target audience — patients, general public, or medical professionals?
- Should it cover recent advances or provide a general overview?

### Phase B — The user's request is SPECIFIC ENOUGH to write an article (topic + focus are clear).
This also applies when the user answers your clarifying questions from Phase A. \
Now research and write. Follow these steps IN ORDER:

Step 1) find-article-id — search PubMed. The 'query' parameter is REQUIRED.
Step 2) fetch-article-abstracts — get abstracts for the best PMIDs from step 1. Pass 'pmids' as a list.
Step 3) fetch-full-text — OPTIONAL. Only if abstracts lack detail. Takes a single 'pmid' string.
Step 4) generate-citation — get Vancouver citations for all PMIDs you will reference. Pass 'pmids' as a list. Do this ONCE before writing.
Step 5) Write the article with this structure:
   - Title
   - Introduction
   - 2-4 body sections with descriptive headings
   - Conclusion
   - References (numbered [1], [2]... with Vancouver-style citations from step 4)

Article requirements:
- Length: 800-1500 words (excluding references)
- Tone: professional but accessible, explain jargon on first use
- Every major medical claim must have at least one citation
- Do NOT fabricate data or citations — only use information from the tools
- Write in the SAME LANGUAGE as the user's messages

## Tool parameter rules
- find-article-id: search term goes in 'query' (NOT 'title' or 'topic')
- fetch-article-abstracts: pass 'pmids' as a list of strings
- generate-citation: pass 'pmids' as a list of strings
- fetch-full-text: pass a single 'pmid' string
- If a tool call fails, read the error, fix the parameters, and retry once
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
        max_steps: int = 15,
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
            max_steps: Maximum reasoning steps for ReAct agent
        """
        self.tools = tools
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.max_steps = max_steps

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
            max_steps=self.max_steps,
            verbose=True,
        )

        logger.info("Agent initialized successfully")

    async def chat(
        self,
        message: str,
        chat_history: list[ChatMessage] | None = None,
    ) -> str:
        """
        Process a user message and return agent response.

        Args:
            message: User message (current query)
            chat_history: Previous conversation as structured ChatMessage list

        Returns:
            Agent response
        """
        logger.info(f"Processing user message: {message[:100]}...")
        if chat_history:
            logger.info(f"With {len(chat_history)} messages of chat history")

        try:
            result = await self.agent.run(
                user_msg=message,
                chat_history=chat_history,
            )

            response_text = str(result.get("response", result))

            logger.info("Agent response generated successfully")
            logger.debug(f"Response: {response_text[:200]}...")

            return response_text

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise

    async def stream_chat(
        self,
        message: str,
        chat_history: list[ChatMessage] | None = None,
    ):
        """
        Process a user message and stream the response.

        Args:
            message: User message
            chat_history: Previous conversation as structured ChatMessage list

        Yields:
            Response chunks
        """
        logger.info(f"Streaming response for message: {message[:100]}...")

        try:
            # For now, run non-streaming and yield the result
            # (streaming in workflow agents requires async iteration)
            result = await self.agent.run(
                user_msg=message,
                chat_history=chat_history,
            )
            response_text = str(result.get("response", result))

            yield response_text

            logger.info("Streaming response completed")

        except Exception as e:
            logger.error(f"Error streaming message: {e}")
            raise

    def switch_llm(
        self,
        llm_provider: Literal["openai", "anthropic"],
        model_name: str,
        api_key: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        max_steps: int = 15,
    ) -> None:
        """
        Switch to a different LLM provider/model.

        Args:
            llm_provider: New LLM provider
            model_name: New model name
            api_key: API key for the new provider
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            max_steps: Maximum reasoning steps
        """
        logger.info(f"Switching LLM to {llm_provider} ({model_name})")

        self.llm_provider = llm_provider
        self.model_name = model_name
        self.max_steps = max_steps

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
            max_steps=self.max_steps,
            verbose=True,
        )

        logger.info(f"Successfully switched to {llm_provider} ({model_name})")
