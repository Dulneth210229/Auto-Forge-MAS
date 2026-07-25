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
    AgentLLMOverrideUpdateRequest,
    AgentLLMSettingsResponse,
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


@router.get("/agents", response_model=list[AgentLLMSettingsResponse])
def list_agent_llm_settings():
    """
    Return every configurable agent's effective LLM settings (global default, or a per-agent
    override where one has been set) -- lets the UI show/configure each agent independently,
    not just one shared global config.
    """
    return llm_provider_service.list_agent_overrides()


@router.put("/agents/{agent_name}", response_model=AgentLLMSettingsResponse)
def update_agent_llm_settings(agent_name: str, request: AgentLLMOverrideUpdateRequest):
    """
    Set (merge into) one agent's LLM override. Only fields provided are changed.
    """
    try:
        return llm_provider_service.set_agent_override(agent_name, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.delete("/agents/{agent_name}", response_model=AgentLLMSettingsResponse)
def clear_agent_llm_settings(agent_name: str):
    """
    Remove an agent's override entirely, reverting it to the global default.
    """
    try:
        return llm_provider_service.clear_agent_override(agent_name)
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


@router.post("/agents/{agent_name}/test", response_model=LLMGenerateResponse)
async def test_agent_llm_provider(agent_name: str, request: LLMGenerateRequest):
    """
    Test one agent's effective LLM settings (its override if it has one, otherwise the global
    default) -- distinct from /test, which always tests the global default regardless of any
    per-agent override.
    """
    try:
        provider = llm_provider_service.get_provider(agent_name=agent_name)

        output = await provider.generate(
            prompt=request.prompt,
            system_prompt=request.system_prompt
        )

        effective = next(
            (a for a in llm_provider_service.list_agent_overrides() if a.agent_name == agent_name),
            None,
        )

        if effective is None:
            raise HTTPException(status_code=400, detail=f"Unknown agent '{agent_name}'.")

        return LLMGenerateResponse(provider=effective.provider, model=effective.model, output=output)

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"LLM provider test failed: {str(error)}"
        )