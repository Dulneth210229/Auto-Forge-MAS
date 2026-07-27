import { artifactDownloadUrl } from "../../api/client";
import CodeViewer from "../artifacts/CodeViewer";
import { useArtifactContent } from "../../hooks/useArtifacts";
import StatusBadge from "../common/StatusBadge";

// Components share one artifact_type (ui_component_code) regardless of which actual component --
// the only real identity is the file's own basename, so "latest of each" means grouping by that,
// not by version number alone (two different components can legitimately be at different
// versions).
function latestByFile(artifacts) {
  const matches = artifacts.filter((a) => a.artifact_type === "ui_component_code");
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

function ComponentCard({ artifact }) {
  const { data } = useArtifactContent(artifact.artifact_id);
  const name = artifact.file_path.split(/[\\/]/).pop();

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-200">
        <p className="text-xs font-semibold text-gray-700">
          {name} <span className="text-gray-400">v{artifact.version}</span>
        </p>
        <div className="flex items-center gap-2">
          <StatusBadge status={artifact.approval_status} />
          <a href={artifactDownloadUrl(artifact.artifact_id)} className="text-xs text-accent-600 hover:text-accent-800 font-semibold">
            Download
          </a>
        </div>
      </div>
      <div className="max-h-72 overflow-y-auto p-2">
        <CodeViewer content={data?.content || ""} />
      </div>
    </div>
  );
}

export default function UiuxGallery({ allArtifacts }) {
  const components = latestByFile(allArtifacts);

  if (components.length === 0) return null;

  return (
    <div className="mt-6 pt-4 border-t border-gray-100">
      <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wide mb-3">Components ({components.length})</h3>
      <div className="flex flex-col gap-3">
        {components.map((artifact) => (
          <ComponentCard key={artifact.artifact_id} artifact={artifact} />
        ))}
      </div>
    </div>
  );
}
