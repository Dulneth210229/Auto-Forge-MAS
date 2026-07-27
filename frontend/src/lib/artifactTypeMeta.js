// Human-readable labels for ArtifactType values (see app/core/enums.py).
export const ARTIFACT_TYPE_LABELS = {
  srs: "SRS",
  enhanced_srs: "Enhanced SRS",
  domain_improvements: "Domain Improvements",
  architecture_plan: "Architecture Plan",
  sds: "SDS (legacy)",
  use_case_diagram: "Use Case Diagram",
  sequence_diagram: "Sequence Diagram",
  class_diagram: "Class Diagram",
  architecture_traceability: "Architecture Traceability",
  ui_metadata: "UI Metadata",
  ui_integration_manifest: "UI Integration Manifest",
  ui_component_code: "Component Code",
  ui_preview_screenshot: "Preview Screenshot",
  design_system: "Design System",
  code_plan: "Code Plan",
  code_diff: "Code Diff",
  code_manifest: "Code Manifest",
  requirement_code_map: "Requirement Code Map",
  setup_instructions: "Setup Instructions",
  project_manifest: "Project Manifest",
  security_report: "Security Report",
  qa_report: "QA Report",
};

// Which stage each artifact_type belongs to, for grouping in ArtifactList.
export const ARTIFACT_TYPE_STAGE = {
  srs: "requirement",
  enhanced_srs: "domain",
  domain_improvements: "domain",
  architecture_plan: "architecture",
  sds: "architecture",
  use_case_diagram: "architecture",
  sequence_diagram: "architecture",
  class_diagram: "architecture",
  architecture_traceability: "architecture",
  ui_metadata: "uiux",
  ui_integration_manifest: "uiux",
  ui_component_code: "uiux",
  ui_preview_screenshot: "uiux",
  code_plan: "coder",
  code_diff: "coder",
  code_manifest: "coder",
  requirement_code_map: "coder",
  setup_instructions: "coder",
};

// The single (artifact_type, artifact_format) pair that gates each stage's approval --
// approving/rejecting THIS specific artifact is what the graph actually reacts to (see
// approval_service.py's resume()). Format matters: every agent saves a JSON+Markdown pair at
// the same version, and the JSON copy is always the one the pipeline keys off of -- EXCEPT
// Coder Agent's code_diff, which only ever exists as Markdown (there is no JSON code_diff).
export const STAGE_GATING_ARTIFACT = {
  requirement: { type: "srs", format: "json" },
  domain: { type: "enhanced_srs", format: "json" },
  architecture: { type: "architecture_plan", format: "json" },
  uiux: { type: "ui_metadata", format: "json" },
  coder: { type: "code_diff", format: "markdown" },
};

// Back-compat plain type map, still useful for "which stage does this artifact_type belong
// to" checks that don't care about the gating nuance above.
export const STAGE_GATING_ARTIFACT_TYPE = Object.fromEntries(
  Object.entries(STAGE_GATING_ARTIFACT).map(([stage, { type }]) => [stage, type])
);

// artifact_type -> dedicated document viewer key, for JSON content that should render as a real
// formatted document rather than a raw tree. SrsDocumentViewer covers both srs and enhanced_srs
// (they share one shape); sds is Architecture Plan's legacy type name (same shape as
// architecture_plan).
const DOCUMENT_VIEWER_TYPES = {
  srs: "srs-document",
  enhanced_srs: "srs-document",
  architecture_plan: "architecture-document",
  sds: "architecture-document",
  domain_improvements: "domain-improvements-document",
  ui_metadata: "ui-metadata-document",
};

export function pickViewer(artifact) {
  if (artifact.artifact_format === "png") return "image";
  // code_diff exists in BOTH formats: the markdown one is the real merge report DiffViewer
  // parses (prose + a fenced diff block); the json one is just a {added, modified, deleted}
  // file-tree summary with no diff text at all -- routing it through DiffViewer showed the raw
  // JSON as if it were prose, with a permanent "No diff content found" underneath. Format still
  // decides the viewer for that one; only markdown code_diff gets the dedicated DiffViewer.
  if (artifact.artifact_type === "code_diff" && artifact.artifact_format === "markdown") return "diff";
  if (artifact.artifact_format === "json" && DOCUMENT_VIEWER_TYPES[artifact.artifact_type]) {
    return DOCUMENT_VIEWER_TYPES[artifact.artifact_type];
  }
  if (artifact.artifact_format === "markdown") return "markdown";
  if (artifact.artifact_format === "json") return "json";
  if (artifact.artifact_format === "code") return "code";
  return "raw";
}
