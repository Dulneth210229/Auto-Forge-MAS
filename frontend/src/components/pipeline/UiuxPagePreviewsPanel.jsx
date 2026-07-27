import { artifactDownloadUrl } from "../../api/client";
import ImageViewer from "../artifacts/ImageViewer";

// Page screenshots share one artifact_type (ui_preview_screenshot) regardless of which page they
// are -- the only real identity is the file's own basename, so "latest of each" means grouping by
// that, not by version number alone.
function latestByFile(artifacts) {
  const matches = artifacts.filter((a) => a.artifact_type === "ui_preview_screenshot");
  const byName = new Map();

  for (const artifact of matches) {
    const name = artifact.file_path.split(/[\\/]/).pop();
    const existing = byName.get(name);
    if (!existing || artifact.version > existing.version) {
      byName.set(name, artifact);
    }
  }

  return [...byName.values()];
}

// This is the UI/UX stage's MAIN output, not a side extra -- per direct user feedback, a human
// reviewing this stage cares most about what the pages actually look like, not the raw
// ui_metadata JSON. Rendered full-width with real-size screenshots; the metadata/components live
// in the narrower side column instead (see StageOutputPanel).
export default function UiuxPagePreviewsPanel({ allArtifacts }) {
  const screenshots = latestByFile(allArtifacts);

  if (screenshots.length === 0) {
    return <p className="text-sm text-gray-400 italic">No page previews were rendered for this stage.</p>;
  }

  return (
    <div>
      <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wide mb-3">
        Page Previews ({screenshots.length})
      </h3>
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {screenshots.map((artifact) => (
          <div key={artifact.artifact_id} className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-200">
              <p className="text-xs font-semibold text-gray-700 truncate" title={artifact.file_path}>
                {artifact.file_path.split(/[\\/]/).pop()}
              </p>
              <a
                href={artifactDownloadUrl(artifact.artifact_id)}
                className="text-xs text-accent-600 hover:text-accent-800 font-semibold flex-shrink-0"
              >
                Download
              </a>
            </div>
            <div className="p-2">
              <ImageViewer artifactId={artifact.artifact_id} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
