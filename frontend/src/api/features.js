import { apiClient } from "./client";

export async function listFeatures(projectId) {
  const { data } = await apiClient.get(`/projects/${projectId}/features`);
  return data;
}

export async function getFeature(featureId) {
  const { data } = await apiClient.get(`/features/${featureId}`);
  return data;
}

export async function createFeature(projectId, { feature_name, feature_description }) {
  const { data } = await apiClient.post(`/projects/${projectId}/features`, {
    feature_name,
    feature_description,
  });
  return data;
}

export async function startPipeline(featureId) {
  const { data } = await apiClient.post(`/features/${featureId}/start`);
  return data;
}

export async function getGraphStatus(featureId) {
  const { data } = await apiClient.get(`/features/${featureId}/graph-status`);
  return data;
}

export async function listFeatureApprovals(featureId) {
  const { data } = await apiClient.get(`/features/${featureId}/approvals`);
  return data;
}

export async function listFeatureEvents(featureId) {
  const { data } = await apiClient.get(`/features/${featureId}/events`);
  return data;
}
