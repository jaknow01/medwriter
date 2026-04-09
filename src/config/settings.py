"""Configuration management for MedWriter.

Secrets and infrastructure settings are loaded from environment variables (.env).
Behavioral parameters (models, chunking, context) are in config/config.json — see json_config.py.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Infrastructure and secrets loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key"
    )
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key"
    )

    # MCP Configuration
    mcp_server_url: str = Field(
        default="http://localhost:8000",
        description="MCP server URL"
    )
    mcp_server_port: int = Field(
        default=8000,
        description="MCP server port"
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    log_file: str = Field(
        default="logs/medwriter.log",
        description="Log file path"
    )

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://medwriter:password@localhost:5432/medwriter_db",
        description="PostgreSQL async connection URL"
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )

    # ChromaDB Configuration
    chromadb_host: str = Field(
        default="localhost",
        description="ChromaDB server host"
    )
    chromadb_port: int = Field(
        default=8000,
        description="ChromaDB server port"
    )

    # Worker Configuration
    worker_id: str = Field(
        default="worker-1",
        description="Unique worker identifier"
    )

    def validate_api_keys(self, llm_provider: str) -> None:
        """Validate that required API key is present for the given provider.

        Args:
            llm_provider: LLM provider name from app config ("openai" or "anthropic")
        """
        if llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
        if llm_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when using Anthropic provider")


# Global settings instance
settings = Settings()
