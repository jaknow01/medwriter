"""Tests for configuration module."""

import json
import pytest
from pathlib import Path
from pydantic import ValidationError

from src.config.settings import Settings
from src.config.json_config import (
    AppConfig,
    AgentConfig,
    PdfConfig,
    ChunkerConfig,
    ContextConfig,
    TitleGeneratorConfig,
    load_config,
)


# --- Settings tests (secrets & infrastructure) ---


def test_settings_defaults():
    """Test default settings values."""
    settings = Settings(
        openai_api_key="test-key",
        anthropic_api_key="test-key",
    )

    assert settings.mcp_server_url == "http://localhost:8000"
    assert settings.mcp_server_port == 8000
    assert settings.log_level == "INFO"
    assert settings.log_file == "logs/medwriter.log"


def test_settings_custom_values():
    """Test custom settings values."""
    settings = Settings(
        openai_api_key="sk-test",
        anthropic_api_key="sk-ant-test",
        mcp_server_url="http://localhost:9000",
        mcp_server_port=9000,
        log_level="DEBUG",
    )

    assert settings.mcp_server_url == "http://localhost:9000"
    assert settings.mcp_server_port == 9000
    assert settings.log_level == "DEBUG"


def test_validate_api_keys_openai():
    """Test API key validation for OpenAI."""
    settings = Settings(openai_api_key="sk-test")
    settings.validate_api_keys("openai")  # Should not raise


def test_validate_api_keys_openai_missing():
    """Test API key validation fails when OpenAI key missing."""
    settings = Settings(anthropic_api_key="sk-ant-test")
    with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
        settings.validate_api_keys("openai")


def test_validate_api_keys_anthropic():
    """Test API key validation for Anthropic."""
    settings = Settings(anthropic_api_key="sk-ant-test")
    settings.validate_api_keys("anthropic")  # Should not raise


def test_validate_api_keys_anthropic_missing():
    """Test API key validation fails when Anthropic key missing."""
    settings = Settings(openai_api_key="sk-test")
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
        settings.validate_api_keys("anthropic")


# --- AppConfig tests (JSON-based behavioral config) ---


def test_app_config_defaults():
    """Test AppConfig with all defaults."""
    config = AppConfig()

    assert config.agent.llm_provider == "openai"
    assert config.agent.model_name == "gpt-4.1-mini"
    assert config.agent.temperature == 0.7
    assert config.agent.max_tokens == 4096
    assert config.agent.max_steps == 15

    assert config.pdf.chunker.type == "sentence"
    assert config.pdf.chunker.params == {"chunk_size": 1000, "chunk_overlap": 200}
    assert config.pdf.top_k == 5

    assert config.context.max_messages == 20
    assert config.context.title_generator.model_name == "gpt-4o-mini"
    assert config.context.title_generator.temperature == 0.7
    assert config.context.title_generator.max_tokens == 50


def test_app_config_custom_values():
    """Test AppConfig with custom values."""
    config = AppConfig(
        agent=AgentConfig(
            llm_provider="anthropic",
            model_name="claude-3-opus",
            temperature=0.5,
            max_tokens=8192,
            max_steps=20,
        ),
        pdf=PdfConfig(
            chunker=ChunkerConfig(type="token", params={"chunk_size": 500}),
            top_k=10,
        ),
        context=ContextConfig(max_messages=30),
    )

    assert config.agent.llm_provider == "anthropic"
    assert config.agent.model_name == "claude-3-opus"
    assert config.agent.max_steps == 20
    assert config.pdf.chunker.type == "token"
    assert config.pdf.chunker.params == {"chunk_size": 500}
    assert config.pdf.top_k == 10
    assert config.context.max_messages == 30


def test_load_config_from_json(tmp_path):
    """Test loading config from a JSON file."""
    config_data = {
        "agent": {
            "llm_provider": "anthropic",
            "model_name": "claude-3-sonnet",
            "temperature": 0.3,
        },
        "pdf": {
            "top_k": 8,
        },
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data))

    config = load_config(tmp_path)

    assert config.agent.llm_provider == "anthropic"
    assert config.agent.model_name == "claude-3-sonnet"
    assert config.agent.temperature == 0.3
    # Defaults for unspecified fields
    assert config.agent.max_tokens == 4096
    assert config.pdf.top_k == 8
    assert config.pdf.chunker.type == "sentence"  # default
    assert config.context.max_messages == 20  # default


def test_load_config_missing_file(tmp_path):
    """Test loading config when file doesn't exist — uses defaults."""
    config = load_config(tmp_path)

    assert config.agent.llm_provider == "openai"
    assert config.agent.model_name == "gpt-4.1-mini"
    assert config.pdf.chunker.type == "sentence"
    assert config.context.max_messages == 20


def test_load_config_partial_file(tmp_path):
    """Test loading config with only some sections."""
    config_data = {"context": {"max_messages": 50}}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data))

    config = load_config(tmp_path)

    assert config.context.max_messages == 50
    # Other sections use defaults
    assert config.agent.llm_provider == "openai"
    assert config.pdf.top_k == 5


def test_load_config_invalid_json(tmp_path):
    """Test loading config with invalid JSON raises error."""
    config_file = tmp_path / "config.json"
    config_file.write_text("{ invalid json }")

    with pytest.raises(json.JSONDecodeError):
        load_config(tmp_path)
