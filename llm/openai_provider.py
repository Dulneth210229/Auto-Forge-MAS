from __future__ import annotations
from typing import Generator
from openai import OpenAI

from config.settings import settings
from llm.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI API implementation of the LLM provider.
    Supports both normal response and streaming response.
    """

    def __init__(self) -> None:
        if not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here":
            raise ValueError(
                "OpenAI API key is missing. Please set OPENAI_API_KEY in your .env file."
            )

        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    def _build_messages(self, user_message: str, system_prompt: str | None = None ) -> list[dict[str, str]]:
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

    def generate_response(self, user_message: str, system_prompt: str | None = None ) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self._build_messages(user_message, system_prompt),
                temperature=settings.llm_temperature,
            )

            return response.choices[0].message.content or ""

        except Exception as error:
            raise RuntimeError(f"OpenAI provider failed: {error}") from error

    def stream_response(self, user_message: str, system_prompt: str | None = None ) -> Generator[str, None, None]:
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=self._build_messages(user_message, system_prompt),
                temperature=settings.llm_temperature,
                stream=True,
            )

            for chunk in stream:
                delta = chunk.choices[0].delta.content

                if delta:
                    yield delta

        except Exception as error:
            raise RuntimeError(f"OpenAI streaming failed: {error}") from error