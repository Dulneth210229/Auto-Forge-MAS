import { useState } from "react";
import { useApprovalMutation } from "../../hooks/useApprovalMutation";
import ErrorBanner from "../common/ErrorBanner";

export default function ApprovalPanel({ featureId, artifact, warning }) {
  const [comment, setComment] = useState("");
  const approval = useApprovalMutation(featureId);

  function submit(status) {
    approval.mutate({ artifactId: artifact.artifact_id, status, reviewer_comment: comment.trim() || null });
  }

  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mt-3">
      <p className="text-sm font-semibold text-yellow-900 mb-2">
        Awaiting your review (v{artifact.version})
      </p>

      {warning && <div className="bg-white border border-yellow-300 rounded p-3 text-xs text-gray-700 mb-3">{warning}</div>}

      <ErrorBanner error={approval.error} fallback="Failed to submit approval decision." />

      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Optional comment..."
        rows={2}
        className="w-full p-2 text-sm border border-gray-300 rounded-md mb-2 focus:outline-none focus:border-accent-500"
      />

      <div className="flex gap-2">
        <button
          onClick={() => submit("approved")}
          disabled={approval.isPending}
          className="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white text-sm font-semibold py-1.5 px-3 rounded"
        >
          Approve
        </button>
        <button
          onClick={() => submit("revision_requested")}
          disabled={approval.isPending}
          className="bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white text-sm font-semibold py-1.5 px-3 rounded"
        >
          Request Revision
        </button>
        <button
          onClick={() => submit("rejected")}
          disabled={approval.isPending}
          className="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-sm font-semibold py-1.5 px-3 rounded"
        >
          Reject
        </button>
      </div>
    </div>
  );
}
