import { createContext, useContext, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { GATED_STAGES } from "../../lib/pipelineStages";

const WorkspaceSelectionContext = createContext(null);

// The left/middle/right panels are siblings, not parent/child -- picking a feature in the left
// panel must simultaneously retarget the middle chat (which agent's conversation is shown) and
// the right panel (which agent's output is shown), and picking an agent in the middle panel must
// retarget the right panel too. A small shared context is the lightest mechanism that lets three
// siblings agree on "what are we looking at right now" without prop-drilling through the page
// component on every change -- no new state library needed, matching this app's existing total
// absence of one.
//
// selectedAgent is seeded from (and kept in sync with) the `agent` URL query param -- direct user
// report: refreshing the browser always reset the visible chat back to Requirement Agent, which
// read as "the other agent's chat history disappeared" even though every agent's chat data was
// always persisted server-side (stage_events/artifacts/approvals, or the requirement_conversations
// record) -- only the CLIENT-side "which agent's chat is currently on screen" state was ever lost.
// A plain useState default has no way to survive a full page reload; the URL does, and it's
// already the mechanism this page uses for featureId (see ProjectWorkspacePage), so a fresh load
// of the exact same URL now reopens the exact same agent's chat instead of silently jumping back
// to Requirement.
export function WorkspaceSelectionProvider({ featureId, onSelectFeature, children }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlAgent = searchParams.get("agent");
  const [selectedAgent, setSelectedAgentState] = useState(
    GATED_STAGES.includes(urlAgent) ? urlAgent : "requirement"
  );
  const [selectedModel, setSelectedModel] = useState(null);
  const [activeOutputTab, setActiveOutputTab] = useState("result");
  const [viewingArtifact, setViewingArtifact] = useState(null);
  // Cursor-style fullscreen toggle for the live preview iframe -- UI-only, no server round trip,
  // so it lives here alongside activeOutputTab/viewingArtifact rather than in preview-specific
  // state. Reset whenever the feature changes (selectFeature below), same as the other UI-only
  // fields, so switching features never leaves a stale fullscreen preview covering the new one.
  const [isPreviewExpanded, setIsPreviewExpanded] = useState(false);

  function setAgentQueryParam(stage) {
    setSearchParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        if (stage) {
          next.set("agent", stage);
        } else {
          next.delete("agent");
        }
        return next;
      },
      { replace: true }
    );
  }

  const value = useMemo(
    () => ({
      selectedFeatureId: featureId,
      selectFeature: (id) => {
        onSelectFeature(id);
        setSelectedAgentState("requirement");
        setActiveOutputTab("result");
        setAgentQueryParam(null);
        setIsPreviewExpanded(false);
      },
      selectedAgent,
      selectAgent: (stage) => {
        setSelectedAgentState(stage);
        setActiveOutputTab("result");
        setAgentQueryParam(stage);
      },
      selectedModel,
      setSelectedModel,
      activeOutputTab,
      setActiveOutputTab,
      viewingArtifact,
      viewArtifact: setViewingArtifact,
      isPreviewExpanded,
      togglePreviewExpanded: () => setIsPreviewExpanded((v) => !v),
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- setAgentQueryParam/onSelectFeature
    // are recreated every render (setSearchParams identity, prop from parent); including them
    // would invalidate this memo every render and defeats its purpose. featureId/selectedAgent/etc
    // are the only values that actually need to trigger a new value object.
    [featureId, selectedAgent, selectedModel, activeOutputTab, viewingArtifact, isPreviewExpanded]
  );

  return <WorkspaceSelectionContext.Provider value={value}>{children}</WorkspaceSelectionContext.Provider>;
}

export function useWorkspaceSelection() {
  const ctx = useContext(WorkspaceSelectionContext);
  if (!ctx) {
    throw new Error("useWorkspaceSelection must be used within a WorkspaceSelectionProvider");
  }
  return ctx;
}
