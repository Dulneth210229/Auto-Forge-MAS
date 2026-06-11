"""
LLM provider service.

This service is the main entry point for agents.

Agents should not directly create OllamaProvider or OpenAIProvider.
Instead, agents should call:

    llm_provider_service.get_provider()

Why:
- Keeps provider selection centralized.
- Allows switching provider from settings.
- Avoids repeating configuration code in every agent.
"""

from app.providers.base_provider import BaseLLMProvider
from app.providers.ollama_provider import OllamaProvider
from app.providers.openai_provider import OpenAIProvider
from app.schemas.llm_schema import LLMSettings, LLMSettingsUpdateRequest
from app.services.in_memory_store import store


class LLMProviderService:
    """
    Service for managing LLM configuration and provider creation.
    """

    SUPPORTED_PROVIDERS = {"ollama", "openai"}

    def get_settings(self) -> LLMSettings:
        """
        Return current LLM settings.

        Important:
        Do not return the real API key.
        Only return whether the key is configured.
        """
        current = store.llm_settings

        api_key_reference = None
        if current.get("api_key"):
            api_key_reference = "API_KEY_CONFIGURED"

        return LLMSettings(
            provider=current["provider"],
            model=current["model"],
            base_url=current["base_url"],
            api_key_reference=api_key_reference,
            temperature=current["temperature"],
            max_tokens=current["max_tokens"],
            streaming_enabled=current["streaming_enabled"],
            timeout_seconds=current["timeout_seconds"],
        )

    def update_settings(self, request: LLMSettingsUpdateRequest) -> LLMSettings:
        """
        Update selected LLM settings.

        Only fields provided by the user are changed.
        """
        current = store.llm_settings

        if request.provider is not None:
            provider = request.provider.lower()

            if provider not in self.SUPPORTED_PROVIDERS:
                raise ValueError(
                    f"Unsupported provider '{request.provider}'. "
                    f"Supported providers: {self.SUPPORTED_PROVIDERS}"
                )

            current["provider"] = provider

        if request.model is not None:
            current["model"] = request.model

        if request.base_url is not None:
            current["base_url"] = request.base_url.rstrip("/")

        if request.api_key is not None:
            # Store the real key internally only.
            # Never return this key through API responses.
            current["api_key"] = request.api_key

        if request.temperature is not None:
            current["temperature"] = request.temperature

        if request.max_tokens is not None:
            current["max_tokens"] = request.max_tokens

        if request.streaming_enabled is not None:
            current["streaming_enabled"] = request.streaming_enabled

        if request.timeout_seconds is not None:
            current["timeout_seconds"] = request.timeout_seconds

        return self.get_settings()

    def get_provider(self) -> BaseLLMProvider:
        """
        Create and return the currently selected provider instance.
        """
        current = store.llm_settings

        provider_name = current["provider"]

        if provider_name == "ollama":
            return OllamaProvider(
                model=current["model"],
                base_url=current["base_url"],
                temperature=current["temperature"],
                max_tokens=current["max_tokens"],
                timeout_seconds=current["timeout_seconds"],
            )

        if provider_name == "openai":
            return OpenAIProvider(
                model=current["model"],
                base_url=current["base_url"],
                api_key=current.get("api_key"),
                temperature=current["temperature"],
                max_tokens=current["max_tokens"],
                timeout_seconds=current["timeout_seconds"],
            )

        raise ValueError(f"Unsupported LLM provider: {provider_name}")


llm_provider_service = LLMProviderService()