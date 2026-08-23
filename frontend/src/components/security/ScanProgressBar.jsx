// A real, live percentage progress bar for the AI-model deep scan -- direct user request. Kept
// as a small, separate component (rather than folded into SecurityReportView.jsx's own header)
// since it's rendered from both that component's empty-state and populated-state branches.
// Deliberately NOT the existing LiveGenerationView (isFinalizing mode, used elsewhere for a
// non-streamable tail) -- that swaps the ENTIRE view away, which would hide the version dropdown
// and the "Continue to QA Agent"/"Fix Vulnerabilities" buttons next to it; this renders inline,
// alongside everything else, instead.
export default function ScanProgressBar({ progress, phaseLabel, onStop }) {
  const percent = progress?.percent ?? 0;

  return (
    <div className="flex flex-col gap-1.5 rounded-lg border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-500/10 px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-indigo-800 dark:text-indigo-300">
          {phaseLabel || "Starting AI model scan..."}
        </p>
        <div className="flex items-center gap-3 flex-shrink-0">
          {progress && (
            <span className="text-xs font-mono text-indigo-700 dark:text-indigo-400">{percent}%</span>
          )}
          <button
            type="button"
            onClick={onStop}
            className="text-xs font-semibold text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300"
          >
            Stop Scan
          </button>
        </div>
      </div>
      <div className="h-2 w-full bg-indigo-200 dark:bg-indigo-500/20 rounded-full overflow-hidden">
        <div
          className="h-full bg-indigo-600 dark:bg-indigo-400 rounded-full transition-all duration-300"
          style={{ width: `${progress ? percent : 8}%` }}
        />
      </div>
    </div>
  );
}
