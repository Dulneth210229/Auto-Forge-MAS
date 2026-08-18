import Modal from "../common/Modal";
import { ARTIFACT_TYPE_LABELS } from "../../lib/artifactTypeMeta";
import ArtifactContentView from "./ArtifactContentView";
import SecurityReportView from "../security/SecurityReportView";

export default function ArtifactViewerModal({ artifact, onClose }) {
  const isSecurityReport = artifact?.artifact_type === "security_report";

  return (
    <Modal
      open={Boolean(artifact)}
      onClose={onClose}
      title={artifact ? `${ARTIFACT_TYPE_LABELS[artifact.artifact_type] || artifact.artifact_type} (v${artifact.version})` : ""}
      wide
    >
      {isSecurityReport ? (
        // The nice Critical/Moderate/Warning report (SecurityReportView.jsx) already renders in
        // the main Result panel for the currently-selected version -- this is the OTHER path a
        // security report can be opened from (any "View" link/button, e.g. an older version),
        // which previously fell through to the generic raw-JSON ArtifactContentView below.
        // `artifact.feature_id` is already present on every artifact record, same as the Result
        // panel's own usage.
        <SecurityReportView artifact={artifact} featureId={artifact.feature_id} />
      ) : (
        <ArtifactContentView artifact={artifact} />
      )}
    </Modal>
  );
}
