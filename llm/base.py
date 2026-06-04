from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generator


class BaseLLMProvider(ABC):
    """
    Common interface for all LLM providers.

    Every provider must support:
    1. normal full response generation
    2. streaming response generation
    """

    @abstractmethod
    def generate_response(self, user_message: str, system_prompt: str | None = None,) -> str:
        pass

    @abstractmethod
    def stream_response(self, user_message: str, system_prompt: str | None = None,) -> Generator[str, None, None]:
        pass