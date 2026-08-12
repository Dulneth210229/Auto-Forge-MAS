import { useState } from "react";
import { Link } from "react-router-dom";
import { timeAgo } from "../../lib/format";
import EditProjectModal from "./EditProjectModal";
import DeleteProjectModal from "./DeleteProjectModal";

const TYPE_ICONS = {
  "e-commerce": "🛒",
  saas: "☁️",
  social: "💬",
  fintech: "💳",
  healthcare: "🏥",
  education: "🎓",
};

const TYPE_GRADIENTS = {
  "e-commerce": "from-orange-400 to-pink-500",
  saas: "from-sky-400 to-indigo-500",
  social: "from-fuchsia-400 to-purple-500",
  fintech: "from-emerald-400 to-teal-500",
  healthcare: "from-rose-400 to-red-500",
  education: "from-amber-400 to-orange-500",
};

function iconFor(projectType) {
  const key = (projectType || "").toLowerCase();
  return TYPE_ICONS[key] || "📦";
}

function gradientFor(projectType) {
  const key = (projectType || "").toLowerCase();
  return TYPE_GRADIENTS[key] || "from-accent-400 to-accent-600";
}

export default function ProjectCard({ project }) {
  const gradient = gradientFor(project.project_type);
  const [showEdit, setShowEdit] = useState(false);
  const [showDelete, setShowDelete] = useState(false);

  return (
    <>
    <Link
      to={`/projects/${project.project_id}`}
      className="group relative block bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden shadow-sm hover:shadow-xl hover:-translate-y-1 hover:border-transparent transition-all duration-200"
    >
      <div className={`h-1.5 bg-gradient-to-r ${gradient}`} />

      {/* Edit/Delete -- hover-revealed, stop propagation so clicking them doesn't also
          navigate into the project (the whole card is a Link). */}
      <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
        <button
          type="button"
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            setShowEdit(true);
          }}
          title="Edit project"
          className="w-7 h-7 flex items-center justify-center rounded-full bg-white/90 dark:bg-gray-800/90 text-gray-500 dark:text-gray-400 hover:text-accent-600 dark:hover:text-accent-400 shadow-sm text-sm"
        >
          ✎
        </button>
        <button
          type="button"
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            setShowDelete(true);
          }}
          title="Delete project"
          className="w-7 h-7 flex items-center justify-center rounded-full bg-white/90 dark:bg-gray-800/90 text-gray-500 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 shadow-sm text-sm"
        >
          &times;
        </button>
      </div>

      <div className="p-5">
        <div className="flex items-start justify-between">
          <div
            className={`w-12 h-12 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center text-xl shadow-sm flex-shrink-0`}
          >
            {iconFor(project.project_type)}
          </div>
          <span className="text-gray-300 dark:text-gray-700 group-hover:text-accent-500 group-hover:translate-x-0.5 transition-all text-lg">
            &rarr;
          </span>
        </div>

        <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mt-3 group-hover:text-accent-700 dark:group-hover:text-accent-400 transition-colors">
          {project.project_name}
        </h3>

        <div className="flex flex-wrap gap-1.5 mt-2.5">
          {project.project_type && (
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-300">
              {project.project_type}
            </span>
          )}
          {project.target_stack && (
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-accent-50 dark:bg-accent-500/15 text-accent-700 dark:text-accent-300">
              {project.target_stack}
            </span>
          )}
        </div>

        <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-100 dark:border-gray-800">
          <p className="text-xs text-gray-400 dark:text-gray-500">Created by {project.created_by}</p>
          <p className="text-xs text-gray-400 dark:text-gray-500">{timeAgo(project.created_at)}</p>
        </div>
      </div>
    </Link>

    <EditProjectModal project={project} open={showEdit} onClose={() => setShowEdit(false)} />
    <DeleteProjectModal project={project} open={showDelete} onClose={() => setShowDelete(false)} />
    </>
  );
}
