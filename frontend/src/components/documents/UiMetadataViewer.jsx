// ui_metadata is the UI/UX Agent's page/component plan -- real shape confirmed against generated
// artifacts: { pages: [{page_id, name, route, actors[], covers_requirements[], layout_regions[],
// components[{name, reused_from_design_system, new_component_justification, covers_ui_expectations[],
// props}], states[]}], notes }. Rendered as real page cards instead of a raw JSON tree.
function Chip({ children, tone = "gray" }) {
  const tones = {
    gray: "bg-gray-100 text-gray-600",
    accent: "bg-accent-50 text-accent-700",
    blue: "bg-blue-50 text-blue-700",
  };
  return <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${tones[tone]}`}>{children}</span>;
}

function ChipGroup({ label, items, tone }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="mb-3">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <Chip key={item} tone={tone}>
            {item}
          </Chip>
        ))}
      </div>
    </div>
  );
}

function ComponentRow({ component }) {
  const reused = Boolean(component.reused_from_design_system);
  const props = component.props && typeof component.props === "object" ? Object.entries(component.props) : [];

  return (
    <div className={`rounded-lg border p-3 ${reused ? "border-accent-200 bg-accent-50" : "border-gray-200 bg-white"}`}>
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-bold text-gray-900">{component.name}</p>
        <span
          className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wide flex-shrink-0 ${
            reused ? "bg-accent-600 text-white" : "bg-gray-200 text-gray-600"
          }`}
        >
          {reused ? "Reused" : "New"}
        </span>
      </div>

      {!reused && component.new_component_justification && (
        <p className="text-xs text-gray-500 italic mt-1">{component.new_component_justification}</p>
      )}

      {component.covers_ui_expectations?.length > 0 && (
        <ul className="list-disc list-inside text-xs text-gray-600 mt-1.5 space-y-0.5">
          {component.covers_ui_expectations.map((expectation, i) => (
            <li key={i}>{expectation}</li>
          ))}
        </ul>
      )}

      {props.length > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-100 flex flex-col gap-0.5">
          {props.map(([key, value]) => (
            <p key={key} className="text-xs text-gray-600">
              <span className="font-mono font-semibold text-gray-700">{key}</span>: {String(value)}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

function PageCard({ page }) {
  const components = page.components || [];

  return (
    <div className="mb-5 border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-bold text-gray-900">{page.name}</h3>
          {page.route && (
            <code className="text-xs text-accent-700 bg-accent-50 px-2 py-0.5 rounded flex-shrink-0">{page.route}</code>
          )}
        </div>
      </div>

      <div className="p-4">
        <div className="flex flex-wrap gap-4">
          <ChipGroup label="Actors" items={page.actors} tone="blue" />
          <ChipGroup label="Layout Regions" items={page.layout_regions} tone="gray" />
          <ChipGroup label="States" items={page.states} tone="gray" />
        </div>
        <ChipGroup label="Covers Requirements" items={page.covers_requirements} tone="accent" />

        {components.length > 0 && (
          <>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 mt-1">
              Components ({components.length})
            </p>
            <div className="flex flex-col gap-2">
              {components.map((component, i) => (
                <ComponentRow key={component.name || i} component={component} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function UiMetadataViewer({ data }) {
  if (!data) return null;

  const pages = data.pages || [];

  return (
    <div className="max-w-3xl">
      <div className="mb-5 pb-3 border-b border-gray-200">
        <p className="text-xs font-bold text-accent-600 uppercase tracking-wide mb-1">UI Metadata</p>
        <h2 className="text-lg font-bold text-gray-900">
          {pages.length} Page{pages.length === 1 ? "" : "s"} Defined
        </h2>
      </div>

      {pages.map((page, i) => (
        <PageCard key={page.page_id || i} page={page} />
      ))}

      {data.notes && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Notes</p>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{data.notes}</p>
        </div>
      )}
    </div>
  );
}
