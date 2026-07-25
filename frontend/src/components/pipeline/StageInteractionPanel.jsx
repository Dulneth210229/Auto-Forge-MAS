import { useMemo, useState } from "react";
import { STATUS } from "../../lib/deriveStageStatus";
import { MANUAL_RUN_STAGES, REVISABLE_STAGES, STAGE_LABELS } from "../../lib/pipelineStages";
import { ARTIFACT_TYPE_LABELS } from "../../lib/artifactTypeMeta";
import { SUGGESTION_CHIPS } from "../../lib/suggestionChips";
import {
  useReviseArchitecture,
  useReviseCoder,
  useReviseDomain,
  useReviseRequirement,
} from "../../hooks/useAgentMutations";
import RequirementRunForm from "./RequirementRunForm";
import ArchitectureRunForm from "./ArchitectureRunForm";
import LoadingSpinner from "../common/LoadingSpinner";
import ErrorBanner from "../common/ErrorBanner";

const REVISE_HOOKS = {
  requirement: useReviseRequirement,
  domain: useReviseDomain,
  architecture: useReviseArchitecture,
  coder: useReviseCoder,
};

const STATUS_LABELS = {
  approved: "Approved",
  rejected: "Rejected",
  revision_requested: "Revision requested",
};

// Merges three independent, real data sources into one chronological timeline -- each run/revise
// request (the "ask"), each artifact version produced (the "response"), and each approval
// decision (the "verdict"). Not a live back-and-forth chat: a real activity log, presented
// conversationally. See stage_event_schema.py / approval_schema.py for why these can't be
// reconstructed from artifacts alone (human_comment/reviewer_comment live on separate records).
function buildTimeline(stage, stageArtifacts, approvals, events) {
  const items = [];

  for (const event of events) {
    items.push({
      kind: "ask",
      timestamp: new Date(event.requested_at).getTime(),
      comment: event.human_comment,
      eventType: event.event_type,
    });
  }

  const byVersion = new Map();
  for (const artifact of stageArtifacts) {
    const key = artifact.version;
    if (!byVersion.has(key)) {
      byVersion.set(key, { version: key, timestamp: new Date(artifact.created_at).getTime(), types: [] });
    }
    byVersion.get(key).types.push(artifact.artifact_type);
  }
  for (const group of byVersion.values()) {
    items.push({ kind: "response", timestamp: group.timestamp, version: group.version, types: [...new Set(group.types)] });
  }

  const stageArtifactIds = new Set(stageArtifacts.map((a) => a.artifact_id));
  for (const approval of approvals) {
    if (!stageArtifactIds.has(approval.artifact_id)) continue;
    items.push({
      kind: "decision",
      timestamp: new Date(approval.approved_at).getTime(),
      status: approval.status,
      comment: approval.reviewer_comment,
    });
  }

  items.sort((a, b) => a.timestamp - b.timestamp);
  return items;
}

function TimelineItem({ item, onViewArtifact, stageArtifacts }) {
  if (item.kind === "ask") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-accent-600 text-white rounded-lg rounded-tr-sm px-3 py-2 text-sm">
          <p className="text-xs text-accent-200 mb-0.5">{item.eventType === "run" ? "Started" : "Revision requested"}</p>
          <p>{item.comment || <span className="italic text-accent-200">(no comment provided)</span>}</p>
        </div>
      </div>
    );
  }

  if (item.kind === "response") {
    const label = item.types.map((t) => ARTIFACT_TYPE_LABELS[t] || t).join(", ");
    const representative = stageArtifacts.find((a) => a.version === item.version && item.types.includes(a.artifact_type));

    return (
      <div className="flex justify-start">
        <div className="max-w-[80%] bg-gray-100 text-gray-800 rounded-lg rounded-tl-sm px-3 py-2 text-sm">
          <p className="text-xs text-gray-500 mb-0.5">Agent</p>
          <p>
            Produced {label} (v{item.version})
            {representative && (
              <>
                {" -- "}
                <button onClick={() => onViewArtifact(representative)} className="text-accent-600 hover:text-accent-800 font-semibold">
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
      <p className="text-xs text-gray-500 bg-gray-50 border border-gray-200 rounded-full px-3 py-1">
        {STATUS_LABELS[item.status] || item.status}
        {item.comment ? `: "${item.comment}"` : ""}
      </p>
    </div>
  );
}

export default function StageInteractionPanel({
  stage,
  status,
  featureId,
  feature,
  stageArtifacts,
  approvals,
  events,
  eventsLoading,
  onViewArtifact,
}) {
  const [comment, setComment] = useState("");

  // Hooks must run unconditionally.
  const reviseRequirement = useReviseRequirement(featureId);
  const reviseDomain = useReviseDomain(featureId);
  const reviseArchitecture = useReviseArchitecture(featureId);
  const reviseCoder = useReviseCoder(featureId);
  const reviseMutationsByStage = {
    requirement: reviseRequirement,
    domain: reviseDomain,
    architecture: reviseArchitecture,
    coder: reviseCoder,
  };
  const reviseMutation = REVISE_HOOKS[stage] ? reviseMutationsByStage[stage] : null;

  const timeline = useMemo(
    () => buildTimeline(stage, stageArtifacts, approvals, events),
    [stage, stageArtifacts, approvals, events]
  );

  async function submitRevision(event) {
    event.preventDefault();
    if (!comment.trim() || !reviseMutation) return;
    await reviseMutation.mutateAsync({ revision_comment: comment.trim(), revised_by: "human_user" });
    setComment("");
  }

  const isManual = MANUAL_RUN_STAGES.includes(stage);

  return (
    <div className="flex flex-col gap-3">
      <div
        className={`text-xs rounded-md px-2.5 py-1.5 ${isManual ? "bg-blue-50 text-blue-700" : "bg-gray-50 text-gray-500"}`}
      >
        {isManual
          ? "Manual trigger -- you run this agent yourself, below."
          : `Runs automatically as soon as the previous stage is approved.`}
      </div>

      {status === STATUS.ACTION_REQUIRED ? (
        stage === "requirement" ? (
          <RequirementRunForm featureId={featureId} feature={feature} />
        ) : stage === "architecture" ? (
          <ArchitectureRunForm featureId={featureId} />
        ) : null
      ) : (
        <>
          <div className="flex flex-col gap-3">
            {eventsLoading ? (
              <LoadingSpinner label="Loading activity..." />
            ) : timeline.length === 0 ? (
              <p className="text-sm text-gray-400 italic">No activity yet for this stage.</p>
            ) : (
              timeline.map((item, i) => (
                <TimelineItem key={i} item={item} onViewArtifact={onViewArtifact} stageArtifacts={stageArtifacts} />
              ))
            )}

            {status === STATUS.PROCESSING && <LoadingSpinner label={`${STAGE_LABELS[stage]} Agent is working...`} />}

            {status === STATUS.POSSIBLY_STUCK && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-sm font-semibold text-red-800">Taking longer than expected.</p>
                <p className="text-xs text-red-700 mt-1">
                  Still polling automatically -- if the underlying issue resolves, this page will pick up
                  the result without a refresh.
                </p>
              </div>
            )}
          </div>

          {REVISABLE_STAGES.includes(stage) && reviseMutation && (
            <form onSubmit={submitRevision} className="border-t border-gray-200 pt-3 mt-2">
              <ErrorBanner error={reviseMutation.error} fallback="Revision request failed." />

              {SUGGESTION_CHIPS[stage] && (
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {SUGGESTION_CHIPS[stage].map((chip) => (
                    <button
                      key={chip}
                      type="button"
                      onClick={() => setComment(chip)}
                      className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full px-2.5 py-1"
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              )}

              <div className="flex gap-2">
                <input
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder={`Ask ${STAGE_LABELS[stage]} Agent for a change...`}
                  className="flex-1 p-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:border-accent-500"
                />
                <button
                  type="submit"
                  disabled={reviseMutation.isPending || !comment.trim()}
                  className="bg-accent-600 hover:bg-accent-700 disabled:opacity-50 text-white text-sm font-semibold px-4 rounded-md"
                >
                  {reviseMutation.isPending ? "Sending..." : "Send"}
                </button>
              </div>
            </form>
          )}
        </>
      )}
    </div>
  );
}
