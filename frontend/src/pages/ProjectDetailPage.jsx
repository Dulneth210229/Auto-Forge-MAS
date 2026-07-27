import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useProject } from "../hooks/useProjects";
import { useFeatures } from "../hooks/useFeatures";
import { projectCodeDownloadUrl } from "../api/client";
import PageHeader from "../components/layout/PageHeader";
import FeatureCard from "../components/features/FeatureCard";
import CreateFeatureForm from "../components/features/CreateFeatureForm";
import Modal from "../components/common/Modal";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorBanner from "../components/common/ErrorBanner";

function formatDate(iso) {
  if (!iso) return "--";
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { data: project, isLoading: projectLoading, error: projectError } = useProject(projectId);
  const { data: features, isLoading: featuresLoading, error: featuresError } = useFeatures(projectId);
  const [showCreate, setShowCreate] = useState(false);

  const statusCounts = useMemo(() => {
    const counts = {};
    for (const f of features || []) {
      counts[f.feature_status] = (counts[f.feature_status] || 0) + 1;
    }
    return counts;
  }, [features]);

  if (projectLoading) {
    return <LoadingSpinner label="Loading project..." />;
  }

  return (
    <div className="h-full overflow-y-auto">
      <ErrorBanner error={projectError} fallback="Failed to load project." />

      <Link to="/" className="text-sm text-gray-500 hover:text-accent-600 mb-2 inline-flex items-center gap-1 w-fit">
        &larr; Back to projects
      </Link>

      {project && (
        <>
          <PageHeader
            title={project.project_name}
            subtitle={`${project.project_type} · ${project.target_stack}`}
            actions={
              <>
                <a
                  href={projectCodeDownloadUrl(projectId)}
                  className="bg-white hover:bg-gray-50 text-gray-700 font-semibold py-2 px-4 rounded border border-gray-300"
                >
                  Download Project (.zip)
                </a>
                <button
                  onClick={() => setShowCreate(true)}
                  className="bg-accent-600 hover:bg-accent-700 text-white font-semibold py-2 px-4 rounded"
                >
                  + New Feature
                </button>
              </>
            }
          />

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6 flex flex-wrap gap-x-10 gap-y-2 text-sm">
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide">Project ID</p>
              <p className="text-gray-700 font-mono text-xs mt-0.5">{project.project_id}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide">Created</p>
              <p className="text-gray-700 mt-0.5">{formatDate(project.created_at)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide">Created By</p>
              <p className="text-gray-700 mt-0.5">{project.created_by}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide">Features</p>
              <div className="flex gap-1.5 mt-1">
                {Object.keys(statusCounts).length === 0 ? (
                  <span className="text-gray-400">None yet</span>
                ) : (
                  Object.entries(statusCounts).map(([status, count]) => (
                    <span key={status} className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full text-xs">
                      {count} {status.replace(/_/g, " ")}
                    </span>
                  ))
                )}
              </div>
            </div>
          </div>
        </>
      )}

      <ErrorBanner error={featuresError} fallback="Failed to load features." />

      {featuresLoading ? (
        <LoadingSpinner label="Loading features..." />
      ) : features.length === 0 ? (
        <p className="text-gray-500">No features yet. Create one to start the pipeline.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((feature) => (
            <FeatureCard key={feature.feature_id} projectId={projectId} feature={feature} />
          ))}
        </div>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Feature">
        <CreateFeatureForm
          projectId={projectId}
          onCancel={() => setShowCreate(false)}
          onCreated={(feature) => {
            setShowCreate(false);
            navigate(`/projects/${projectId}/features/${feature.feature_id}`);
          }}
        />
      </Modal>
    </div>
  );
}
