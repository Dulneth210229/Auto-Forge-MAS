import { MANUAL_RUN_STAGES, STUCK_TIMEOUT_MS } from "./pipelineStages";
import { STAGE_GATING_ARTIFACT } from "./artifactTypeMeta";

// Best-effort, client-side reconstruction of "what stage is this feature at" -- the backend
// has no dedicated status API beyond graph-status's {next, values} shape, and feature_status/
// current_agent on the Feature resource are documented as unreliable past the Architecture
// stage. This heuristic mirrors exactly what the graph itself does (GATED_STAGES + approval
// gates), just reconstructed from artifact state + graph-status rather than true graph
// internals -- correct scope for a system with no real status endpoint, not a permanent gap.
export const STATUS = {
  NOT_STARTED: "not_started",
  ACTION_REQUIRED: "action_required",
  AWAITING_REVIEW: "awaiting_review",
  PROCESSING: "processing",
  POSSIBLY_STUCK: "possibly_stuck",
  APPROVED: "approved",
  REJECTED: "rejected",
};

// Every agent saves a JSON+Markdown pair sharing one version -- exactly one format is what the
// pipeline actually keys approval/gating off of for each stage (see STAGE_GATING_ARTIFACT).
// Without a format filter, an approved-JSON/still-pending-Markdown pair at the same version is
// ambiguous to pick between -- this caused a real bug where the pending twin could win
// depending on array order, showing a stage as "awaiting review" when it was really approved.
export function latestArtifactOfType(artifacts, artifactType, artifactFormat = null) {
  const matches = artifacts.filter(
    (artifact) =>
      artifact.artifact_type === artifactType && (artifactFormat == null || artifact.artifact_format === artifactFormat)
  );

  if (matches.length === 0) {
    return null;
  }

  return matches.reduce((latest, artifact) => (artifact.version > latest.version ? artifact : latest), matches[0]);
}

/**
 * @param {object} params
 * @param {string} params.stage - one of GATED_STAGES
 * @param {{next: string[]}|null|undefined} params.graphStatus
 * @param {Array} params.artifacts - all artifacts for the feature (any stage)
 * @param {number|null} [params.processingSince] - ms timestamp when this stage was first
 *   observed as "processing" (tracked by the caller, e.g. a useRef in FeatureDetailPage)
 * @param {number} [params.now]
 */
export function deriveStageStatus({ stage, graphStatus, artifacts, processingSince = null, now = Date.now() }) {
  const gating = STAGE_GATING_ARTIFACT[stage];
  const latest = gating ? latestArtifactOfType(artifacts, gating.type, gating.format) : null;
  const nextNodes = graphStatus?.next || [];
  const isGraphProcessingThisStage = nextNodes.includes(`${stage}_node`);

  if (!latest) {
    if (MANUAL_RUN_STAGES.includes(stage)) {
      return STATUS.ACTION_REQUIRED;
    }

    if (isGraphProcessingThisStage) {
      const timeout = STUCK_TIMEOUT_MS[stage] ?? Infinity;

      if (processingSince != null && now - processingSince > timeout) {
        return STATUS.POSSIBLY_STUCK;
      }

      return STATUS.PROCESSING;
    }

    return STATUS.NOT_STARTED;
  }

  if (latest.approval_status === "approved") {
    return STATUS.APPROVED;
  }

  if (latest.approval_status === "rejected") {
    return STATUS.REJECTED;
  }

  // "pending" or "revision_requested"
  return STATUS.AWAITING_REVIEW;
}

export function getLatestGatingArtifact(stage, artifacts) {
  const gating = STAGE_GATING_ARTIFACT[stage];
  return gating ? latestArtifactOfType(artifacts, gating.type, gating.format) : null;
}

// Every version of a stage's gating artifact, newest first -- powers the Output tab's version
// picker (distinct from getLatestGatingArtifact, which only ever returns the newest one).
export function listGatingArtifactVersions(stage, artifacts) {
  const gating = STAGE_GATING_ARTIFACT[stage];
  if (!gating) return [];

  return artifacts
    .filter((a) => a.artifact_type === gating.type && a.artifact_format === gating.format)
    .sort((a, b) => b.version - a.version);
}
