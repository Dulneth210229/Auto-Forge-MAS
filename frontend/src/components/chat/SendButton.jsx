// Up-arrow send button, circular, matching the reference composer's send affordance. Shared by
// every composer in the app (ChatPanel's normal composer and ChatComposerBox, which the
// Requirement Agent's conversational reply box also uses) so "send" always looks and behaves
// identically regardless of which agent/flow is active.
export default function SendButton({ disabled, pending }) {
  return (
    <button
      type="submit"
      disabled={disabled}
      className="w-8 h-8 rounded-full bg-accent-600 hover:bg-accent-700 disabled:opacity-30 disabled:cursor-not-allowed text-white flex items-center justify-center flex-shrink-0 transition-colors"
      title="Send"
    >
      {pending ? (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
        </svg>
      ) : (
        <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
          <path
            fillRule="evenodd"
            d="M10 17a.75.75 0 01-.75-.75V5.612L5.29 9.77a.75.75 0 01-1.08-1.04l5.25-5.5a.75.75 0 011.08 0l5.25 5.5a.75.75 0 11-1.08 1.04l-3.96-4.158V16.25A.75.75 0 0110 17z"
            clipRule="evenodd"
          />
        </svg>
      )}
    </button>
  );
}
