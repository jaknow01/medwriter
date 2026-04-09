"""JSON-based configuration for behavioral parameters."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from loguru import logger


class AgentConfig(BaseModel):
    """Main LLM agent configuration."""

    llm_provider: str = Field(default="openai", description="LLM provider (openai or anthropic)")
    model_name: str = Field(default="gpt-4.1-mini", description="Model name")
    temperature: float = Field(default=0.7, description="Sampling temperature")
    max_tokens: int = Field(default=4096, description="Maximum tokens to generate")
    max_steps: int = Field(default=15, description="Max reasoning steps for ReAct agent")


class ChunkerConfig(BaseModel):
    """PDF chunker configuration with selectable type and params."""

    type: str = Field(
        default="sentence",
        description="Chunker type: sentence, token, semantic, sentence_window",
    )
    params: dict[str, Any] = Field(
        default={"chunk_size": 1000, "chunk_overlap": 200},
        description="Parameters passed as kwargs to the selected chunker",
    )


class PdfConfig(BaseModel):
    """PDF processing configuration."""

    chunker: ChunkerConfig = Field(default_factory=ChunkerConfig)
    top_k: int = Field(default=5, description="Number of chunks to retrieve per query")


class TitleGeneratorConfig(BaseModel):
    """Title generator LLM configuration."""

    model_name: str = Field(default="gpt-4o-mini", description="Model for title generation")
    temperature: float = Field(default=0.7, description="Sampling temperature")
    max_tokens: int = Field(default=50, description="Max tokens for title")


class ContextConfig(BaseModel):
    """Conversation context management configuration."""

    max_messages: int = Field(default=20, description="Max messages in sliding window")
    title_generator: TitleGeneratorConfig = Field(default_factory=TitleGeneratorConfig)


class AppConfig(BaseModel):
    """Root application configuration loaded from config/config.json."""

    agent: AgentConfig = Field(default_factory=AgentConfig)
    pdf: PdfConfig = Field(default_factory=PdfConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)


def load_config(config_dir: Path | None = None) -> AppConfig:
    """Load application config from config/config.json.

    Falls back to defaults if the file is missing.
    Partial files are supported — Pydantic fills in missing fields with defaults.

    Args:
        config_dir: Directory containing config.json. Defaults to <project_root>/config/.

    Returns:
        Loaded AppConfig instance.

    Raises:
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    if config_dir is None:
        config_dir = Path(__file__).resolve().parent.parent.parent / "config"

    config_path = config_dir / "config.json"

    if not config_path.exists():
        logger.warning(f"Config file not found at {config_path}, using defaults")
        return AppConfig()

    logger.info(f"Loading config from {config_path}")
    with open(config_path) as f:
        data = json.load(f)

    return AppConfig(**data)


app_config = load_config()
