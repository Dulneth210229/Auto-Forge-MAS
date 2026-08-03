import { GATED_STAGES } from "./pipelineStages";
import { STATUS } from "./deriveStageStatus";

// Ground truth for "where is the pipeline right now" is the graph's own position: `next`
// names either "{stage}_node" (auto-run stages actively executing) or "approve_{stage}"
// (paused at a human gate) -- either way, that stage is definitively current. Only fall back
// to "first non-approved stage in sequence" when the graph gives no signal (never started, or
// fully finished) -- confirmed live that a purely sequential scan gets stuck forever on a stage
// whose own derived status can be stale for reasons unrelated to real progress (e.g. a feature
// created before Domain Agent became a real gate has no enhanced_srs artifact and never will).
//
// Extracted from the old FeatureDetailPage so both the left-panel feature list (each row's
// status pill) and the chat panel's default agent selection can share the exact same logic.
export function deriveCurrentStage(graphStatus, stageStatuses) {
  const nextNodes = graphStatus?.next || [];
  const graphIndicatedStage = GATED_STAGES.find((stage) =>
    nextNodes.includes(`${stage}_node`) || nextNodes.includes(`approve_${stage}`)
  );

  return graphIndicatedStage || GATED_STAGES.find((stage) => stageStatuses[stage] !== STATUS.APPROVED);
}
