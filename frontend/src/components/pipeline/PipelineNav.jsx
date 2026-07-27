import clsx from "clsx";
import { PLACEHOLDER_STAGES, STAGE_LABELS, STAGE_ROLE_LABELS, STAGE_SEQUENCE } from "../../lib/pipelineStages";

const DISPLAY_STAGES = [...STAGE_SEQUENCE, "deployment"];

const DOT_STYLES = {
  approved: "bg-green-500",
  awaiting_review: "bg-yellow-500",
  action_required: "bg-blue-500",
  processing: "bg-accent-500 animate-pulse",
  possibly_stuck: "bg-red-500",
  rejected: "bg-red-500",
  not_started: "bg-gray-300",
};

// Every stage is always clickable regardless of its derived status -- this is the direct fix
// for the prior design's "artifacts become unreachable once a stage is approved" gap. Status is
// only ever used here for the dot color, never to gate navigation.
export default function PipelineNav({ stageStatuses, selectedStage, onSelectStage }) {
  return (
    <nav className="flex flex-col gap-1 bg-white rounded-lg shadow-sm border border-gray-200 p-2 w-56 flex-shrink-0">
      <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wide px-2 pt-1 pb-2">Pipeline</h2>
      {DISPLAY_STAGES.map((stage) => {
        const isPlaceholder = PLACEHOLDER_STAGES.includes(stage);
        const status = stageStatuses[stage];
        const isSelected = stage === selectedStage;

        return (
          <button
            key={stage}
            type="button"
            disabled={isPlaceholder}
            onClick={() => onSelectStage(stage)}
            className={clsx(
              "text-left px-3 py-2 rounded-md transition-colors",
              isPlaceholder && "opacity-50 cursor-not-allowed",
              !isPlaceholder && isSelected && "bg-accent-50 border border-accent-200",
              !isPlaceholder && !isSelected && "hover:bg-gray-50 border border-transparent"
            )}
          >
            <div className="flex items-center gap-2">
              <span
                className={clsx("w-2 h-2 rounded-full flex-shrink-0", isPlaceholder ? "bg-gray-200" : DOT_STYLES[status] || "bg-gray-300")}
              />
              <span className={clsx("text-sm font-semibold", isSelected ? "text-accent-900" : "text-gray-800")}>
                {STAGE_LABELS[stage]}
              </span>
            </div>
            <p className="text-xs text-gray-400 pl-4">
              {isPlaceholder ? "Not yet implemented" : STAGE_ROLE_LABELS[stage]}
            </p>
          </button>
        );
      })}
    </nav>
  );
}
