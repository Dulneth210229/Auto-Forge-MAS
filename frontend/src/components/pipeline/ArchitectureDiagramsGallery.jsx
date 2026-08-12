import { useState } from "react";
import { artifactDownloadUrl } from "../../api/client";
import ImageViewer from "../artifacts/ImageViewer";
import Modal from "../common/Modal";

const DIAGRAM_TYPES = [
  ["use_case_diagram", "Use Case Diagram"],
  ["sequence_diagram", "Sequence Diagram"],
  ["class_diagram", "Class Diagram"],
];

// Diagrams are separate artifacts from architecture_plan JSON (not embedded in it) -- previously
// they were rendered stacked at the very end of the plan document, requiring a long scroll to
// find them. A tab switcher shows one at a time (matching how a reviewer actually looks at
// diagrams -- one at a time, not all three competing for attention at once), and clicking one
// opens it full-size in a lightbox for closer inspection.
export default function ArchitectureDiagramsGallery({ allArtifacts }) {
  const available = DIAGRAM_TYPES.map(([type, label]) => {
    const versions = allArtifacts.filter((a) => a.artifact_type === type && a.artifact_format === "png");
    if (versions.length === 0) return null;
    const latest = versions.reduce((best, a) => (a.version > best.version ? a : best), versions[0]);
    return { type, label, artifact: latest };
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
            v{active.artifact.version} &middot; click the diagram to view full-size
          </p>
          <a href={artifactDownloadUrl(active.artifact.artifact_id)} className="text-xs text-accent-600 dark:text-accent-400 hover:text-accent-800 dark:hover:text-accent-300 font-semibold">
            Download
          </a>
        </div>
        <button onClick={() => setLightbox(active)} className="block w-full cursor-zoom-in">
          <ImageViewer artifactId={active.artifact.artifact_id} alt={active.label} boxHeight="480px" />
        </button>
      </div>

      <Modal open={Boolean(lightbox)} onClose={() => setLightbox(null)} title={lightbox?.label || ""} size="xl">
        {lightbox && <ImageViewer artifactId={lightbox.artifact.artifact_id} alt={lightbox.label} boxHeight="75vh" />}
      </Modal>
    </div>
  );
}
