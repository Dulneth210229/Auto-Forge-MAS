import DocumentValue, { humanizeKey } from "./DocumentValue";

const DESIGN_VIEW_LABELS = {
  context_view: "Context View",
  logical_view: "Logical View",
  interface_view: "Interface View",
  data_view: "Data View",
  behavior_view: "Behavior View",
  error_handling_view: "Error Handling View",
  security_authorization_view: "Security & Authorization View",
  quality_attributes_view: "Quality Attributes View",
};

function Section({ title, value }) {
  if (value === null || value === undefined || (Array.isArray(value) && value.length === 0)) return null;

  return (
    <section className="mb-5">
      <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wide mb-1.5 pb-1 border-b border-gray-100">
        {title}
      </h3>
      <DocumentValue value={value} />
    </section>
  );
}

const KNOWN_TOP_KEYS = [
  "document_control",
  "feature_overview",
  "architecture_approach",
  "design_views",
  "frontend_architecture_plan",
  "backend_architecture_plan",
  "validation_plan",
  "coder_implementation_tasks",
  "implementation_plan",
  "traceability_matrix",
  "assumptions",
  "constraints",
  "risks",
  "dependencies",
  "revision_metadata",
  "human_approval_note",
];

export default function ArchitecturePlanDocumentViewer({ data }) {
  if (!data) return null;

  const docControl = data.document_control || {};
  const extraKeys = Object.keys(data).filter((k) => !KNOWN_TOP_KEYS.includes(k));

  return (
    <div className="max-w-3xl">
      <div className="mb-5 pb-3 border-b border-gray-200">
        <h2 className="text-lg font-bold text-gray-900">
          {docControl.document_title || data.feature_overview?.feature_name || "Architecture Plan"}
        </h2>
        <p className="text-xs text-gray-500 mt-1">
          {[docControl.target_stack, docControl.architecture_style, docControl.version && `v${docControl.version}`.replace("vv", "v")]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </div>

      {data.human_approval_note && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-5 text-sm text-yellow-900">
          <p className="text-xs font-bold uppercase tracking-wide mb-1">Note for reviewer</p>
          {data.human_approval_note}
        </div>
      )}

      <Section title="Feature Overview" value={data.feature_overview} />
      <Section title="Architecture Approach" value={data.architecture_approach} />

      {data.design_views && (
        <section className="mb-5">
          <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wide mb-2 pb-1 border-b border-gray-100">
            Design Views
          </h3>
          <div className="flex flex-col gap-3 pl-1">
            {Object.entries(data.design_views).map(([key, value]) => (
              <div key={key}>
                <p className="text-xs font-bold text-gray-600 mb-1">{DESIGN_VIEW_LABELS[key] || humanizeKey(key)}</p>
                <DocumentValue value={value} />
              </div>
            ))}
          </div>
        </section>
      )}

      {data.implementation_plan && (
        <section className="mb-5">
          <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wide mb-2 pb-1 border-b border-gray-100">
            Implementation Plan
          </h3>
          {data.implementation_plan.backend?.files && (
            <div className="mb-3">
              <p className="text-xs font-bold text-gray-600 mb-1">Backend Files</p>
              <DocumentValue value={data.implementation_plan.backend.files} />
            </div>
          )}
          {data.implementation_plan.frontend?.pages && (
            <div className="mb-3">
              <p className="text-xs font-bold text-gray-600 mb-1">Frontend Pages</p>
              <DocumentValue value={data.implementation_plan.frontend.pages} />
            </div>
          )}
          {data.implementation_plan.frontend?.services && (
            <div className="mb-3">
              <p className="text-xs font-bold text-gray-600 mb-1">Frontend Services</p>
              <DocumentValue value={data.implementation_plan.frontend.services} />
            </div>
          )}
          {data.implementation_plan.implementation_order && (
            <div className="mb-3">
              <p className="text-xs font-bold text-gray-600 mb-1">Implementation Order</p>
              <ol className="list-decimal list-inside text-sm text-gray-700 space-y-1">
                {data.implementation_plan.implementation_order.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </div>
          )}
        </section>
      )}

      <Section title="Traceability Matrix" value={data.traceability_matrix} />
      <Section title="Constraints" value={data.constraints} />
      <Section title="Assumptions" value={data.assumptions} />
      <Section title="Risks" value={data.risks} />
      <Section title="Dependencies" value={data.dependencies} />

      {extraKeys.map((key) => (
        <Section key={key} title={humanizeKey(key)} value={data[key]} />
      ))}
    </div>
  );
}
