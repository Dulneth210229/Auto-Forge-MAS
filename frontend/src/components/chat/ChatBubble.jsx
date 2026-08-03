import { STAGE_LABELS } from "../../lib/pipelineStages";
import { ARTIFACT_TYPE_LABELS } from "../../lib/artifactTypeMeta";
import { PencilIcon } from "../pipeline/RequirementConversationParts";

const STATUS_LABELS = {
  approved: "Approved",
  rejected: "Rejected",
  revision_requested: "Revision requested",
};

// Ask-bubble labels by stage_event event_type -- a plain map instead of a ternary so a new
// event_type never silently falls through to the wrong label.
const ASK_EVENT_LABELS = {
  run: "Started",
  revise: "Revision requested",
  clarify_start: "Conversation started",
  clarify: "Answered questions",
  confirm: "Confirmed SRS",
};

// Extracted from StageInteractionPanel's old TimelineItem, generalized with a small stage tag on
// each bubble since this feed now spans every agent at once, not one stage at a time.
//
// `onEdit`, when provided, adds a hover-reveal "Edit" affordance to "ask" bubbles -- unlike the
// Requirement Agent's pre-SRS conversation (which has real cumulative state worth rewinding, so
// editing there discards and regenerates in place), a run/revise comment here has no downstream
// state to unwind: the artifact it already produced is immutable history. So "edit and resubmit"
// is simpler and equally honest: clicking Edit loads that message's text back into the composer
// for the human to tweak and send again as a new message, rather than pretending to rewrite an
// already-produced artifact's history.
export default function ChatBubble({ item, allArtifacts, onViewArtifact, onEdit }) {
  const stageTag = STAGE_LABELS[item.stage] || item.stage;

  if (item.kind === "ask") {
    return (
      <div className="flex justify-end group">
        <div className="max-w-[85%] flex flex-col items-end gap-1">
          <div className="bg-accent-600 dark:bg-accent-500 text-white rounded-lg rounded-tr-sm px-3 py-2 text-sm">
            <p className="text-xs text-accent-200 dark:text-accent-100/80 mb-0.5">
              {ASK_EVENT_LABELS[item.eventType] || "Revision requested"} &middot; {stageTag}
            </p>
            <p className="whitespace-pre-wrap">{item.comment || <span className="italic text-accent-200 dark:text-accent-100/80">(no comment provided)</span>}</p>
          </div>
          {onEdit && item.comment && (
            <button
              type="button"
              onClick={() => onEdit(item.comment)}
              title="Edit and resend this message"
              className="opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity text-xs text-gray-400 dark:text-gray-500 hover:text-accent-600 dark:hover:text-accent-400 flex items-center gap-1 px-1"
            >
              <PencilIcon />
              Edit
            </button>
          )}
        </div>
      </div>
    );
  }

  if (item.kind === "response") {
    const label = item.types.map((t) => ARTIFACT_TYPE_LABELS[t] || t).join(", ");
    const representative = allArtifacts.find(
      (a) => a.version === item.version && item.types.includes(a.artifact_type)
    );

    return (
      <div className="flex justify-start">
        <div className="max-w-[85%] bg-gray-100 dark:bg-white/10 text-gray-800 dark:text-gray-200 rounded-lg rounded-tl-sm px-3 py-2 text-sm">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">{stageTag} Agent</p>
          <p>
            Produced {label} (v{item.version})
            {representative && (
              <>
                {" -- "}
                <button
                  onClick={() => onViewArtifact(representative)}
                  className="text-accent-600 dark:text-accent-400 hover:text-accent-800 dark:hover:text-accent-300 font-semibold"
                >
                  View
                </button>
              </>
            )}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-center">
      <p className="text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-gray-700 rounded-full px-3 py-1">
        {stageTag}: {STATUS_LABELS[item.status] || item.status}
        {item.comment ? ` -- "${item.comment}"` : ""}
      </p>
    </div>
  );
}
