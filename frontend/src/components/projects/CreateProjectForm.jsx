import { useState } from "react";
import { useCreateProject } from "../../hooks/useProjects";
import ErrorBanner from "../common/ErrorBanner";

export default function CreateProjectForm({ onCreated, onCancel }) {
  const [projectName, setProjectName] = useState("");
  const [projectType, setProjectType] = useState("E-commerce");
  const [targetStack, setTargetStack] = useState("MERN");
  const createProject = useCreateProject();

  async function handleSubmit(event) {
    event.preventDefault();

    const project = await createProject.mutateAsync({
      project_name: projectName.trim(),
      project_type: projectType.trim(),
      target_stack: targetStack.trim() || "MERN",
      created_by: "human_user",
    });

    onCreated?.(project);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <ErrorBanner error={createProject.error} fallback="Failed to create project." />

      <div>
        <label className="block text-sm font-semibold mb-1">Project Name</label>
        <input
          required
          value={projectName}
          onChange={(event) => setProjectName(event.target.value)}
          placeholder="E-commerce Platform"
          className="w-full p-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:border-accent-500"
        />
      </div>

      <div>
        <label className="block text-sm font-semibold mb-1">Project Type</label>
        <input
          required
          value={projectType}
          onChange={(event) => setProjectType(event.target.value)}
          placeholder="E-commerce"
          className="w-full p-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:border-accent-500"
        />
      </div>

      <div>
        <label className="block text-sm font-semibold mb-1">Target Stack</label>
        <input
          value={targetStack}
          onChange={(event) => setTargetStack(event.target.value)}
          className="w-full p-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:border-accent-500"
        />
      </div>

      <div className="flex gap-2 justify-end">
        <button
          type="button"
          onClick={onCancel}
          className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-2 px-4 rounded"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={createProject.isPending}
          className="bg-accent-600 hover:bg-accent-700 disabled:opacity-50 text-white font-semibold py-2 px-4 rounded"
        >
          {createProject.isPending ? "Creating..." : "Create Project"}
        </button>
      </div>
    </form>
  );
}
