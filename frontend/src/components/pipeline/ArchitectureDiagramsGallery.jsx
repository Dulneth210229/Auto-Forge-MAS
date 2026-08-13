import { useState } from "react";
import { artifactContentUrl, artifactDownloadUrl } from "../../api/client";
import ImageViewer from "../artifacts/ImageViewer";
import Modal from "../common/Modal";
import ZoomableImage from "../common/ZoomableImage";

const DIAGRAM_TYPES = [
  ["use_case_diagram", "Use Case Diagram"],
  ["sequence_diagram", "Sequence Diagram"],
  ["class_diagram", "Class Diagram"],
];

function latestByVersion(versions) {
  return versions.length ? versions.reduce((best, a) => (a.version > best.version ? a : best), versions[0]) : null;
}

// Diagrams are separate artifacts from architecture_plan JSON (not embedded in it) -- previously
// they were rendered stacked at the very end of the plan document, requiring a long scroll to
// find them. A tab switcher shows one at a time (matching how a reviewer actually looks at
// diagrams -- one at a time, not all three competing for attention at once), and clicking one
// opens it full-size in a lightbox for closer inspection.
//
// Diagrams no longer have their own approve/reject controls (they're excluded from "All
// Artifacts"/Governance entirely -- see ResultTab.jsx's UNLISTED_ARTIFACT_TYPES) -- approving the
// Architecture Plan cascades approval to them automatically on the backend. This gallery is now
// their ONLY viewing surface, which is also why a "Download PUML source" link was added here:
// removing diagrams from the generic artifact list would otherwise have made the raw .puml source
// unreachable.
export default function ArchitectureDiagramsGallery({ allArtifacts }) {
  const available = DIAGRAM_TYPES.map(([type, label]) => {
    const pngVersions = allArtifacts.filter((a) => a.artifact_type === type && a.artifact_format === "png");
    const latest = latestByVersion(pngVersions);
    if (!latest) return null;
    const pumlVersions = allArtifacts.filter((a) => a.artifact_type === type && a.artifact_format === "text");
    const pumlArtifact = latestByVersion(pumlVersions);
    return { type, label, artifact: latest, pumlArtifact };
  }).filter(Boolean);

  const [activeType, setActiveType] = useState(available[0]?.type ?? null);
  const [lightbox, setLightbox] = useState(null);

  if (available.length === 0) return null;

  const active = available.find((d) => d.type === activeType) || available[0];

  return (
    <div className="mt-6 pt-4 border-t border-gray-100 dark:border-gray-800">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">Diagrams</h3>
        <div className="flex gap-1">
          {available.map((d) => (
            <button
              key={d.type}
              onClick={() => setActiveType(d.type)}
              className={`text-xs font-semibold px-3 py-1.5 rounded-md ${
                active.type === d.type
                  ? "bg-accent-100 dark:bg-accent-500/15 text-accent-800 dark:text-accent-300"
                  : "text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5"
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            v{active.artifact.version} &middot; click the diagram to zoom
          </p>
          <div className="flex items-center gap-3">
            <a href={artifactDownloadUrl(active.artifact.artifact_id)} className="text-xs text-accent-600 dark:text-accent-400 hover:text-accent-800 dark:hover:text-accent-300 font-semibold">
              Download
            </a>
            {active.pumlArtifact && (
              <a
                href={artifactDownloadUrl(active.pumlArtifact.artifact_id)}
                className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 font-semibold"
              >
                Download PUML source
              </a>
            )}
          </div>
        </div>
        <button onClick={() => setLightbox(active)} className="block w-full cursor-zoom-in">
          <ImageViewer artifactId={active.artifact.artifact_id} alt={active.label} boxHeight="480px" />
        </button>
      </div>

      <Modal
        open={Boolean(lightbox)}
        onClose={() => setLightbox(null)}
        title={lightbox?.label || ""}
        size="xl"
        bodyClassName="overflow-hidden"
      >
        {lightbox && (
          <ZoomableImage src={artifactContentUrl(lightbox.artifact.artifact_id)} alt={lightbox.label} className="h-[75vh]" />
        )}
      </Modal>
    </div>
  );
}
