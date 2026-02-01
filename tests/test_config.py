"""Tests for configuration module."""

import pytest
from pydantic import ValidationError

from src.config.settings import Settings


def test_settings_defaults():
    """Test default settings values."""
    settings = Settings(
        openai_api_key="test-key",
        anthropic_api_key="test-key",
    )

    assert settings.llm_provider == "openai"
    assert settings.model_name == "gpt-4"
    assert settings.mcp_server_url == "http://localhost:8000"
    assert settings.mcp_server_port == 8000
    assert settings.log_level == "INFO"
    assert settings.log_file == "logs/medwriter.log"


def test_settings_custom_values():
    """Test custom settings values."""
    settings = Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-ant-test",
        model_name="claude-3-opus-20240229",
        mcp_server_url="http://localhost:9000",
        mcp_server_port=9000,
        log_level="DEBUG",
    )

    assert settings.llm_provider == "anthropic"
    assert settings.model_name == "claude-3-opus-20240229"
    assert settings.mcp_server_url == "http://localhost:9000"
    assert settings.mcp_server_port == 9000
    assert settings.log_level == "DEBUG"


def test_invalid_llm_provider():
    """Test validation of invalid LLM provider."""
    with pytest.raises(ValidationError):
        Settings(
            llm_provider="invalid",
            openai_api_key="test-key",
        )


def test_validate_api_keys_openai():
    """Test API key validation for OpenAI."""
    settings = Settings(
        llm_provider="openai",
        openai_api_key="sk-test",
    )

    # Should not raise
    settings.validate_api_keys()


def test_validate_api_keys_openai_missing():
    """Test API key validation fails when OpenAI key missing."""
    settings = Settings(
        llm_provider="openai",
        anthropic_api_key="sk-ant-test",
    )

    with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
        settings.validate_api_keys()


def test_validate_api_keys_anthropic():
    """Test API key validation for Anthropic."""
    settings = Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-ant-test",
    )

    # Should not raise
    settings.validate_api_keys()


def test_validate_api_keys_anthropic_missing():
    """Test API key validation fails when Anthropic key missing."""
    settings = Settings(
        llm_provider="anthropic",
        openai_api_key="sk-test",
    )

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
        settings.validate_api_keys()


def test_get_model_defaults_openai():
    """Test getting model defaults for OpenAI."""
    settings = Settings(
        llm_provider="openai",
        model_name="gpt-4-turbo",
        openai_api_key="sk-test",
    )

    defaults = settings.get_model_defaults()

    assert defaults["model"] == "gpt-4-turbo"
    assert defaults["temperature"] == 0.7
    assert defaults["max_tokens"] == 2000


def test_get_model_defaults_anthropic():
    """Test getting model defaults for Anthropic."""
    settings = Settings(
        llm_provider="anthropic",
        model_name="claude-3-sonnet-20240229",
        anthropic_api_key="sk-ant-test",
    )

    defaults = settings.get_model_defaults()

    assert defaults["model"] == "claude-3-sonnet-20240229"
    assert defaults["temperature"] == 0.7
    assert defaults["max_tokens"] == 2000


def test_model_name_fallback():
    """Test model name fallback to defaults."""
    settings_openai = Settings(
        llm_provider="openai",
        openai_api_key="sk-test",
        model_name="",  # Empty string
    )
    defaults = settings_openai.get_model_defaults()
    assert defaults["model"] == "gpt-4"

    settings_anthropic = Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-ant-test",
        model_name="",  # Empty string
    )
    defaults = settings_anthropic.get_model_defaults()
    assert defaults["model"] == "claude-3-opus-20240229"
