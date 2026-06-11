"""
Temporary in-memory database.

Important:
This is only for the first MVP foundation.

Later, this will be replaced with PostgreSQL or MongoDB.

This store now also keeps LLM settings so we can switch between:
- Ollama
- OpenAI/API provider
"""

from typing import Any

from app.core.config import settings


class InMemoryStore:
    """
    Very simple in-memory storage.

    Data will be lost when the backend restarts.
    """

    def __init__(self):
        self.projects: dict[str, dict[str, Any]] = {}
        self.features: dict[str, dict[str, Any]] = {}
        self.artifacts: dict[str, dict[str, Any]] = {}
        self.approvals: dict[str, dict[str, Any]] = {}

        # LLM settings are stored here for MVP.
        # Later, move this to a database table or collection.
        self.llm_settings: dict[str, Any] = {
            "provider": settings.DEFAULT_LLM_PROVIDER,
            "model": settings.DEFAULT_LLM_MODEL,
            "base_url": settings.OLLAMA_BASE_URL,
            "api_key": settings.OPENAI_API_KEY,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
            "streaming_enabled": settings.LLM_STREAMING_ENABLED,
            "timeout_seconds": settings.LLM_TIMEOUT_SECONDS,
        }

    def reset(self) -> None:
        """
        Clear all in-memory data.

        We do not reset LLM settings here because the selected model
        should remain available during local development.
        """
        self.projects.clear()
        self.features.clear()
        self.artifacts.clear()
        self.approvals.clear()


store = InMemoryStore()