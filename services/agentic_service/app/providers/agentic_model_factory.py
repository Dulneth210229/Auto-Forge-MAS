"""
Agentic (tool-calling) model factory.

The existing `llm_provider_service` / `BaseLLMProvider` stack is one-shot only
(generate/stream/invoke_agent) and is kept unchanged for Requirement, Domain,
Architecture, and UI/UX agents -- none of them need tool calling.

Agentic nodes (currently only the Coder Agent's ReAct loop) need a real
tool-calling chat model. `init_chat_model` already dispatches to
langchain-anthropic / langchain-openai / langchain-ollama based on a
"provider:model" string, so it is used directly here rather than hand-writing
per-provider wrappers.

The provider comes from the same shared `store.llm_settings` document the rest
of the app uses, so switching provider in one place still works. The *model*
defaults to `settings.AGENTIC_MODEL_OVERRIDE` instead of the shared
`llm_settings["model"]`, because the one-shot prose model and the agentic
coding model have different quality tradeoffs and are usually not the same
model in practice.
"""

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import settings
from app.services.in_memory_store import store


def get_agentic_chat_model() -> BaseChatModel:
    """
    Build the chat model used by agentic (tool-calling) LangGraph nodes.
    """
    llm_settings = store.llm_settings
    provider = llm_settings.get("provider", settings.DEFAULT_LLM_PROVIDER)
    model = settings.AGENTIC_MODEL_OVERRIDE or llm_settings.get("model")

    model_string = f"{provider}:{model}"

    extra_kwargs = {}

    if provider == "ollama":
        # Ollama's server-side default context window (often 2048-4096) is far
        # smaller than this model's actual capability, and is easily blown past
        # by a single tool result containing a real file's contents (e.g.
        # read_ui_component returning a whole .jsx file) -- which silently
        # truncates the conversation and produces degenerate/empty completions
        # rather than an error. Set explicitly, well within the model's real
        # context length, for the agentic path specifically.
        extra_kwargs["num_ctx"] = settings.AGENTIC_OLLAMA_NUM_CTX

    return init_chat_model(
        model_string,
        temperature=llm_settings.get("temperature", settings.LLM_TEMPERATURE),
        timeout=llm_settings.get("timeout_seconds", settings.LLM_TIMEOUT_SECONDS),
        **extra_kwargs,
    )
