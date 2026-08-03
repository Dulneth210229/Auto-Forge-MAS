import { useNavigate, useParams } from "react-router-dom";
import { useFeatures } from "../hooks/useFeatures";
import {
  WorkspaceSelectionProvider,
  useWorkspaceSelection,
} from "../components/workspace/WorkspaceSelectionContext";
import ResizableWorkspace from "../components/workspace/ResizableWorkspace";
import FeatureListPanel from "../components/workspace/FeatureListPanel";
import EmptyChatPanel from "../components/workspace/EmptyChatPanel";
import EmptyOutputPanel from "../components/workspace/EmptyOutputPanel";
import { RequirementConversationFlowProvider } from "../components/workspace/RequirementConversationFlowContext";
import ChatPanel from "../components/chat/ChatPanel";
import OutputPanel from "../components/output/OutputPanel";
import ArtifactViewerModal from "../components/artifacts/ArtifactViewerModal";
import LoadingSpinner from "../components/common/LoadingSpinner";

function WorkspaceBody({ projectId }) {
  const { selectedFeatureId, viewingArtifact, viewArtifact } = useWorkspaceSelection();

  return (
    // Wraps both the chat and output panels (regardless of which agent is currently selected) so
    // the Requirement Agent's conversation/generation state is shared between them -- see
    // RequirementConversationFlowContext for why this can't just be two separate hook calls.
    // Cheap when irrelevant: the underlying query is a single disabled-when-no-feature GET.
    <RequirementConversationFlowProvider featureId={selectedFeatureId}>
      <div className="h-full">
        <ResizableWorkspace
          left={<FeatureListPanel projectId={projectId} />}
          middle={
            selectedFeatureId ? (
              <ChatPanel featureId={selectedFeatureId} />
            ) : (
              <EmptyChatPanel projectId={projectId} />
            )
          }
          right={selectedFeatureId ? <OutputPanel featureId={selectedFeatureId} /> : <EmptyOutputPanel />}
        />
        <ArtifactViewerModal artifact={viewingArtifact} onClose={() => viewArtifact(null)} />
      </div>
    </RequirementConversationFlowProvider>
  );
}

// Replaces the old ProjectDetailPage -> FeatureDetailPage drill-down with one Cursor-style
// workspace: pick a feature in the left panel, talk to its agents in the middle panel, see their
// output in the right panel -- all without a page navigation. featureId in the URL just seeds
// which feature is initially selected (and keeps the URL bookmarkable/shareable); switching
// features afterward updates the URL via `replace` without unmounting this page.
export default function ProjectWorkspacePage() {
  const { projectId, featureId } = useParams();
  const navigate = useNavigate();
  const { data: features, isLoading } = useFeatures(projectId);

  function handleSelectFeature(id) {
    navigate(`/projects/${projectId}/features/${id}`, { replace: true });
  }

  if (isLoading) {
    return <LoadingSpinner label="Loading project..." />;
  }

  // No featureId in the URL yet -- default to the first feature (if any) so the workspace isn't
  // empty on first load after coming from the projects list.
  const effectiveFeatureId = featureId || features?.[0]?.feature_id || null;

  return (
    <WorkspaceSelectionProvider featureId={effectiveFeatureId} onSelectFeature={handleSelectFeature}>
      <WorkspaceBody projectId={projectId} />
    </WorkspaceSelectionProvider>
  );
}
