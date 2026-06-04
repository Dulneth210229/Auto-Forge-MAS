from __future__ import annotations
from typing import Generator
from ollama import Client

from config.settings import settings
from llm.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    """
    Local Ollama implementation of the LLM provider.
    Supports both normal response and streaming response.
    """

    def __init__(self) -> None:
        self.client = Client(host=settings.ollama_base_url)
        self.model = settings.ollama_model

    def _build_messages(
        self,
        user_message: str,
        system_prompt: str | None = None,
    ) -> list[dict[str, str]]:
        messages = []

        if system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        return messages

    def generate_response(
        self,
        user_message: str,
        system_prompt: str | None = None,
    ) -> str:
        try:
            response = self.client.chat(
                model=self.model,
                messages=self._build_messages(user_message, system_prompt),
                options={
                    "temperature": settings.llm_temperature,
                },
            )

            return response["message"]["content"]

        except Exception as error:
            raise RuntimeError(
                f"Ollama provider failed. Make sure Ollama is running and model '{self.model}' is pulled. Error: {error}"
            ) from error

    def stream_response(
        self,
        user_message: str,
        system_prompt: str | None = None,
    ) -> Generator[str, None, None]:
        try:
            stream = self.client.chat(
                model=self.model,
                messages=self._build_messages(user_message, system_prompt),
                options={
                    "temperature": settings.llm_temperature,
                },
                stream=True,
            )

            for chunk in stream:
                content = chunk["message"]["content"]

                if content:
                    yield content

        except Exception as error:
            raise RuntimeError(
                f"Ollama streaming failed. Make sure Ollama is running and model '{self.model}' is pulled. Error: {error}"
            ) from error