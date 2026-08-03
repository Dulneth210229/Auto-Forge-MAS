import { ARTIFACT_TYPE_STAGE } from "./artifactTypeMeta";

// Generalized from StageInteractionPanel's old per-stage buildTimeline: instead of one stage's
// slice of artifacts/approvals/events, this builds ONE continuous chronological feed across
// every agent for the whole feature, tagging each item with the stage it belongs to so the chat
// panel can show a single conversation-like history regardless of which agent is currently
// selected. Still a real activity log (ask/response/decision), not a live back-and-forth chat --
// see stage_event_schema.py / approval_schema.py for why these three sources can't be
// reconstructed from artifacts alone (human_comment/reviewer_comment live on separate records).
export function buildAgentTimeline(allArtifacts, allApprovals, allEvents) {
  const items = [];

  for (const event of allEvents) {
    items.push({
      kind: "ask",
      stage: event.agent_name.replace(/_agent$/, ""),
      timestamp: new Date(event.requested_at).getTime(),
      comment: event.human_comment,
      eventType: event.event_type,
    });
  }

  const byStageVersion = new Map();
  for (const artifact of allArtifacts) {
    const stage = ARTIFACT_TYPE_STAGE[artifact.artifact_type];
    if (!stage) continue;
    const key = `${stage}:${artifact.version}`;
    if (!byStageVersion.has(key)) {
      byStageVersion.set(key, {
        stage,
        version: artifact.version,
        timestamp: new Date(artifact.created_at).getTime(),
        types: [],
        artifactIds: [],
      });
    }
    const group = byStageVersion.get(key);
    group.types.push(artifact.artifact_type);
    group.artifactIds.push(artifact.artifact_id);
  }
  for (const group of byStageVersion.values()) {
    items.push({
      kind: "response",
      stage: group.stage,
      timestamp: group.timestamp,
      version: group.version,
      types: [...new Set(group.types)],
    });
  }

  const artifactById = new Map(allArtifacts.map((a) => [a.artifact_id, a]));
  for (const approval of allApprovals) {
    const artifact = artifactById.get(approval.artifact_id);
    if (!artifact) continue;
    items.push({
      kind: "decision",
      stage: ARTIFACT_TYPE_STAGE[artifact.artifact_type],
      timestamp: new Date(approval.approved_at).getTime(),
      status: approval.status,
      comment: approval.reviewer_comment,
    });
  }

  items.sort((a, b) => a.timestamp - b.timestamp);
  return items;
}
