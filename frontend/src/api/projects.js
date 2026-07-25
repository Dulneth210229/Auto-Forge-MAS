import { apiClient } from "./client";

export async function listProjects() {
  const { data } = await apiClient.get("/projects");
  return data;
}

export async function getProject(projectId) {
  const { data } = await apiClient.get(`/projects/${projectId}`);
  return data;
}

export async function createProject({ project_name, project_type, target_stack, created_by }) {
  const { data } = await apiClient.post("/projects", {
    project_name,
    project_type,
    target_stack,
    created_by,
  });
  return data;
}
