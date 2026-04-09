"""Configuration module — secrets from env, behavior from JSON."""

from src.config.settings import Settings, settings
from src.config.json_config import (
    AppConfig,
    AgentConfig,
    PdfConfig,
    ChunkerConfig,
    ContextConfig,
    TitleGeneratorConfig,
    app_config,
    load_config,
)

__all__ = [
    "Settings",
    "settings",
    "AppConfig",
    "AgentConfig",
    "PdfConfig",
    "ChunkerConfig",
    "ContextConfig",
    "TitleGeneratorConfig",
    "app_config",
    "load_config",
]
