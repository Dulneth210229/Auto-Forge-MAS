import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useFeature } from "../hooks/useFeatures";
import { useGraphStatus, useFeatureApprovals, useFeatureEvents, useStartPipeline } from "../hooks/usePipeline";
import { useFeatureArtifacts } from "../hooks/useArtifacts";
import { deriveStageStatus, STATUS } from "../lib/deriveStageStatus";
import { GATED_STAGES, STAGE_LABELS } from "../lib/pipelineStages";
import { ARTIFACT_TYPE_STAGE } from "../lib/artifactTypeMeta";
import PageHeader from "../components/layout/PageHeader";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorBanner from "../components/common/ErrorBanner";
import StatusBadge from "../components/common/StatusBadge";
import PipelineNav from "../components/pipeline/PipelineNav";
import StageSidebar from "../components/pipeline/StageSidebar";
import StageOutputPanel from "../components/pipeline/StageOutputPanel";
import ArtifactViewerModal from "../components/artifacts/ArtifactViewerModal";

function isProcessingNode(graphStatus, stage) {
  return Boolean(graphStatus?.next?.includes(`${stage}_node`));
}

export default function FeatureDetailPage() {
  const { featureId } = useParams();
  const { data: feature, isLoading: featureLoading, error: featureError } = useFeature(featureId);
  const { data: graphStatus, isLoading: graphLoading } = useGraphStatus(featureId);

  const anyProcessing = ["domain", "uiux", "coder"].some((stage) => isProcessingNode(graphStatus, stage));
  const { data: artifacts, isLoading: artifactsLoading, error: artifactsError } = useFeatureArtifacts(featureId, {
    isProcessing: anyProcessing,
  });
  const { data: approvals } = useFeatureApprovals(featureId);
  const { data: events, isLoading: eventsLoading } = useFeatureEvents(featureId);

  const startPipeline = useStartPipeline(featureId);
  const [viewingArtifact, setViewingArtifact] = useState(null);
  const [selectedStage, setSelectedStage] = useState(null);

  // Tracks, per auto-run stage, the timestamp it was first observed as "processing" -- reset
  // whenever the graph moves off that stage. Used to distinguish a normal wait from
  // "possibly stuck" without a dedicated backend signal for either.
  const processingSinceRef = useRef({});

  useEffect(() => {
    if (!graphStatus) return;

    for (const stage of ["domain", "uiux", "coder"]) {
      if (isProcessingNode(graphStatus, stage)) {
        if (!processingSinceRef.current[stage]) {
          processingSinceRef.current[stage] = Date.now();
        }
      } else {
        processingSinceRef.current[stage] = null;
      }
    }
  }, [graphStatus]);

  const allArtifacts = artifacts || [];
  const allApprovals = approvals || [];
  const allEvents = events || [];

  const stageStatuses = {};
  for (const stage of GATED_STAGES) {
    stageStatuses[stage] = deriveStageStatus({
      stage,
      graphStatus,
      artifacts: allArtifacts,
      processingSince: processingSinceRef.current[stage],
      now: Date.now(),
    });
  }
  // Security/QA auto-approve with no gate and no artifacts worth reviewing yet -- always shown
  // as "approved" once the graph has passed them, otherwise not started.
  for (const stage of ["security", "qa"]) {
    const nextNodes = graphStatus?.next || [];
    const graphReachedEnd = graphStatus && nextNodes.length === 0 && stageStatuses.coder === STATUS.APPROVED;
    stageStatuses[stage] = graphReachedEnd ? STATUS.APPROVED : STATUS.NOT_STARTED;
  }

  // Ground truth for "where is the pipeline right now" is the graph's own position: `next`
  // names either "{stage}_node" (auto-run stages actively executing) or "approve_{stage}"
  // (paused at a human gate) -- either way, that stage is definitively current. Only fall back
  // to "first non-approved stage in sequence" when the graph gives no signal (never started, or
  // fully finished) -- confirmed live that a purely sequential scan gets stuck forever on a stage
  // whose own derived status can be stale for reasons unrelated to real progress (e.g. a feature
  // created before Domain Agent became a real gate has no enhanced_srs artifact and never will).
  const nextNodes = graphStatus?.next || [];
  const graphIndicatedStage = GATED_STAGES.find((stage) =>
    nextNodes.includes(`${stage}_node`) || nextNodes.includes(`approve_${stage}`)
  );
  const currentStage = graphIndicatedStage || GATED_STAGES.find((stage) => stageStatuses[stage] !== STATUS.APPROVED);

  // Used only to pick which stage is selected by default on first load -- every stage stays
  // independently selectable afterward (see PipelineNav), not gated by this at all.
  useEffect(() => {
    if (selectedStage === null && currentStage) {
      setSelectedStage(currentStage);
    }
  }, [selectedStage, currentStage]);

  const stage = selectedStage || currentStage || "requirement";

  // A graph run that has ever been started (via POST .../start) leaves its input/output keys in
  // state.values permanently, even after `next` empties out on completion -- `next.length` alone
  // can't distinguish "never started" from "started and now finished." Artifact existence is NOT
  // a valid signal here either: Requirement/Architecture generate real artifacts via their manual
  // `/run` endpoints without the graph ever being started at all (see the hybrid trigger model),
  // so using it caused the Start Pipeline button to vanish permanently the moment a human ran
  // Requirement -- before the graph had ever actually started -- leaving no way to make Domain
  // auto-trigger after approval.
  const pipelineStarted = Boolean(graphStatus && Object.keys(graphStatus.values || {}).length > 0);

  const stageArtifacts = allArtifacts.filter((a) => ARTIFACT_TYPE_STAGE[a.artifact_type] === stage);
  const stageApprovals = allApprovals.filter((a) => a.agent_name === `${stage}_agent`);
  const stageEvents = allEvents.filter((e) => e.agent_name === `${stage}_agent`);

  if (featureLoading) {
    return <LoadingSpinner label="Loading feature..." />;
  }

  return (
    <div className="flex flex-col h-full">
      <ErrorBanner error={featureError} fallback="Failed to load feature." />

      {feature && (
        <Link
          to={`/projects/${feature.project_id}`}
          className="text-sm text-gray-500 hover:text-accent-600 mb-2 inline-flex items-center gap-1 flex-shrink-0 w-fit"
        >
          &larr; Back to project
        </Link>
      )}

      {feature && <PageHeader title={feature.feature_name} subtitle={feature.feature_description} />}

      {!pipelineStarted && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4 flex-shrink-0">
          <button
            onClick={() => startPipeline.mutate()}
            disabled={startPipeline.isPending}
            className="bg-gray-900 hover:bg-gray-800 disabled:opacity-50 text-white font-semibold py-2 px-4 rounded text-sm"
          >
            {startPipeline.isPending ? "Starting..." : "Start Pipeline (fully automatic, agent by agent)"}
          </button>
          <p className="text-xs text-gray-500 mt-2">
            Or trigger Requirement/Architecture yourself below whenever they're up -- either way works.
          </p>
          <ErrorBanner error={startPipeline.error} fallback="Failed to start pipeline." />
        </div>
      )}

      <ErrorBanner error={artifactsError} fallback="Failed to load artifacts." />

      {graphLoading || artifactsLoading ? (
        <LoadingSpinner label="Loading pipeline..." />
      ) : (
        <div className="flex gap-4 items-stretch flex-1 min-h-0">
          <div className="h-full overflow-y-auto flex-shrink-0">
            <PipelineNav stageStatuses={stageStatuses} selectedStage={stage} onSelectStage={setSelectedStage} />
          </div>

          <div className="flex-1 min-w-0 h-full bg-white rounded-lg shadow-sm border border-gray-200 p-4 flex flex-col">
            <div className="flex items-center gap-2 mb-3 border-b border-gray-100 pb-3 flex-shrink-0">
              <h2 className="text-base font-bold text-gray-900">{STAGE_LABELS[stage]} Output</h2>
              <StatusBadge status={stageStatuses[stage]} />
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto">
              <StageOutputPanel stage={stage} featureId={featureId} allArtifacts={allArtifacts} />
            </div>
          </div>

          <StageSidebar
            stage={stage}
            status={stageStatuses[stage]}
            featureId={featureId}
            feature={feature}
            allArtifacts={allArtifacts}
            stageArtifacts={stageArtifacts}
            approvals={stageApprovals}
            events={stageEvents}
            eventsLoading={eventsLoading}
            onViewArtifact={setViewingArtifact}
          />
        </div>
      )}

      <ArtifactViewerModal artifact={viewingArtifact} onClose={() => setViewingArtifact(null)} />
    </div>
  );
}
