import { useState } from "react";
import { PencilIcon } from "../pipeline/RequirementConversationParts";

// Renders SRS requirement-like arrays (functional_requirements, non_functional_requirements,
// acceptance_criteria, validation_rules) as cards instead of a generic table -- specifically so
// Domain Agent enrichment is visually obvious, not buried in a raw field. Real Enhanced SRS data
// marks its own changes: an item with modified_by_domain_agent=true carries the pre-enrichment
// original_description alongside the enriched one; an item with origin="domain_agent" is a whole
// new item the Domain Agent added that never existed in the plain SRS. Color convention matches
// DomainImprovementsViewer (green=addition, blue=modification) so the same meaning reads the same
// way everywhere in the app.
function Citation({ citation }) {
  if (!citation) return null;
  return (
    <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1.5 italic">
      Source: {citation.source_document}
      {citation.chunk_id ? ` (${citation.chunk_id})` : ""}
    </p>
  );
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-3 h-3">
      <path
        fillRule="evenodd"
        d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.808a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
        clipRule="evenodd"
      />
    </svg>
  );
}

// The 3 sections a genuinely empty SRS can't survive (RequirementAgent._validate_stable_ids
// raises if any of these become empty) -- the remove affordance refuses to delete the last
// remaining item in these specifically, so a stray click can't produce an SRS the backend would
// itself reject. validation_rules has no equivalent floor.
const CRITICAL_NON_EMPTY_FIELDS = new Set([
  "functional_requirements", "non_functional_requirements", "acceptance_criteria",
]);

function ItemCard({ item, field, canEdit, canRemove, onEdit }) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(item.description || "");

  const isNew = item.origin === "domain_agent";
  const isModified = Boolean(item.modified_by_domain_agent);

  const colorClasses = isNew
    ? "border-green-200 dark:border-green-500/30 bg-green-50 dark:bg-green-500/10"
    : isModified
      ? "border-blue-200 dark:border-blue-500/30 bg-blue-50 dark:bg-blue-500/10"
      : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900";

  const tags = [item.priority, item.category].filter(Boolean);

  function handleSave() {
    const trimmed = draft.trim();
    setIsEditing(false);
    if (!trimmed || trimmed === item.description) return;
    onEdit({ action: "modify", field, target: item.id, value: trimmed });
  }

  if (isEditing) {
    return (
      <div className={`rounded-lg border p-3 ${colorClasses}`}>
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          autoFocus
          rows={Math.min(8, Math.max(2, draft.split("\n").length))}
          className="w-full text-sm bg-white dark:bg-gray-900 border border-accent-400 dark:border-accent-500 rounded-md p-2 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-accent-500 resize-none"
        />
        <div className="flex items-center justify-end gap-2 mt-2">
          <button
            type="button"
            onClick={() => {
              setDraft(item.description || "");
              setIsEditing(false);
            }}
            className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 font-semibold px-2 py-1"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={!draft.trim()}
            className="text-xs bg-accent-600 hover:bg-accent-700 disabled:opacity-50 text-white font-semibold px-3 py-1 rounded-md"
          >
            Save
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`rounded-lg border p-3 group ${colorClasses}`}>
      <div className="flex items-center justify-between gap-2 mb-1">
        <div className="flex items-center gap-2">
          {item.id && <span className="text-xs font-bold text-gray-500 dark:text-gray-400">{item.id}</span>}
          {tags.map((tag) => (
            <span key={tag} className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-300">
              {tag}
            </span>
          ))}
        </div>
        {isNew && (
          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-green-600 text-white uppercase tracking-wide">
            Added by Domain Agent
          </span>
        )}
        {isModified && (
          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-600 text-white uppercase tracking-wide">
            Enhanced by Domain Agent
          </span>
        )}
      </div>

      {isModified && item.original_description && (
        <p className="text-xs text-gray-400 dark:text-gray-500 line-through mb-0.5">{item.original_description}</p>
      )}
      <p className="text-sm text-gray-800 dark:text-gray-200">{item.description}</p>

      <Citation citation={item.domain_citation} />

      {canEdit && (
        <div className="flex items-center gap-3 mt-2 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
          <button
            type="button"
            onClick={() => setIsEditing(true)}
            title="Edit"
            className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500 hover:text-accent-600 dark:hover:text-accent-400"
          >
            <PencilIcon /> Edit
          </button>
          <button
            type="button"
            onClick={() => onEdit({ action: "remove", field, target: item.id })}
            disabled={!canRemove}
            title={canRemove ? "Remove" : "Can't remove the last item in this section"}
            className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500 hover:text-red-600 dark:hover:text-red-400 disabled:opacity-30 disabled:hover:text-gray-400"
          >
            <TrashIcon /> Remove
          </button>
        </div>
      )}
    </div>
  );
}

function AddItemCard({ field, onEdit }) {
  const [isAdding, setIsAdding] = useState(false);
  const [draft, setDraft] = useState("");

  if (!isAdding) {
    return (
      <button
        type="button"
        onClick={() => setIsAdding(true)}
        className="self-start text-xs font-semibold text-accent-600 dark:text-accent-400 hover:text-accent-700 dark:hover:text-accent-300 px-1 py-1"
      >
        + Add
      </button>
    );
  }

  function handleAdd() {
    const trimmed = draft.trim();
    if (trimmed) onEdit({ action: "add", field, value: trimmed });
    setDraft("");
    setIsAdding(false);
  }

  return (
    <div className="rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-3">
      <textarea
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        autoFocus
        placeholder="Describe the new entry..."
        rows={2}
        className="w-full text-sm bg-white dark:bg-gray-900 border border-accent-400 dark:border-accent-500 rounded-md p-2 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-accent-500 resize-none"
      />
      <div className="flex items-center justify-end gap-2 mt-2">
        <button
          type="button"
          onClick={() => {
            setDraft("");
            setIsAdding(false);
          }}
          className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 font-semibold px-2 py-1"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleAdd}
          disabled={!draft.trim()}
          className="text-xs bg-accent-600 hover:bg-accent-700 disabled:opacity-50 text-white font-semibold px-3 py-1 rounded-md"
        >
          Add
        </button>
      </div>
    </div>
  );
}

export default function EnrichedItemList({ items, field, canEdit, onEdit }) {
  if (!Array.isArray(items) || items.length === 0) return null;

  const canRemove = !(CRITICAL_NON_EMPTY_FIELDS.has(field) && items.length <= 1);

  return (
    <div className="flex flex-col gap-2">
      {items.map((item, index) => (
        <ItemCard
          key={item.id || index}
          item={item}
          field={field}
          canEdit={canEdit}
          canRemove={canRemove}
          onEdit={onEdit}
        />
      ))}
      {canEdit && field && <AddItemCard field={field} onEdit={onEdit} />}
    </div>
  );
}
