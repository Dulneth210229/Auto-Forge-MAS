const STYLES = {
  pending: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  revision_requested: "bg-orange-100 text-orange-800",
  not_started: "bg-gray-100 text-gray-500",
  action_required: "bg-blue-100 text-blue-800",
  awaiting_review: "bg-yellow-100 text-yellow-800",
  processing: "bg-accent-100 text-accent-800",
  possibly_stuck: "bg-red-100 text-red-800",
  // Feature-level status (feature_status, see app/core/enums.py's FeatureStatus) -- a distinct
  // namespace from the artifact/stage statuses above, each given its own clearly different color
  // so a feature card's status is visually distinguishable at a glance from a stage's own status.
  created: "bg-slate-100 text-slate-600",
  in_progress: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

const LABELS = {
  pending: "Pending",
  approved: "Approved",
  rejected: "Rejected",
  revision_requested: "Revision requested",
  not_started: "Not started",
  action_required: "Action required",
  awaiting_review: "Awaiting review",
  processing: "Processing...",
  possibly_stuck: "Possibly stuck",
  created: "Created",
  in_progress: "In Progress",
  completed: "Completed",
  failed: "Failed",
};

export default function StatusBadge({ status }) {
  const style = STYLES[status] || "bg-gray-100 text-gray-600";
  const label = LABELS[status] || status;

  return (
    <span className={`inline-block px-2 py-1 text-xs font-semibold rounded-full ${style}`}>{label}</span>
  );
}
