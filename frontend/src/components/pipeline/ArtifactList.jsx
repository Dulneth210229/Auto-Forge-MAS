import ArtifactRow from "./ArtifactRow";

export default function ArtifactList({ artifacts, onView, gatingArtifactType, reviseMutation, featureId }) {
  if (artifacts.length === 0) {
    return null;
  }

  const sorted = [...artifacts].sort((a, b) => {
    if (a.artifact_type !== b.artifact_type) {
      return a.artifact_type.localeCompare(b.artifact_type);
    }
    return b.version - a.version;
  });

  return (
    <div className="flex flex-col gap-2 mt-3">
      {sorted.map((artifact) => {
        const isGating = artifact.artifact_type === gatingArtifactType;
        return (
          <ArtifactRow
            key={artifact.artifact_id}
            artifact={artifact}
            onView={onView}
            reviseMutation={isGating ? reviseMutation : null}
            // The gating artifact already gets a dedicated ApprovalPanel rendered alongside this
            // list -- only non-gating rows (e.g. individual UI/UX components) need their own
            // inline approval actions.
            featureId={isGating ? undefined : featureId}
          />
        );
      })}
    </div>
  );
}
