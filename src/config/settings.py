"""Configuration management for MedWriter."""

from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Configuration
    llm_provider: Literal["openai", "anthropic"] = Field(
        default="openai",
        description="LLM provider to use (openai or anthropic)"
    )
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key"
    )
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key"
    )
    model_name: str = Field(
        default="gpt-4",
        description="Model name to use"
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

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Validate LLM provider."""
        if v not in ["openai", "anthropic"]:
            raise ValueError("llm_provider must be 'openai' or 'anthropic'")
        return v

    def validate_api_keys(self) -> None:
        """Validate that required API key is present for selected provider."""
        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when using Anthropic provider")

    def get_model_defaults(self) -> dict:
        """Get default model configuration based on provider."""
        if self.llm_provider == "openai":
            return {
                "model": self.model_name or "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000,
            }
        else:  # anthropic
            return {
                "model": self.model_name or "claude-3-opus-20240229",
                "temperature": 0.7,
                "max_tokens": 2000,
            }


# Global settings instance
settings = Settings()
