import { apiClient, API_BASE_URL } from "./client";

const base = (featureId) => `/features/${featureId}/agents`;

// Shared by every streamed endpoint (confirm, reply): POSTs a JSON body and reads the response
// body as newline-delimited JSON events via fetch's own ReadableStream reader (not axios, which
// buffers the whole response) -- onEvent is called once per parsed line, in order, as it arrives.
async function streamNdjsonPost(url, body, onEvent) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok || !response.body) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    let newlineIndex;
    while ((newlineIndex = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, newlineIndex).trim();
      buffer = buffer.slice(newlineIndex + 1);
      if (!line) continue;

      try {
        onEvent(JSON.parse(line));
      } catch {
        // Malformed/partial line -- ignore rather than crash the whole stream.
      }
    }
  }
}

// Requirement Agent
export async function runRequirement(featureId, { ba_input, human_comment }) {
  const { data } = await apiClient.post(`${base(featureId)}/requirement/run`, {
    ba_input,
    human_comment,
  });
  return data;
}

// Live, token-by-token revision (ChatGPT/Claude-style) -- the agent's revision_summary reaction
// + the regenerated SRS "type" in as they're generated, same mechanism as the other streamed
// Requirement Agent endpoints. This is the only revise path the frontend uses now; the backend's
// plain (non-streaming) POST /requirement/revise route still exists and works for any direct API
// caller, it's just no longer called from here.
export async function reviseRequirementStream(featureId, { revision_comment, revised_by }, onEvent) {
  await streamNdjsonPost(
    `${API_BASE_URL}${base(featureId)}/requirement/revise/stream`,
    { revision_comment, revised_by },
    onEvent
  );
}

// Requirement Agent conversational gap-filling loop -- additive, alongside run/revise above.
export async function startRequirementConversation(featureId) {
  const { data } = await apiClient.post(`${base(featureId)}/requirement/conversation/start`);
  return data;
}

// Live, token-by-token reply (ChatGPT/Claude-style) -- the agent's reaction+questions "type" in
// as they're generated, same newline-delimited-JSON-over-fetch mechanism as
// confirmRequirementConversationStream below. This is the only reply path the frontend uses now;
// the backend's plain (non-streaming) POST /requirement/conversation/reply route still exists and
// works for any direct API caller, it's just no longer called from here.
export async function replyToRequirementConversationStream(featureId, { reply }, onEvent) {
  await streamNdjsonPost(
    `${API_BASE_URL}${base(featureId)}/requirement/conversation/reply/stream`,
    { reply },
    onEvent
  );
}

// Reply with an attached text/PDF/DOCX/MD document -- the backend extracts its full text and
// scrapes requirements from it the same way it would from typed text. Omitting an explicit
// Content-Type lets the browser/axios set the multipart boundary itself; setting it manually
// would break the upload.
export async function replyToRequirementConversationWithDocument(featureId, { file, reply }) {
  const formData = new FormData();
  formData.append("file", file);
  if (reply) formData.append("reply", reply);
  const { data } = await apiClient.post(`${base(featureId)}/requirement/conversation/reply/upload`, formData);
  return data;
}

// Edits an already-submitted reply and regenerates the conversation from that point forward --
// mirrors ChatGPT/Claude's "edit message" flow. Discards the edited turn and everything after it.
// Live, token-by-token: the regenerated reaction+questions "type" in live instead of sitting
// behind a plain spinner for however long the real LLM call takes, same mechanism as
// replyToRequirementConversationStream. The backend also still has a plain (non-streaming) POST
// .../turns/{turnIndex}/edit route for any direct API caller; the frontend only uses this one.
export async function editRequirementConversationTurnStream(featureId, turnIndex, { reply }, onEvent) {
  await streamNdjsonPost(
    `${API_BASE_URL}${base(featureId)}/requirement/conversation/turns/${turnIndex}/edit/stream`,
    { reply },
    onEvent
  );
}

export async function getRequirementConversation(featureId) {
  const { data } = await apiClient.get(`${base(featureId)}/requirement/conversation`);
  return data;
}

export async function resetRequirementConversation(featureId) {
  const { data } = await apiClient.post(`${base(featureId)}/requirement/conversation/reset`);
  return data;
}

export async function confirmRequirementConversation(
  featureId,
  { override_quality_gate = false, override_reason, confirmed_by = "human_user" } = {}
) {
  const { data } = await apiClient.post(`${base(featureId)}/requirement/conversation/confirm`, {
    override_quality_gate,
    override_reason,
    confirmed_by,
  });
  return data;
}

// Streaming variant -- the response body is newline-delimited JSON events
// ({"type": "token"|"error"|"done", ...}) so the SRS can be shown "typing" live as it's
// generated. onEvent is called once per parsed line, in order.
export async function confirmRequirementConversationStream(
  featureId,
  { override_quality_gate = false, override_reason, confirmed_by = "human_user" } = {},
  onEvent
) {
  await streamNdjsonPost(
    `${API_BASE_URL}${base(featureId)}/requirement/conversation/confirm/stream`,
    { override_quality_gate, override_reason, confirmed_by },
    onEvent
  );
}

// Domain Agent (auto-runs via the graph once Requirement is approved; both a manual initial run
// and revise are also real, e.g. for referencing an uploaded document via "/" before the graph
// gets there on its own)
export async function runDomain(featureId, { human_comment, referenced_document_ids = [] } = {}) {
  const { data } = await apiClient.post(`${base(featureId)}/domain/run`, {
    human_comment,
    referenced_document_ids,
  });
  return data;
}

export async function reviseDomain(featureId, { revision_comment, revised_by, referenced_document_ids = [] }) {
  const { data } = await apiClient.post(`${base(featureId)}/domain/revise`, {
    revision_comment,
    revised_by,
    referenced_document_ids,
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

// UI/UX Agent
export async function runUiux(featureId, { use_enhanced_srs_if_available = true, ui_preferences, human_comment } = {}) {
  const { data } = await apiClient.post(`${base(featureId)}/uiux/run`, {
    use_enhanced_srs_if_available,
    ui_preferences,
    human_comment,
  });
  return data;
}

// Coder Agent
export async function runCoder(featureId, { use_enhanced_srs_if_available = true, human_comment } = {}) {
  const { data } = await apiClient.post(`${base(featureId)}/coder/run`, {
    use_enhanced_srs_if_available,
    human_comment,
  });
  return data;
}

export async function reviseCoder(featureId, { revision_comment, revised_by }) {
  const { data } = await apiClient.post(`${base(featureId)}/coder/revise`, {
    revision_comment,
    revised_by,
  });
  return data;
}
