import { useEffect, useState } from "react";
import { listGatingArtifactVersions } from "../../lib/deriveStageStatus";
import { artifactDownloadUrl, featureCodeDownloadUrl } from "../../api/client";
import ArtifactContentView from "../artifacts/ArtifactContentView";
import ArchitectureDiagramsGallery from "./ArchitectureDiagramsGallery";
import UiuxPagePreviewsPanel from "./UiuxPagePreviewsPanel";

export default function StageOutputPanel({ stage, featureId, allArtifacts }) {
  const versions = listGatingArtifactVersions(stage, allArtifacts);
  const [selectedVersion, setSelectedVersion] = useState(versions[0]?.version ?? null);

  useEffect(() => {
    if (versions.length > 0 && !versions.some((v) => v.version === selectedVersion)) {
      setSelectedVersion(versions[0].version);
    }
  }, [versions, selectedVersion]);

  if (versions.length === 0) {
    return <p className="text-sm text-gray-400 italic">No output yet for this stage.</p>;
  }

  const artifact = versions.find((v) => v.version === selectedVersion) || versions[0];

  const versionHeader = (
    <div className="flex items-center justify-between mb-3">
      <select
        value={selectedVersion ?? ""}
        onChange={(e) => setSelectedVersion(Number(e.target.value))}
        className="text-sm border border-gray-300 rounded-md p-1.5 focus:outline-none focus:border-accent-500"
      >
        {versions.map((v) => (
          <option key={v.artifact_id} value={v.version}>
            v{v.version} -- {v.approval_status}
          </option>
        ))}
      </select>
      <div className="flex items-center gap-3">
        <a
          href={artifactDownloadUrl(artifact.artifact_id)}
          className="text-sm text-accent-600 hover:text-accent-800 font-semibold"
        >
          Download report
        </a>
        {stage === "coder" && (
          <a
            href={featureCodeDownloadUrl(featureId)}
            className="text-sm bg-accent-600 hover:bg-accent-700 text-white font-semibold px-3 py-1.5 rounded-md"
          >
            Download Project (.zip)
          </a>
        )}
      </div>
    </div>
  );

  // UI/UX Output shows ONLY the rendered Page Previews -- no version selector, download-report
  // link, raw ui_metadata JSON, or component code list. Per direct user feedback, this section
  // should be the images and nothing else; the metadata/component code/download are still
  // reachable via the Artifacts tab in the sidebar.
  if (stage === "uiux") {
    return <UiuxPagePreviewsPanel allArtifacts={allArtifacts} />;
  }

  return (
    <div>
      {versionHeader}
      <ArtifactContentView artifact={artifact} />
      {stage === "architecture" && <ArchitectureDiagramsGallery allArtifacts={allArtifacts} />}
    </div>
  );
}
