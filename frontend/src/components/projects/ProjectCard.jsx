import { Link } from "react-router-dom";

const TYPE_ICONS = {
  "e-commerce": "🛒",
  saas: "☁️",
  social: "💬",
  fintech: "💳",
  healthcare: "🏥",
  education: "🎓",
};

function iconFor(projectType) {
  const key = (projectType || "").toLowerCase();
  return TYPE_ICONS[key] || "📦";
}

export default function ProjectCard({ project }) {
  return (
    <Link
      to={`/projects/${project.project_id}`}
      className="group block bg-white rounded-lg shadow-sm border border-gray-200 p-5 hover:shadow-lg hover:border-accent-200 hover:-translate-y-0.5 transition-all"
    >
      <div className="flex items-start justify-between">
        <div className="w-10 h-10 rounded-lg bg-accent-50 flex items-center justify-center text-lg flex-shrink-0">
          {iconFor(project.project_type)}
        </div>
        <span className="text-gray-300 group-hover:text-accent-500 transition-colors text-lg">&rarr;</span>
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mt-3">{project.project_name}</h3>
      <p className="text-sm text-gray-500 mt-1">
        {project.project_type} &middot; {project.target_stack}
      </p>
      <p className="text-xs text-gray-400 mt-2">Created by {project.created_by}</p>
    </Link>
  );
}
