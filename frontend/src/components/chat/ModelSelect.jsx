import { useOllamaModels, useAgentLlmSettings, useUpdateAgentLlmSettings } from "../../hooks/useLlmSettings";
import { PLACEHOLDER_STAGES } from "../../lib/pipelineStages";
import PillDropdown from "./PillDropdown";

// Model picker for the chat composer, styled as a pill next to AgentSelect (matching Cursor's
// "Grok 4.5" model selector). Important, honestly-stated constraint: no run/revise request
// schema has a per-request model field -- picking a model here actually sets that agent's
// PERSISTENT LLM override (via the existing PUT /settings/llm/agents/{agent_name} route),
// applied before the next run/revise call, not a true "just this one message" scope. The title
// attribute says so explicitly rather than implying per-message scoping that doesn't exist.
export default function ModelSelect({ agentStage }) {
  const agentName = `${agentStage}_agent`;
  const isSelectable = !PLACEHOLDER_STAGES.includes(agentStage);

  const { data: models, isLoading: modelsLoading, error: modelsError } = useOllamaModels();
  const { data: agentSettings } = useAgentLlmSettings();
  const updateOverride = useUpdateAgentLlmSettings();

  const currentSetting = agentSettings?.find((a) => a.agent_name === agentName);

  if (!isSelectable) {
    return (
      <span className="text-xs text-gray-400 dark:text-gray-600 rounded-full px-3 py-1.5">Not available</span>
    );
  }

  if (modelsError) {
    // Ollama unreachable (or a non-Ollama provider is configured) -- degrade to just showing the
    // effective model as read-only text rather than blocking the whole composer.
    return (
      <span
        className="text-xs text-gray-400 dark:text-gray-500 italic px-2 truncate max-w-[140px]"
        title="Could not load model list from Ollama"
      >
        {currentSetting?.model || "model unavailable"}
      </span>
    );
  }

  const options = (models || []).map((model) => ({ value: model, label: model }));
  if (currentSetting?.model && !(models || []).includes(currentSetting.model)) {
    options.unshift({ value: currentSetting.model, label: currentSetting.model });
  }

  return (
    <PillDropdown
      value={currentSetting?.model || ""}
      options={options}
      onChange={(model) => updateOverride.mutate({ agentName, update: { model } })}
      disabled={modelsLoading || updateOverride.isPending}
      title={`Sets ${agentName}'s model from now on (not just this one message)`}
    />
  );
}
