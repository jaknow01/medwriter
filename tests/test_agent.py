"""Tests for LlamaIndex agent."""

import pytest
from unittest.mock import Mock, MagicMock
from llama_index.core.tools import FunctionTool

from src.worker.agent import MedicalArticleAgent, MEDICAL_ARTICLE_SYSTEM_PROMPT


@pytest.fixture
def mock_tools():
    """Fixture for mock tools."""

    def mock_web_search(query: str) -> str:
        """Mock web search."""
        return f"Search results for: {query}"

    def mock_medical_knowledge(topic: str) -> str:
        """Mock medical knowledge."""
        return f"Medical knowledge about: {topic}"

    tools = [
        FunctionTool.from_defaults(
            fn=mock_web_search,
            name="web_search",
            description="Search the web for medical information",
        ),
        FunctionTool.from_defaults(
            fn=mock_medical_knowledge,
            name="medical_knowledge",
            description="Get medical knowledge",
        ),
    ]

    return tools


def test_agent_initialization_openai(mock_tools):
    """Test agent initialization with OpenAI."""
    agent = MedicalArticleAgent(
        tools=mock_tools,
        llm_provider="openai",
        model_name="gpt-3.5-turbo",
        api_key="test-key",
    )

    assert agent.llm_provider == "openai"
    assert agent.model_name == "gpt-3.5-turbo"
    assert len(agent.tools) == 2
    assert agent.agent is not None


def test_agent_initialization_anthropic(mock_tools):
    """Test agent initialization with Anthropic."""
    agent = MedicalArticleAgent(
        tools=mock_tools,
        llm_provider="anthropic",
        model_name="claude-3-sonnet-20240229",
        api_key="test-key",
    )

    assert agent.llm_provider == "anthropic"
    assert agent.model_name == "claude-3-sonnet-20240229"
    assert len(agent.tools) == 2
    assert agent.agent is not None


def test_agent_initialization_invalid_provider(mock_tools):
    """Test agent initialization with invalid provider."""
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        MedicalArticleAgent(
            tools=mock_tools,
            llm_provider="invalid",
            model_name="test",
            api_key="test-key",
        )


def test_switch_llm_openai_to_anthropic(mock_tools):
    """Test switching from OpenAI to Anthropic."""
    agent = MedicalArticleAgent(
        tools=mock_tools,
        llm_provider="openai",
        model_name="gpt-4",
        api_key="openai-key",
    )

    assert agent.llm_provider == "openai"

    agent.switch_llm(
        llm_provider="anthropic",
        model_name="claude-3-opus-20240229",
        api_key="anthropic-key",
    )

    assert agent.llm_provider == "anthropic"
    assert agent.model_name == "claude-3-opus-20240229"
    assert agent.agent is not None


def test_switch_llm_anthropic_to_openai(mock_tools):
    """Test switching from Anthropic to OpenAI."""
    agent = MedicalArticleAgent(
        tools=mock_tools,
        llm_provider="anthropic",
        model_name="claude-3-sonnet-20240229",
        api_key="anthropic-key",
    )

    assert agent.llm_provider == "anthropic"

    agent.switch_llm(
        llm_provider="openai",
        model_name="gpt-4-turbo",
        api_key="openai-key",
    )

    assert agent.llm_provider == "openai"
    assert agent.model_name == "gpt-4-turbo"


def test_switch_llm_invalid_provider(mock_tools):
    """Test switching to invalid provider."""
    agent = MedicalArticleAgent(
        tools=mock_tools,
        llm_provider="openai",
        model_name="gpt-4",
        api_key="test-key",
    )

    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        agent.switch_llm(
            llm_provider="invalid",
            model_name="test",
            api_key="test-key",
        )


def test_system_prompt_content():
    """Test that system prompt contains expected content."""
    assert "medical article writing assistant" in MEDICAL_ARTICLE_SYSTEM_PROMPT.lower()
    assert "citations" in MEDICAL_ARTICLE_SYSTEM_PROMPT.lower()
    assert "research" in MEDICAL_ARTICLE_SYSTEM_PROMPT.lower()


def test_agent_has_tools(mock_tools):
    """Test that agent has access to tools."""
    agent = MedicalArticleAgent(
        tools=mock_tools,
        llm_provider="openai",
        model_name="gpt-3.5-turbo",
        api_key="test-key",
    )

    # Check agent has tools registered
    assert len(agent.tools) == len(mock_tools)
    assert agent.agent is not None


def test_agent_custom_parameters(mock_tools):
    """Test agent with custom temperature and max_tokens."""
    agent = MedicalArticleAgent(
        tools=mock_tools,
        llm_provider="openai",
        model_name="gpt-4",
        api_key="test-key",
        temperature=0.5,
        max_tokens=1000,
    )

    assert agent.llm is not None
    # LLM should be configured with custom parameters
    assert agent.agent is not None
