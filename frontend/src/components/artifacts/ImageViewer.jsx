import { artifactContentUrl } from "../../api/client";

export default function ImageViewer({ artifactId, alt }) {
  return (
    <img src={artifactContentUrl(artifactId)} alt={alt || "Artifact preview"} className="max-w-full rounded border border-gray-200" />
  );
}
