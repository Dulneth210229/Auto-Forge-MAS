import { apiClient, artifactContentUrl, artifactDownloadUrl } from "./client";

export async function listFeatureArtifacts(featureId) {
  const { data } = await apiClient.get(`/features/${featureId}/artifacts`);
  return data;
}

export async function getArtifact(artifactId) {
  const { data } = await apiClient.get(`/artifacts/${artifactId}`);
  return data;
}

export async function getArtifactContent(artifactId) {
  const { data } = await apiClient.get(`/artifacts/${artifactId}/content`);
  return data;
}

export { artifactContentUrl, artifactDownloadUrl };
