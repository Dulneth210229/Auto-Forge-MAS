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

// Shown as a persistent panel right next to the UI/UX Output, not behind a tab click or below a
// scroll -- these are the single most useful thing to glance at while reviewing this stage.
export default function UiuxPagePreviewsPanel({ allArtifacts }) {
  const screenshots = latestByFile(allArtifacts);

  return (
    <div className="w-72 flex-shrink-0 h-full overflow-y-auto border-l border-gray-100 pl-4">
      <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2">
        Page Previews {screenshots.length > 0 && `(${screenshots.length})`}
      </h3>
      {screenshots.length === 0 ? (
        <p className="text-xs text-gray-400 italic">No page previews were rendered.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {screenshots.map((artifact) => (
            <div key={artifact.artifact_id} className="border border-gray-200 rounded-lg p-2">
              <div className="flex items-center justify-between mb-1.5">
                <p className="text-xs font-semibold text-gray-600 truncate" title={artifact.file_path}>
                  {artifact.file_path.split(/[\\/]/).pop()}
                </p>
                <a
                  href={artifactDownloadUrl(artifact.artifact_id)}
                  className="text-xs text-accent-600 hover:text-accent-800 font-semibold flex-shrink-0"
                >
                  Download
                </a>
              </div>
              <ImageViewer artifactId={artifact.artifact_id} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
