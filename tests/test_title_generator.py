"""Tests for title generation."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.worker.title_generator import TitleGenerator


@pytest.fixture
def mock_llm_openai(monkeypatch):
    """Mock OpenAI LLM."""
    mock_llm = MagicMock()
    mock_llm.acomplete = AsyncMock(return_value="Diabetes Treatment Guidelines")

    # Mock OpenAI constructor
    def mock_openai_init(self, **kwargs):
        return mock_llm

    monkeypatch.setattr(
        "src.worker.title_generator.OpenAI.__init__",
        lambda self, **kwargs: None
    )
    monkeypatch.setattr(
        "src.worker.title_generator.OpenAI.acomplete",
        mock_llm.acomplete
    )

    return mock_llm


@pytest.fixture
def mock_llm_anthropic(monkeypatch):
    """Mock Anthropic LLM."""
    mock_llm = MagicMock()
    mock_llm.acomplete = AsyncMock(return_value="Hypertension Management Strategies")

    monkeypatch.setattr(
        "src.worker.title_generator.Anthropic.__init__",
        lambda self, **kwargs: None
    )
    monkeypatch.setattr(
        "src.worker.title_generator.Anthropic.acomplete",
        mock_llm.acomplete
    )

    return mock_llm


class TestTitleGenerator:
    """Test title generation."""

    def test_init_openai(self):
        """Test initializing with OpenAI."""
        generator = TitleGenerator(
            llm_provider="openai",
            api_key="test-key",
            model_name="gpt-4o-mini"
        )

        assert generator.llm_provider == "openai"

    def test_init_anthropic(self):
        """Test initializing with Anthropic."""
        generator = TitleGenerator(
            llm_provider="anthropic",
            api_key="test-key",
            model_name="claude-3-haiku-20240307"
        )

        assert generator.llm_provider == "anthropic"

    def test_init_invalid_provider(self):
        """Test initializing with invalid provider."""
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            TitleGenerator(
                llm_provider="invalid",
                api_key="test-key"
            )

    async def test_generate_title_openai(self, mock_llm_openai):
        """Test generating title with OpenAI."""
        generator = TitleGenerator(
            llm_provider="openai",
            api_key="test-key"
        )

        first_message = "What are the treatment guidelines for type 2 diabetes?"
        title = await generator.generate_title(first_message)

        assert title == "Diabetes Treatment Guidelines"
        mock_llm_openai.acomplete.assert_called_once()

    async def test_generate_title_anthropic(self, mock_llm_anthropic):
        """Test generating title with Anthropic."""
        generator = TitleGenerator(
            llm_provider="anthropic",
            api_key="test-key"
        )

        first_message = "How should we manage hypertension in elderly patients?"
        title = await generator.generate_title(first_message)

        assert title == "Hypertension Management Strategies"
        mock_llm_anthropic.acomplete.assert_called_once()

    async def test_generate_title_with_quotes(self, monkeypatch):
        """Test title generation removes quotes."""
        mock_llm = MagicMock()
        mock_llm.acomplete = AsyncMock(return_value='"Quoted Title"')

        monkeypatch.setattr(
            "src.worker.title_generator.OpenAI.__init__",
            lambda self, **kwargs: None
        )
        monkeypatch.setattr(
            "src.worker.title_generator.OpenAI.acomplete",
            mock_llm.acomplete
        )

        generator = TitleGenerator(llm_provider="openai", api_key="test-key")
        title = await generator.generate_title("Test message")

        assert title == "Quoted Title"

    async def test_generate_title_truncation(self, monkeypatch):
        """Test title is truncated to 200 chars."""
        long_title = "A" * 250
        mock_llm = MagicMock()
        mock_llm.acomplete = AsyncMock(return_value=long_title)

        monkeypatch.setattr(
            "src.worker.title_generator.OpenAI.__init__",
            lambda self, **kwargs: None
        )
        monkeypatch.setattr(
            "src.worker.title_generator.OpenAI.acomplete",
            mock_llm.acomplete
        )

        generator = TitleGenerator(llm_provider="openai", api_key="test-key")
        title = await generator.generate_title("Test message")

        assert len(title) == 200
        assert title.endswith("...")

    async def test_generate_title_fallback_on_error(self, monkeypatch):
        """Test fallback to first words on error."""
        mock_llm = MagicMock()
        mock_llm.acomplete = AsyncMock(side_effect=Exception("API error"))

        monkeypatch.setattr(
            "src.worker.title_generator.OpenAI.__init__",
            lambda self, **kwargs: None
        )
        monkeypatch.setattr(
            "src.worker.title_generator.OpenAI.acomplete",
            mock_llm.acomplete
        )

        generator = TitleGenerator(llm_provider="openai", api_key="test-key")
        first_message = "What are the symptoms of diabetes and how to treat it effectively?"
        title = await generator.generate_title(first_message)

        # Should use first 8 words + "..."
        expected = "What are the symptoms of diabetes and how..."
        assert title == expected

    async def test_generate_title_fallback_short_message(self, monkeypatch):
        """Test fallback with short message."""
        mock_llm = MagicMock()
        mock_llm.acomplete = AsyncMock(side_effect=Exception("API error"))

        monkeypatch.setattr(
            "src.worker.title_generator.OpenAI.__init__",
            lambda self, **kwargs: None
        )
        monkeypatch.setattr(
            "src.worker.title_generator.OpenAI.acomplete",
            mock_llm.acomplete
        )

        generator = TitleGenerator(llm_provider="openai", api_key="test-key")
        first_message = "What is diabetes?"
        title = await generator.generate_title(first_message)

        expected = "What is diabetes?..."
        assert title == expected
