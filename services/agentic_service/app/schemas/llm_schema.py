"""
LLM schemas.

These schemas define how LLM settings are stored and updated.

The system should support:
- local Ollama models
- OpenAI API
- future OpenAI-compatible APIs

These settings will later be controlled from the frontend.
For now, they can be updated through backend APIs.
"""

from pydantic import BaseModel, Field


class LLMSettings(BaseModel):
    """
    Current LLM provider settings.

    provider:
        ollama or openai

    model:
        model name, for example:
        - llama3.1
        - qwen2.5-coder
        - gpt-4o-mini

    base_url:
        API base URL.
        For Ollama: http://localhost:11434
        For OpenAI: https://api.openai.com/v1

    api_key_reference:
        We do not expose the real API key.
        This field only tells whether an API key exists.
    """

    provider: str = Field(default="ollama", example="ollama")
    model: str = Field(default="llama3.1", example="llama3.1")
    base_url: str = Field(default="http://localhost:11434")
    api_key_reference: str | None = Field(
        default=None,
        example="OPENAI_API_KEY_CONFIGURED"
    )
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)
    streaming_enabled: bool = Field(default=True)
    timeout_seconds: int = Field(default=120, ge=1)


class LLMSettingsUpdateRequest(BaseModel):
    """
    Request body for updating LLM settings.

    All fields are optional because the user may update only one setting.
    """

    provider: str | None = Field(default=None, example="ollama")
    model: str | None = Field(default=None, example="llama3.1")
    base_url: str | None = Field(default=None, example="http://localhost:11434")
    api_key: str | None = Field(
        default=None,
        description="Real API key. Do not return this in responses."
    )
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    streaming_enabled: bool | None = None
    timeout_seconds: int | None = Field(default=None, ge=1)


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