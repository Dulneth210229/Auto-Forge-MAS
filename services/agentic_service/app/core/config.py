"""
Application configuration file.

This file reads environment variables and exposes them through
a single settings object.

The LLM provider layer depends on this file to know:
- default provider
- default model
- Ollama URL
- OpenAI API URL
- timeout
- generation settings

Important:
Do not hardcode API keys in source code.
Use .env for local development.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Main application settings.

    Values are loaded from:
    1. Environment variables
    2. .env file if available
    3. Default values written below
    """

    APP_NAME: str = "AutoForge Agentic SDLC Backend"
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"

    API_PREFIX: str = "/api/v1"
    OUTPUT_DIR: str = "outputs"

    # -----------------------------
    # LLM Provider Defaults
    # -----------------------------

    DEFAULT_LLM_PROVIDER: str = "ollama"
    DEFAULT_LLM_MODEL: str = "llama3.1"

    # Ollama runs locally by default.
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # OpenAI-compatible settings.
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Common generation settings.
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 4096
    LLM_TIMEOUT_SECONDS: int = 120
    LLM_STREAMING_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()