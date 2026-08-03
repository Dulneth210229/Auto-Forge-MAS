import { useState } from "react";
import { useRunArchitecture } from "../../hooks/useAgentMutations";
import ErrorBanner from "../common/ErrorBanner";

export default function ArchitectureRunForm({ featureId }) {
  const [useEnhancedSrs, setUseEnhancedSrs] = useState(true);
  const [architectureNotes, setArchitectureNotes] = useState("");
  const [humanComment, setHumanComment] = useState("");
  const runArchitecture = useRunArchitecture(featureId);

  async function handleSubmit(event) {
    event.preventDefault();
    await runArchitecture.mutateAsync({
      use_enhanced_srs_if_available: useEnhancedSrs,
      architecture_notes: architectureNotes.trim() || null,
      human_comment: humanComment.trim() || null,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4 bg-white dark:bg-gray-900 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800">
      <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">Run Architecture Agent</h3>

      <ErrorBanner error={runArchitecture.error} fallback="Architecture Agent run failed." />

      <label className="flex items-center gap-2 text-sm text-gray-900 dark:text-gray-200">
        <input
          type="checkbox"
          checked={useEnhancedSrs}
          onChange={(e) => setUseEnhancedSrs(e.target.checked)}
        />
        Use approved Enhanced SRS if available
      </label>

      <div>
        <label className="block text-sm font-semibold mb-1 text-gray-900 dark:text-gray-200">Architecture Notes (optional)</label>
        <textarea
          value={architectureNotes}
          onChange={(e) => setArchitectureNotes(e.target.value)}
          rows={2}
          placeholder="Keep it simple: a single Item resource with standard CRUD REST endpoints."
          className="w-full p-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-white/5 dark:text-gray-100 rounded-md focus:outline-none focus:border-accent-500"
        />
      </div>

      <div>
        <label className="block text-sm font-semibold mb-1 text-gray-900 dark:text-gray-200">Human Comment (optional)</label>
        <textarea
          value={humanComment}
          onChange={(e) => setHumanComment(e.target.value)}
          rows={2}
          className="w-full p-2 text-sm border border-gray-300 dark:border-gray-600 dark:bg-white/5 dark:text-gray-100 rounded-md focus:outline-none focus:border-accent-500"
        />
      </div>

      <button
        type="submit"
        disabled={runArchitecture.isPending}
        className="self-start bg-accent-600 hover:bg-accent-700 disabled:opacity-50 text-white font-semibold py-2 px-4 rounded"
      >
        {runArchitecture.isPending ? "Generating Architecture Plan..." : "Run Architecture Agent"}
      </button>
    </form>
  );
}
