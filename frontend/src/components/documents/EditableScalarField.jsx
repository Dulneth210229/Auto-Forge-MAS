import { useState } from "react";
import { PencilIcon } from "../pipeline/RequirementConversationParts";

// Editable counterpart to DocumentValue's plain-text rendering, for the SRS's top-level scalar
// fields (business_goal, architectural_style, target_stack) -- these have no per-item id/list
// shape, so they get their own small in-place editor rather than reusing EnrichedItemList/
// EnrichedPlainList. Same hover-reveal pencil + inline textarea + Cancel/Save pattern used
// throughout this codebase for "edit this text in place."
export default function EditableScalarField({ value, field, canEdit, onEdit }) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(value || "");

  if (isEditing) {
    return (
      <div>
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          autoFocus
          rows={Math.min(6, Math.max(1, draft.split("\n").length))}
          className="w-full text-sm bg-white dark:bg-gray-900 border border-accent-400 dark:border-accent-500 rounded-md p-2 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-accent-500 resize-none"
        />
        <div className="flex items-center justify-end gap-2 mt-1.5">
          <button
            type="button"
            onClick={() => {
              setDraft(value || "");
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
              if (!trimmed || trimmed === (value || "")) return;
              onEdit({ action: "set", field, value: trimmed });
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
    <div className="group">
      <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{value}</p>
      {canEdit && (
        <button
          type="button"
          onClick={() => setIsEditing(true)}
          title="Edit"
          className="flex items-center gap-1 mt-1 text-xs text-gray-400 dark:text-gray-500 hover:text-accent-600 dark:hover:text-accent-400 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
        >
          <PencilIcon /> Edit
        </button>
      )}
    </div>
  );
}
