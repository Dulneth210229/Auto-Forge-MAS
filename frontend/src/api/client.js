import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

export function artifactContentUrl(artifactId) {
  return `${API_BASE_URL}/artifacts/${artifactId}/content`;
}

export function artifactDownloadUrl(artifactId) {
  return `${API_BASE_URL}/artifacts/${artifactId}/download`;
}

export function artifactDownloadPdfUrl(artifactId) {
  return `${API_BASE_URL}/artifacts/${artifactId}/download-pdf`;
}

export function featureCodeDownloadUrl(featureId) {
  return `${API_BASE_URL}/features/${featureId}/code/download`;
}

export function projectCodeDownloadUrl(projectId) {
  return `${API_BASE_URL}/projects/${projectId}/code/download`;
}
