import { useState } from "react";
import StatusBadge from "../common/StatusBadge";
import ErrorBanner from "../common/ErrorBanner";
import { ARTIFACT_TYPE_LABELS } from "../../lib/artifactTypeMeta";
import { useApprovalMutation } from "../../hooks/useApprovalMutation";

// Per-artifact approve/reject/request-revision, independent of the stage's own gating
// ApprovalPanel -- needed because a stage's gating artifact (e.g. UI/UX's ui_metadata) approving
// does NOT cascade to sibling artifacts (e.g. individual ui_component_code rows), and each of
// those has no other approval path once the stage itself moves on. Pass featureId only for rows
// that need this (the gating artifact itself already gets the bigger ApprovalPanel below it, so
// callers should omit featureId there to avoid a redundant/confusing second set of buttons).
export default function ArtifactRow({ artifact, onView, reviseMutation, featureId }) {
  const [showRevise, setShowRevise] = useState(false);
  const [revisionComment, setRevisionComment] = useState("");
  const approval = useApprovalMutation(featureId);

  async function submitRevision(event) {
    event.preventDefault();
    await reviseMutation.mutateAsync({ revision_comment: revisionComment.trim(), revised_by: "human_user" });
    setShowRevise(false);
    setRevisionComment("");
  }

  const showInlineApproval = Boolean(featureId) && artifact.approval_status === "pending";

  return (
    <div className="bg-white border border-gray-200 rounded p-3">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-sm font-medium">{ARTIFACT_TYPE_LABELS[artifact.artifact_type] || artifact.artifact_type}</span>
          <span className="text-xs text-gray-400 ml-2">v{artifact.version}</span>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={artifact.approval_status} />
          <button onClick={() => onView(artifact)} className="text-accent-600 hover:text-accent-800 text-sm font-semibold">
            View
          </button>
          {reviseMutation && (
            <button
              onClick={() => setShowRevise((v) => !v)}
              className="text-gray-500 hover:text-gray-700 text-sm font-semibold"
            >
              Revise
            </button>
          )}
        </div>
      </div>

      {showInlineApproval && (
        <div className="mt-2 pt-2 border-t border-gray-100">
          <ErrorBanner error={approval.error} fallback="Failed to submit approval decision." />
          <div className="flex gap-2">
            <button
              onClick={() => approval.mutate({ artifactId: artifact.artifact_id, status: "approved" })}
              disabled={approval.isPending}
              className="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white text-xs font-semibold py-1 px-2 rounded"
            >
              Approve
            </button>
            <button
              onClick={() => approval.mutate({ artifactId: artifact.artifact_id, status: "revision_requested" })}
              disabled={approval.isPending}
              className="bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white text-xs font-semibold py-1 px-2 rounded"
            >
              Request Revision
            </button>
            <button
              onClick={() => approval.mutate({ artifactId: artifact.artifact_id, status: "rejected" })}
              disabled={approval.isPending}
              className="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-xs font-semibold py-1 px-2 rounded"
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {showRevise && (
        <form onSubmit={submitRevision} className="mt-3 flex flex-col gap-2">
          <ErrorBanner error={reviseMutation.error} fallback="Revision failed." />
          <textarea
            required
            value={revisionComment}
            onChange={(e) => setRevisionComment(e.target.value)}
            placeholder="What should change?"
            rows={2}
            className="w-full p-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:border-accent-500"
          />
          <button
            type="submit"
            disabled={reviseMutation.isPending}
            className="self-start bg-gray-700 hover:bg-gray-800 disabled:opacity-50 text-white text-sm font-semibold py-1.5 px-3 rounded"
          >
            {reviseMutation.isPending ? "Submitting..." : "Submit Revision"}
          </button>
        </form>
      )}
    </div>
  );
}
