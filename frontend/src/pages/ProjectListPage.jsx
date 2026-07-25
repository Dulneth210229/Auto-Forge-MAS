import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useProjects } from "../hooks/useProjects";
import PageHeader from "../components/layout/PageHeader";
import ProjectCard from "../components/projects/ProjectCard";
import CreateProjectForm from "../components/projects/CreateProjectForm";
import Modal from "../components/common/Modal";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorBanner from "../components/common/ErrorBanner";

export default function ProjectListPage() {
  const { data: projects, isLoading, error } = useProjects();
  const [showCreate, setShowCreate] = useState(false);
  const navigate = useNavigate();

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader
        title="Projects"
        subtitle={
          projects?.length
            ? `${projects.length} application${projects.length === 1 ? "" : "s"} AutoForge is building.`
            : "The applications AutoForge is building."
        }
        actions={
          <button
            onClick={() => setShowCreate(true)}
            className="bg-accent-600 hover:bg-accent-700 text-white font-semibold py-2 px-4 rounded"
          >
            + New Project
          </button>
        }
      />

      <ErrorBanner error={error} fallback="Failed to load projects." />

      {isLoading ? (
        <LoadingSpinner label="Loading projects..." />
      ) : projects.length === 0 ? (
        <div className="bg-white rounded-lg border border-dashed border-gray-300 p-12 text-center">
          <p className="text-4xl mb-3">🚀</p>
          <p className="text-gray-700 font-semibold">No projects yet</p>
          <p className="text-gray-500 text-sm mt-1">Create your first project to start the pipeline.</p>
          <button
            onClick={() => setShowCreate(true)}
            className="mt-4 bg-accent-600 hover:bg-accent-700 text-white font-semibold py-2 px-4 rounded"
          >
            + New Project
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <ProjectCard key={project.project_id} project={project} />
          ))}
        </div>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Project">
        <CreateProjectForm
          onCancel={() => setShowCreate(false)}
          onCreated={(project) => {
            setShowCreate(false);
            navigate(`/projects/${project.project_id}`);
          }}
        />
      </Modal>
    </div>
  );
}
