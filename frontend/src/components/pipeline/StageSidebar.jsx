import { useState } from "react";
import clsx from "clsx";
import GovernancePanel from "./GovernancePanel";
import StageInteractionPanel from "./StageInteractionPanel";
import ArtifactList from "./ArtifactList";

const TABS = [
  { key: "governance", label: "Governance" },
  { key: "interaction", label: "Interaction" },
  { key: "artifacts", label: "Artifacts" },
];

// Everything that ISN'T the stage's main output lives here, behind its own tabs, so the center
// panel can be dedicated to output alone -- Governance (approve/reject, trace links, artifact
// sizes/downloads) is the default since approving is the most common side action; Interaction
// (the activity timeline + revise box) and Artifacts (the full versioned list) are one click
// away, not competing for primary billing.
export default function StageSidebar({
  stage,
  status,
  featureId,
  feature,
  allArtifacts,
  stageArtifacts,
  approvals,
  events,
  eventsLoading,
  onViewArtifact,
}) {
  const [tab, setTab] = useState("governance");

  return (
    <div className="w-96 flex-shrink-0 h-full flex flex-col bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="flex border-b border-gray-100 flex-shrink-0">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={clsx(
              "flex-1 text-sm font-semibold py-2.5",
              tab === t.key ? "text-accent-700 border-b-2 border-accent-600" : "text-gray-500 hover:bg-gray-50"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-3">
        {tab === "governance" && (
          <GovernancePanel stage={stage} featureId={featureId} allArtifacts={allArtifacts} stageArtifacts={stageArtifacts} />
        )}
        {tab === "interaction" && (
          <StageInteractionPanel
            stage={stage}
            status={status}
            featureId={featureId}
            feature={feature}
            stageArtifacts={stageArtifacts}
            approvals={approvals}
            events={events}
            eventsLoading={eventsLoading}
            onViewArtifact={onViewArtifact}
          />
        )}
        {tab === "artifacts" && (
          <ArtifactList artifacts={stageArtifacts} onView={onViewArtifact} gatingArtifactType={null} featureId={featureId} />
        )}
      </div>
    </div>
  );
}
