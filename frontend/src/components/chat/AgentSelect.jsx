import { PLACEHOLDER_STAGES, STAGE_LABELS, STAGE_SEQUENCE } from "../../lib/pipelineStages";
import PillDropdown from "./PillDropdown";

const DISPLAY_STAGES = [...STAGE_SEQUENCE, "deployment"];

const OPTIONS = DISPLAY_STAGES.map((stage) => ({
  value: stage,
  label: `${STAGE_LABELS[stage]}${PLACEHOLDER_STAGES.includes(stage) ? " (soon)" : ""}`,
  disabled: PLACEHOLDER_STAGES.includes(stage),
}));

// Agent picker for the chat composer, styled as a rounded pill (matching Cursor's "Agent"
// selector in the composer bar). Every stage is listed (matching the old PipelineNav's "every
// stage always visible" convention); placeholder stages (security/qa/deployment, no real backend
// implementation at all) are disabled rather than hidden. `isRunning` renders a small pulsing dot
// so the currently-selected agent's live/processing state is visible right on the pill itself.
export default function AgentSelect({ value, onChange, isRunning }) {
  const leading = isRunning ? (
    <span className="relative flex h-1.5 w-1.5 flex-shrink-0">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-400 opacity-75" />
      <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-accent-500" />
    </span>
  ) : null;

  return (
    <PillDropdown
      value={value}
      options={OPTIONS}
      onChange={onChange}
      title="Select which agent to talk to"
      leading={leading}
      scrollable={false}
    />
  );
}
