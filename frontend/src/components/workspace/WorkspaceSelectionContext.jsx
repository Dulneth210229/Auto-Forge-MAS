import { createContext, useContext, useMemo, useState } from "react";

const WorkspaceSelectionContext = createContext(null);

// The left/middle/right panels are siblings, not parent/child -- picking a feature in the left
// panel must simultaneously retarget the middle chat (which agent's conversation is shown) and
// the right panel (which agent's output is shown), and picking an agent in the middle panel must
// retarget the right panel too. A small shared context is the lightest mechanism that lets three
// siblings agree on "what are we looking at right now" without prop-drilling through the page
// component on every change -- no new state library needed, matching this app's existing total
// absence of one.
export function WorkspaceSelectionProvider({ featureId, onSelectFeature, children }) {
  const [selectedAgent, setSelectedAgent] = useState("requirement");
  const [selectedModel, setSelectedModel] = useState(null);
  const [activeOutputTab, setActiveOutputTab] = useState("result");
  const [viewingArtifact, setViewingArtifact] = useState(null);

  const value = useMemo(
    () => ({
      selectedFeatureId: featureId,
      selectFeature: (id) => {
        onSelectFeature(id);
        setSelectedAgent("requirement");
        setActiveOutputTab("result");
      },
      selectedAgent,
      selectAgent: (stage) => {
        setSelectedAgent(stage);
        setActiveOutputTab("result");
      },
      selectedModel,
      setSelectedModel,
      activeOutputTab,
      setActiveOutputTab,
      viewingArtifact,
      viewArtifact: setViewingArtifact,
    }),
    [featureId, onSelectFeature, selectedAgent, selectedModel, activeOutputTab, viewingArtifact]
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
