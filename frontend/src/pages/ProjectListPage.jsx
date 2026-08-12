import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useProjects } from "../hooks/useProjects";
import PageHeader from "../components/layout/PageHeader";
import ProjectCard from "../components/projects/ProjectCard";
import CreateProjectForm from "../components/projects/CreateProjectForm";
import Modal from "../components/common/Modal";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorBanner from "../components/common/ErrorBanner";

function StatChip({ value, label }) {
  return (
    <div className="flex-1 min-w-[120px] bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 px-4 py-3">
      <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{value}</p>
      <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">{label}</p>
    </div>
  );
}

export default function ProjectListPage() {
  const { data: projects, isLoading, error } = useProjects();
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState("");
  const navigate = useNavigate();

  const stats = useMemo(() => {
    if (!projects?.length) return null;
    return {
      total: projects.length,
      types: new Set(projects.map((p) => p.project_type).filter(Boolean)).size,
      stacks: new Set(projects.map((p) => p.target_stack).filter(Boolean)).size,
    };
  }, [projects]);

  const filtered = useMemo(() => {
    if (!projects) return [];
    const q = search.trim().toLowerCase();
    if (!q) return projects;
    return projects.filter((p) =>
      [p.project_name, p.project_type, p.target_stack].filter(Boolean).some((v) => v.toLowerCase().includes(q))
    );
  }, [projects, search]);

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
            className="bg-gradient-to-r from-accent-600 to-accent-500 hover:from-accent-700 hover:to-accent-600 text-white font-semibold py-2 px-4 rounded-lg shadow-sm hover:shadow-md transition-all"
          >
            + New Project
          </button>
        }
      />

      <ErrorBanner error={error} fallback="Failed to load projects." />

      {isLoading ? (
        <LoadingSpinner label="Loading projects..." />
      ) : projects.length === 0 ? (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-dashed border-gray-300 dark:border-gray-700 p-12 text-center">
          <p className="text-4xl mb-3">🚀</p>
          <p className="text-gray-700 dark:text-gray-200 font-semibold">No projects yet</p>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">Create your first project to start the pipeline.</p>
          <button
            onClick={() => setShowCreate(true)}
            className="mt-4 bg-accent-600 hover:bg-accent-700 text-white font-semibold py-2 px-4 rounded"
          >
            + New Project
          </button>
        </div>
      ) : (
        <>
          {stats && (
            <div className="flex flex-wrap gap-3 mb-5">
              <StatChip value={stats.total} label="Total Projects" />
              <StatChip value={stats.types} label="Project Types" />
              <StatChip value={stats.stacks} label="Tech Stacks" />
            </div>
          )}

          <div className="mb-5">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search projects by name, type, or stack..."
              className="w-full max-w-md text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-2.5 focus:outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500 bg-white dark:bg-white/5 dark:text-gray-100"
            />
          </div>

          {filtered.length === 0 ? (
            <p className="text-sm text-gray-400 dark:text-gray-500 italic">No projects match "{search}".</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map((project, index) => (
                <div
                  key={project.project_id}
                  className="animate-[fadeInUp_0.35s_ease-out_backwards]"
                  style={{ animationDelay: `${Math.min(index, 8) * 40}ms` }}
                >
                  <ProjectCard project={project} />
                </div>
              ))}
            </div>
          )}
        </>
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

      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
