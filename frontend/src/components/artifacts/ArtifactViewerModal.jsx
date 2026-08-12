import Modal from "../common/Modal";
import { ARTIFACT_TYPE_LABELS } from "../../lib/artifactTypeMeta";
import ArtifactContentView from "./ArtifactContentView";

export default function ArtifactViewerModal({ artifact, onClose }) {
  return (
    <Modal
      open={Boolean(artifact)}
      onClose={onClose}
      title={artifact ? `${ARTIFACT_TYPE_LABELS[artifact.artifact_type] || artifact.artifact_type} (v${artifact.version})` : ""}
      wide
    >
      <ArtifactContentView artifact={artifact} />
    </Modal>
  );
}
