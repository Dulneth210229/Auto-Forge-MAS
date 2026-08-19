import clsx from "clsx";
import { useEffect } from "react";
import { useFeatureArtifacts } from "../../hooks/useArtifacts";
import { useFeature } from "../../hooks/useFeatures";
import { useWorkspaceSelection } from "../workspace/WorkspaceSelectionContext";
import { getEffectiveActiveArtifact } from "../../lib/activeArtifactSelection";
import { ARTIFACT_TYPE_LABELS } from "../../lib/artifactTypeMeta";
import { STAGE_LABELS } from "../../lib/pipelineStages";
import ResultTab from "./ResultTab";
import PreviewPanel from "./PreviewPanel";
import UiuxPreviewPanel from "./UiuxPreviewPanel";
import LoadingSpinner from "../common/LoadingSpinner";
import ErrorBanner from "../common/ErrorBanner";

const TABS = [
  { key: "result", label: "Result" },
  { key: "files", label: "Files" },
  { key: "preview", label: "Preview" },
];

// Only "files" stays disabled -- it's a separate, not-yet-built workspace file browser.
// "preview" is live (see PreviewPanel).
const DISABLED_TABS = new Set(["files"]);

// stage -> the real previous-stage artifact(s) it actually reads, for the "Using X vN for Y
// Agent" indicator -- generalized (direct user request, with a screenshot of the original
// Requirement->Domain-only version as the reference example) to every stage that has a real,
// approved-artifact input. Confirmed against each agent's own real run()/revise() code, not
// guessed:
// - domain reads the approved SRS.
// - architecture reads the approved Enhanced SRS when one exists, falling back to the plain SRS
//   only if it doesn't (srs_for_generation = enhanced_srs_json or srs_json, at every real call
//   site in architecture_agent/agent.py) -- resolved at render time below, never hardcoded to
//   just one.
// - uiux reads the approved Architecture Plan.
// - coder reads BOTH the Architecture Plan and the UI/UX Integration Manifest independently (at
//   every real call site in coder_agent/agent.py) -- the human-recognizable version to show for
//   the latter is ui_preview_screenshot's (its real gating/cascade-anchored type since item 64;
//   the manifest shares that exact version through the same approval cascade).
const PREVIOUS_STAGE_INPUTS_BY_STAGE = {
  domain: [{ artifactType: "srs" }],
  architecture: [{ artifactType: "enhanced_srs", fallbackArtifactType: "srs" }],
  uiux: [{ artifactType: "architecture_plan" }],
  coder: [
    { artifactType: "architecture_plan" },
    { artifactType: "ui_preview_screenshot", artifactFormat: "png", label: "UI/UX Output" },
  ],
};

// Security and QA scan the live generated workspace directly off disk (confirmed: neither
// security_agent.py's nor qa_agent.py's run() ever calls a "find latest approved artifact"
// lookup for their main input) -- there is no formal, approved-artifact version behind "what
// they used" the way every other stage has one. An honest, plain, non-versioned label instead of
// a pill, so this indicator never implies a version number that doesn't actually exist.
const NO_ARTIFACT_VERSION_LABEL_BY_STAGE = {
  security: "Scanning the latest generated code",
  qa: "Testing the latest generated code",
};

// The right panel -- deliberately the largest of the three (see ResizableWorkspace's default
// sizes). "Preview" is live: Cursor-style Start/Stop of the Coder Agent's generated Next.js app
// (PreviewPanel) for every stage EXCEPT uiux, which gets an instant, server-less HTML+Tailwind
// design preview instead (UiuxPreviewPanel) -- a UI/UX page has no server/build step of its own,
// so there's nothing to Start/Stop. "Files" stays disabled -- a workspace file browser hasn't
// been built yet.
export default function OutputPanel({ featureId }) {
  const { selectedAgent, activeOutputTab, setActiveOutputTab } = useWorkspaceSelection();
  const { data: artifacts, isLoading, error } = useFeatureArtifacts(featureId);
  const { data: feature } = useFeature(featureId);

  // Preview always shows the Coder Agent's live app preview regardless of which stage is
  // actually selected -- misleading (and, per direct user request for Security -- extended here
  // to QA for the same reason -- removed entirely rather than just disabled-with-tooltip like
  // "Files") while looking at a stage with no runnable preview of its own at all.
  const hasNoPreview = selectedAgent === "security" || selectedAgent === "qa";
  const visibleTabs = hasNoPreview ? TABS.filter((tab) => tab.key !== "preview") : TABS;

  // If the user was already on "preview" and then switches to Security/QA (whose tab bar no
  // longer has a button for it), fall back to "result" rather than leaving the panel stuck
  // showing a tab with no way to navigate back to it via the bar itself.
  useEffect(() => {
    if (hasNoPreview && activeOutputTab === "preview") {
      setActiveOutputTab("result");
    }
  }, [hasNoPreview, activeOutputTab, setActiveOutputTab]);

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800">
      <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 flex-shrink-0 px-2">
        <div className="flex items-center">
          {visibleTabs.map((tab) => {
            const disabled = DISABLED_TABS.has(tab.key);
            return (
              <button
                key={tab.key}
                disabled={disabled}
                onClick={() => setActiveOutputTab(tab.key)}
                title={disabled ? "Coming soon -- depends on upcoming Coder Agent changes" : undefined}
                className={clsx(
                  "text-sm font-semibold px-4 py-2.5 border-b-2 -mb-px",
                  disabled && "text-gray-300 dark:text-gray-700 cursor-not-allowed",
                  !disabled && activeOutputTab === tab.key && "text-accent-700 dark:text-accent-400 border-accent-600 dark:border-accent-500",
                  !disabled &&
                    activeOutputTab !== tab.key &&
                    "text-gray-500 dark:text-gray-400 border-transparent hover:text-gray-700 dark:hover:text-gray-200"
                )}
              >
                {tab.label}
                {disabled && <span className="ml-1.5 text-[10px] text-gray-300 dark:text-gray-700">(soon)</span>}
              </button>
            );
          })}
        </div>

        {(() => {
          const noArtifactLabel = NO_ARTIFACT_VERSION_LABEL_BY_STAGE[selectedAgent];
          if (noArtifactLabel) {
            return (
              <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-white/5 rounded-full px-3 py-1 whitespace-nowrap truncate">
                {noArtifactLabel}
              </span>
            );
          }

          const descriptors = PREVIOUS_STAGE_INPUTS_BY_STAGE[selectedAgent];
          if (!descriptors) return null;

          const agentLabel = `${STAGE_LABELS[selectedAgent] || selectedAgent} Agent`;

          const pills = descriptors
            .map((descriptor) => {
              const format = descriptor.artifactFormat || "json";
              let effective = getEffectiveActiveArtifact(
                artifacts || [], feature?.active_artifact_selection, descriptor.artifactType, format
              );
              let resolvedType = descriptor.artifactType;
              if (!effective && descriptor.fallbackArtifactType) {
                effective = getEffectiveActiveArtifact(
                  artifacts || [], feature?.active_artifact_selection, descriptor.fallbackArtifactType, format
                );
                resolvedType = descriptor.fallbackArtifactType;
              }
              if (!effective) return null;

              const label = descriptor.label || ARTIFACT_TYPE_LABELS[resolvedType] || resolvedType;
              return { key: resolvedType, label, version: effective.version };
            })
            .filter(Boolean);

          if (pills.length === 0) return null;

          return (
            <div className="flex items-center gap-1.5 flex-wrap justify-end">
              {pills.map((pill) => (
                <span
                  key={pill.key}
                  title={`${agentLabel} will use ${pill.label} v${pill.version} -- pin a different approved version from its row's radio button below.`}
                  className="text-xs font-semibold text-accent-700 dark:text-accent-400 bg-accent-50 dark:bg-accent-500/10 rounded-full px-3 py-1 whitespace-nowrap truncate"
                >
                  Using {pill.label} v{pill.version} for {agentLabel}
                </span>
              ))}
            </div>
          );
        })()}
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-4">
        {activeOutputTab === "preview" ? (
          selectedAgent === "uiux" ? (
            <UiuxPreviewPanel featureId={featureId} />
          ) : (
            <PreviewPanel featureId={featureId} />
          )
        ) : (
          <>
            <ErrorBanner error={error} fallback="Failed to load artifacts." />

            {isLoading ? (
              <LoadingSpinner variant="cube" label="Loading output..." />
            ) : (
              <ResultTab featureId={featureId} stage={selectedAgent} allArtifacts={artifacts || []} />
            )}
          </>
        )}
      </div>
    </div>
  );
}
