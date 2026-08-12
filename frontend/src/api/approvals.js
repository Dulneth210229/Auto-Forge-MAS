import { apiClient } from "./client";

export async function submitApproval(artifactId, { status, reviewer_comment, approved_by }) {
  const { data } = await apiClient.post(`/artifacts/${artifactId}/approval`, {
    status,
    reviewer_comment,
    approved_by,
  });
  return data;
}
