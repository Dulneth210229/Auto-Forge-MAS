import { useState } from "react";
import { PencilIcon } from "../pipeline/RequirementConversationParts";

// Highlight version of a plain bullet list (see DocumentValue's own string-array rendering) for
// SRS sections that have no per-item id/object to hang a domain-agent origin flag on (scope,
// out_of_scope, constraints, risks, dependencies, data_requirements, etc.) -- unlike
// EnrichedItemList's FR/NFR/AC/VR items, a plain string can't carry its own "origin" field, so a
// domain-added entry is identified by exact-text match against the sibling Domain Improvements
// artifact's own recorded additions (see SrsDocumentViewer's buildHighlightedTextsBySection).
// Same green "Added by Domain Agent" color convention as EnrichedItemList/DomainImprovementsViewer
// so the same meaning reads the same way everywhere in the app -- plain-list sections never get a
// "modified" state (there's no original text to diff against once a string is edited in place).
function Citation({ citation }) {
  if (!citation) return null;
  return (
    <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1 italic">
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

// This field is documented as list[str], but a real, confirmed LLM generation mimicked the
// ID-tagged {id, description} shape FR/NFR/AC/VR items use (schema drift, not a display-layer
// bug) -- rendering the raw object as a JSX child crashes the whole page ("Objects are not
// valid as a React child"). Extracts a displayable string regardless of which shape actually
// arrived, so a schema violation degrades to "shows the text" instead of a hard crash.
function itemText(item) {
  if (typeof item === "string") return item;
  if (item && typeof item === "object") {
    if (typeof item.description === "string") return item.description;
    if (typeof item.text === "string") return item.text;
    if (typeof item.value === "string") return item.value;
    try {
      return JSON.stringify(item);
    } catch {
      return String(item);
    }
  }
  return String(item ?? "");
}

function EditControls({ text, field, onEdit }) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(text);

  if (isEditing) {
    return (
      <div className="mt-1">
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          autoFocus
          rows={Math.min(6, Math.max(2, draft.split("\n").length))}
          className="w-full text-sm bg-white dark:bg-gray-900 border border-accent-400 dark:border-accent-500 rounded-md p-2 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-accent-500 resize-none"
        />
        <div className="flex items-center justify-end gap-2 mt-1.5">
          <button
            type="button"
            onClick={() => {
              setDraft(text);
              setIsEditing(false);
            }}
            className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 font-semibold px-2 py-1"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => {
              const trimmed = draft.trim();
              setIsEditing(false);
              if (!trimmed || trimmed === text) return;
              onEdit({ action: "modify", field, target: text, value: trimmed });
            }}
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
    <div className="flex items-center gap-3 mt-1 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
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
        onClick={() => onEdit({ action: "remove", field, target: text })}
        title="Remove"
        className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500 hover:text-red-600 dark:hover:text-red-400"
      >
        <TrashIcon /> Remove
      </button>
    </div>
  );
}

function AddRow({ field, onEdit }) {
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
    <div className="rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-2.5">
      <textarea
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        autoFocus
        placeholder="Describe the new entry..."
        rows={2}
        className="w-full text-sm bg-white dark:bg-gray-900 border border-accent-400 dark:border-accent-500 rounded-md p-2 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-accent-500 resize-none"
      />
      <div className="flex items-center justify-end gap-2 mt-1.5">
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

export default function EnrichedPlainList({ items, highlighted, field, canEdit, onEdit }) {
  if (!Array.isArray(items) || items.length === 0) {
    return canEdit && field ? (
      <div className="flex flex-col gap-1.5">
        <p className="text-sm text-gray-400 dark:text-gray-500 italic">None</p>
        <AddRow field={field} onEdit={onEdit} />
      </div>
    ) : (
      <p className="text-sm text-gray-400 dark:text-gray-500 italic">None</p>
    );
  }

  return (
    <div className="flex flex-col gap-1.5">
      {items.map((item, index) => {
        const text = itemText(item);
        const match = highlighted?.get(text);

        if (!match) {
          return (
            <div key={index} className="group pl-3 relative before:content-['\2022'] before:absolute before:left-0 before:text-gray-400">
              <p className="text-sm text-gray-700 dark:text-gray-300">{text}</p>
              {canEdit && field && <EditControls text={text} field={field} onEdit={onEdit} />}
            </div>
          );
        }

        return (
          <div
            key={index}
            className="rounded-lg border border-green-200 dark:border-green-500/30 bg-green-50 dark:bg-green-500/10 p-2.5 group"
          >
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm text-gray-800 dark:text-gray-200">{text}</p>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-green-600 text-white uppercase tracking-wide whitespace-nowrap flex-shrink-0">
                Added by Domain Agent
              </span>
            </div>
            <Citation citation={match.domain_citation} />
            {canEdit && field && <EditControls text={text} field={field} onEdit={onEdit} />}
          </div>
        );
      })}
      {canEdit && field && <AddRow field={field} onEdit={onEdit} />}
    </div>
  );
}
