from config.settings import settings
from llm.base import BaseLLMProvider
from llm.openai_provider import OpenAIProvider
from llm.ollama_provider import OllamaProvider


def get_llm_provider() -> BaseLLMProvider:
    """
    Factory function that returns the selected LLM provider.

    The provider is selected using LLM_PROVIDER in the .env file.
    """

    if settings.llm_provider == "openai":
        return OpenAIProvider()

    if settings.llm_provider == "ollama":
        return OllamaProvider()

    raise ValueError(
        f"Unsupported LLM_PROVIDER '{settings.llm_provider}'. Use 'openai' or 'ollama'."
    )