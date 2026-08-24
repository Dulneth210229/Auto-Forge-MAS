import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useProject } from "../../hooks/useProjects";
import { useDeleteFeature, useFeatures } from "../../hooks/useFeatures";
import { useWorkspaceSelection } from "./WorkspaceSelectionContext";
import FeatureListItem from "./FeatureListItem";
import DomainKnowledgePanel from "./DomainKnowledgePanel";
import DatabaseConnectionPanel from "./DatabaseConnectionPanel";
import CreateFeatureForm from "../features/CreateFeatureForm";
import EditProjectModal from "../projects/EditProjectModal";
import DeleteProjectModal from "../projects/DeleteProjectModal";
import Modal from "../common/Modal";
import ConfirmDialog from "../common/ConfirmDialog";
import LoadingSpinner from "../common/LoadingSpinner";
import ErrorBanner from "../common/ErrorBanner";

// Left panel: this project's features/tasks, like Cursor's task list. Replaces the old
// ProjectDetailPage's feature grid -- clicking a row retargets the whole workspace (middle chat
// + right output) at that feature, rather than navigating to a separate page.
export default function FeatureListPanel({ projectId }) {
  const { data: project } = useProject(projectId);
  const { data: featuresData, isLoading, error } = useFeatures(projectId);
  const features = featuresData || [];
  const { selectedFeatureId, selectFeature } = useWorkspaceSelection();
  const navigate = useNavigate();
  const [showCreate, setShowCreate] = useState(false);
  const [showKnowledge, setShowKnowledge] = useState(false);
  const [showDatabaseConnection, setShowDatabaseConnection] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [deletingFeature, setDeletingFeature] = useState(null);
  const deleteFeature = useDeleteFeature(projectId);

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900 rounded-lg shadow border border-gray-300 dark:border-gray-800">
      <div className="flex-shrink-0 p-3 border-b border-gray-100 dark:border-gray-800">
        <Link to="/" className="text-xs text-gray-400 dark:text-gray-500 hover:text-accent-600 dark:hover:text-accent-400 inline-flex items-center gap-1">
          &larr; Projects
        </Link>
        <div className="flex items-start justify-between gap-2 mt-1">
          <h2 className="text-sm font-bold text-gray-900 dark:text-gray-100 truncate" title={project?.project_name}>
            {project?.project_name || "..."}
          </h2>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={() => setShowEdit(true)}
              title="Edit project"
              className="text-xs text-gray-400 dark:text-gray-500 hover:text-accent-600 dark:hover:text-accent-400"
            >
              Edit
            </button>
            <button
              onClick={() => setShowDelete(true)}
              title="Delete project"
              className="text-xs text-gray-400 dark:text-gray-500 hover:text-red-600 dark:hover:text-red-400"
            >
              Delete
            </button>
          </div>
        </div>
        <p className="text-xs text-gray-400 dark:text-gray-500 truncate">{project?.target_stack}</p>
        <div className="flex items-center gap-2 mt-2 flex-wrap">
          <button
            onClick={() => setShowKnowledge(true)}
            className="text-xs font-semibold bg-white dark:bg-white/10 hover:bg-gray-50 dark:hover:bg-white/20 border border-gray-300 dark:border-gray-600 hover:border-accent-300 dark:hover:border-accent-500/40 text-gray-700 dark:text-gray-200 hover:text-accent-700 dark:hover:text-accent-300 transition-colors px-2.5 py-1 rounded-md inline-flex items-center gap-1"
          >
            Domain Knowledge
          </button>
          <button
            onClick={() => setShowDatabaseConnection(true)}
            className="text-xs font-semibold bg-white dark:bg-white/10 hover:bg-gray-50 dark:hover:bg-white/20 border border-gray-300 dark:border-gray-600 hover:border-accent-300 dark:hover:border-accent-500/40 text-gray-700 dark:text-gray-200 hover:text-accent-700 dark:hover:text-accent-300 transition-colors px-2.5 py-1 rounded-md inline-flex items-center gap-1"
          >
            Database Connection
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-2">
        <div className="flex items-center justify-between px-1 pb-2">
          <h3 className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wide">Features</h3>
          <button
            onClick={() => setShowCreate(true)}
            className="text-xs font-semibold text-accent-600 dark:text-accent-400 hover:text-accent-800 dark:hover:text-accent-300"
          >
            + New
          </button>
        </div>

        <ErrorBanner error={error} fallback="Failed to load features." />

        {isLoading ? (
          <LoadingSpinner label="Loading features..." />
        ) : features.length === 0 ? (
          <p className="text-xs text-gray-400 dark:text-gray-500 italic px-1">No features yet. Create one to get started.</p>
        ) : (
          <div className="flex flex-col gap-1">
            {features.map((feature) => (
              <FeatureListItem
                key={feature.feature_id}
                feature={feature}
                isSelected={feature.feature_id === selectedFeatureId}
                onSelect={() => selectFeature(feature.feature_id)}
                onDeleteClick={setDeletingFeature}
              />
            ))}
          </div>
        )}
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Feature">
        <CreateFeatureForm
          projectId={projectId}
          onCancel={() => setShowCreate(false)}
          onCreated={(feature) => {
            setShowCreate(false);
            selectFeature(feature.feature_id);
          }}
        />
      </Modal>

      <Modal open={showKnowledge} onClose={() => setShowKnowledge(false)} title="Domain Knowledge" size="wide">
        <DomainKnowledgePanel projectId={projectId} />
      </Modal>

      <Modal
        open={showDatabaseConnection}
        onClose={() => setShowDatabaseConnection(false)}
        title="Database Connection"
        size="wide"
      >
        <DatabaseConnectionPanel projectId={projectId} />
      </Modal>

      <EditProjectModal project={project} open={showEdit} onClose={() => setShowEdit(false)} />
      <DeleteProjectModal
        project={project}
        open={showDelete}
        onClose={() => setShowDelete(false)}
        onDeleted={() => navigate("/")}
      />

      <ConfirmDialog
        open={Boolean(deletingFeature)}
        onClose={() => {
          if (!deleteFeature.isPending) setDeletingFeature(null);
        }}
        onConfirm={async () => {
          await deleteFeature.mutateAsync(deletingFeature.feature_id);
          if (deletingFeature.feature_id === selectedFeatureId) {
            navigate(`/projects/${projectId}`);
          }
          setDeletingFeature(null);
        }}
        title="Delete this feature?"
        message={`This permanently deletes "${deletingFeature?.feature_name}" and everything scoped to it -- every artifact, approval, and conversation. This cannot be undone.`}
        confirmLabel="Delete Feature"
        confirmingLabel="Deleting..."
        confirming={deleteFeature.isPending}
        error={deleteFeature.error}
        errorFallback="Failed to delete feature."
      />
    </div>
  );
}
