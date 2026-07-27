import { Link } from "react-router-dom";
import { timeAgo } from "../../lib/format";

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

  return (
    <Link
      to={`/projects/${project.project_id}`}
      className="group relative block bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm hover:shadow-xl hover:-translate-y-1 hover:border-transparent transition-all duration-200"
    >
      <div className={`h-1.5 bg-gradient-to-r ${gradient}`} />

      <div className="p-5">
        <div className="flex items-start justify-between">
          <div
            className={`w-12 h-12 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center text-xl shadow-sm flex-shrink-0`}
          >
            {iconFor(project.project_type)}
          </div>
          <span className="text-gray-300 group-hover:text-accent-500 group-hover:translate-x-0.5 transition-all text-lg">
            &rarr;
          </span>
        </div>

        <h3 className="text-lg font-bold text-gray-900 mt-3 group-hover:text-accent-700 transition-colors">
          {project.project_name}
        </h3>

        <div className="flex flex-wrap gap-1.5 mt-2.5">
          {project.project_type && (
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
              {project.project_type}
            </span>
          )}
          {project.target_stack && (
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-accent-50 text-accent-700">
              {project.target_stack}
            </span>
          )}
        </div>

        <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-100">
          <p className="text-xs text-gray-400">Created by {project.created_by}</p>
          <p className="text-xs text-gray-400">{timeAgo(project.created_at)}</p>
        </div>
      </div>
    </Link>
  );
}
