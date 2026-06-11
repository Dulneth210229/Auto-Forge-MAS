"""
LLM settings routes.

These APIs allow the backend or frontend to:
- view current LLM settings
- update provider/model settings
- test the selected provider

This is important before implementing agents because all agents
will call the same LLM provider service.
"""

from fastapi import APIRouter, HTTPException

from app.schemas.llm_schema import (
    LLMSettings,
    LLMSettingsUpdateRequest,
    LLMGenerateRequest,
    LLMGenerateResponse,
)
from app.services.llm_provider_service import llm_provider_service

router = APIRouter(prefix="/settings/llm", tags=["LLM Settings"])


@router.get("", response_model=LLMSettings)
def get_llm_settings():
    """
    Return current LLM settings.

    Real API keys are never returned.
    """
    return llm_provider_service.get_settings()


@router.put("", response_model=LLMSettings)
def update_llm_settings(request: LLMSettingsUpdateRequest):
    """
    Update LLM settings.

    Example:
    Switch to Ollama:
    {
      "provider": "ollama",
      "model": "llama3.1",
      "base_url": "http://localhost:11434"
    }

    Example:
    Switch to OpenAI:
    {
      "provider": "openai",
      "model": "gpt-4o-mini",
      "base_url": "https://api.openai.com/v1",
      "api_key": "your_real_key_here"
    }
    """
    try:
        return llm_provider_service.update_settings(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post("/test", response_model=LLMGenerateResponse)
async def test_llm_provider(request: LLMGenerateRequest):
    """
    Test the currently selected LLM provider.

    This is useful before running agents.
    """
    try:
        provider = llm_provider_service.get_provider()

        output = await provider.generate(
            prompt=request.prompt,
            system_prompt=request.system_prompt
        )

        settings = llm_provider_service.get_settings()

        return LLMGenerateResponse(
            provider=settings.provider,
            model=settings.model,
            output=output
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"LLM provider test failed: {str(error)}"
        )