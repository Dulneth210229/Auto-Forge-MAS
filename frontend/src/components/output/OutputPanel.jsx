import clsx from "clsx";
import { useEffect } from "react";
import { useFeatureArtifacts } from "../../hooks/useArtifacts";
import { useFeature } from "../../hooks/useFeatures";
import { useWorkspaceSelection } from "../workspace/WorkspaceSelectionContext";
import { getEffectiveActiveArtifact } from "../../lib/activeArtifactSelection";
import { ARTIFACT_TYPE_LABELS, ARTIFACT_TYPE_STAGE } from "../../lib/artifactTypeMeta";
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

// artifact_type -> which downstream agent actually consumes it, for the "Using SRS vN for..."
// indicator. Requirement -> Domain and Domain -> Architecture are both wired (direct user
// request for the latter, mirroring the former) -- extend this map if another stage's handoff
// gets the same pin-a-version treatment.
const NEXT_AGENT_BY_ARTIFACT_TYPE = {
  srs: "Domain Agent",
  enhanced_srs: "Architecture Agent",
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
          // Only the pill for whichever stage is currently selected -- rendering every configured
          // entry in NEXT_AGENT_BY_ARTIFACT_TYPE simultaneously (the original behavior) would
          // overflow the tab bar now that a second entry (Enhanced SRS) exists alongside SRS.
          const artifactType = Object.keys(NEXT_AGENT_BY_ARTIFACT_TYPE).find(
            (type) => ARTIFACT_TYPE_STAGE[type] === selectedAgent
          );
          if (!artifactType) return null;

          const nextAgentLabel = NEXT_AGENT_BY_ARTIFACT_TYPE[artifactType];
          const effective = getEffectiveActiveArtifact(artifacts || [], feature?.active_artifact_selection, artifactType);
          if (!effective) return null;

          const label = ARTIFACT_TYPE_LABELS[artifactType] || artifactType;

          return (
            <span
              title={`${nextAgentLabel} will use ${label} v${effective.version} -- pin a different approved version from its row's radio button below.`}
              className="text-xs font-semibold text-accent-700 dark:text-accent-400 bg-accent-50 dark:bg-accent-500/10 rounded-full px-3 py-1 whitespace-nowrap truncate"
            >
              Using {label} v{effective.version} for {nextAgentLabel}
            </span>
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
