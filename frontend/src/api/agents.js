import { apiClient } from "./client";

const base = (featureId) => `/features/${featureId}/agents`;

// Requirement Agent
export async function runRequirement(featureId, { ba_input, human_comment }) {
  const { data } = await apiClient.post(`${base(featureId)}/requirement/run`, {
    ba_input,
    human_comment,
  });
  return data;
}

export async function reviseRequirement(featureId, { revision_comment, revised_by }) {
  const { data } = await apiClient.post(`${base(featureId)}/requirement/revise`, {
    revision_comment,
    revised_by,
  });
  return data;
}

// Domain Agent (auto-runs via the graph; revise is exposed for a real, occasional manual nudge)
export async function reviseDomain(featureId, { revision_comment, revised_by }) {
  const { data } = await apiClient.post(`${base(featureId)}/domain/revise`, {
    revision_comment,
    revised_by,
  });
  return data;
}

// Architecture Agent
export async function runArchitecture(
  featureId,
  { use_enhanced_srs_if_available = true, architecture_notes, human_comment }
) {
  const { data } = await apiClient.post(`${base(featureId)}/architecture/run`, {
    use_enhanced_srs_if_available,
    architecture_notes,
    human_comment,
  });
  return data;
}

export async function reviseArchitecture(featureId, { revision_comment, revised_by }) {
  const { data } = await apiClient.post(`${base(featureId)}/architecture/revise`, {
    revision_comment,
    revised_by,
  });
  return data;
}

// Coder Agent (initial run only happens via the graph; revise is the only real HTTP-reachable action)
export async function reviseCoder(featureId, { revision_comment, revised_by }) {
  const { data } = await apiClient.post(`${base(featureId)}/coder/revise`, {
    revision_comment,
    revised_by,
  });
  return data;
}
