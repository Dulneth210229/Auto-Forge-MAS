"""
LLM schemas.

These schemas define the shape of LLM settings API data.

Important:
This file should NOT control the real selected Ollama/OpenAI model.

The real model should come from:

.env
  -> app/core/config.py
  -> app/services/in_memory_store.py
  -> app/services/llm_provider_service.py

This schema file only validates and documents API request/response data.
"""

from pydantic import BaseModel, Field


class LLMSettings(BaseModel):
    """
    Current LLM provider settings returned by the API.

    Do not put real default model values here.
    The actual values must be passed from llm_provider_service.py.
    """

    provider: str = Field(..., example="ollama")
    model: str = Field(..., example="gemma4")
    base_url: str = Field(..., example="http://localhost:11434")

    api_key_reference: str | None = Field(
        default=None,
        example="OPENAI_API_KEY_CONFIGURED"
    )

    temperature: float = Field(..., ge=0.0, le=2.0, example=0.2)
    max_tokens: int = Field(..., ge=1, example=4097)
    streaming_enabled: bool = Field(..., example=True)
    timeout_seconds: int = Field(..., ge=1, example=120)


class LLMSettingsUpdateRequest(BaseModel):
    """
    Request body for updating LLM settings.

    All fields are optional because the user may update only one setting.

    Example:
    {
      "provider": "ollama",
      "model": "gemma4",
      "base_url": "http://localhost:11434"
    }
    """

    provider: str | None = Field(default=None, example="ollama")
    model: str | None = Field(default=None, example="gemma4")
    base_url: str | None = Field(default=None, example="http://localhost:11434")

    api_key: str | None = Field(
        default=None,
        description="Real API key. Do not return this in responses."
    )

    temperature: float | None = Field(default=None, ge=0.0, le=2.0, example=0.3)
    max_tokens: int | None = Field(default=None, ge=1, example=4097)
    streaming_enabled: bool | None = Field(default=None, example=True)
    timeout_seconds: int | None = Field(default=None, ge=1, example=120)


class LLMGenerateRequest(BaseModel):
    """
    Request body used to test the selected LLM provider.
    """

    prompt: str = Field(..., example="Say hello from AutoForge.")

    system_prompt: str | None = Field(
        default=None,
        example="You are a helpful AI assistant."
    )


class LLMGenerateResponse(BaseModel):
    """
    Response returned after testing the LLM provider.
    """

    provider: str
    model: str
    output: str