"""
Application configuration file.

This file reads environment variables and exposes them through
a single settings object.

Why this file exists:
- Avoid hardcoding configuration values.
- Keep app name, API prefix, output directory, and LLM settings centralized.
- Make it easier to switch between development, testing, and production.
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

    # Root folder where generated artifacts will be saved.
    OUTPUT_DIR: str = "outputs"

    # Default LLM configuration.
    # Later this will be moved to database-based LLM settings.
    DEFAULT_LLM_PROVIDER: str = "ollama"
    DEFAULT_LLM_MODEL: str = "llama3.1"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OPENAI_API_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()