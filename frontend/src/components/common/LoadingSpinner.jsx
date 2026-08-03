// The 3D rotating-cube loader from https://uiverse.io/AqFox/young-dragon-29 (see index.css's
// .cube-loader for the actual animation/geometry) -- reserved for the output section specifically
// (variant="cube"), per direct user feedback that it shouldn't appear everywhere. Every other
// loading state in the app (chat activity, page loads, feature/artifact lists, settings, etc.)
// keeps the original plain spin icon, the default when `variant` is omitted.
function PlainSpinner() {
  return (
    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  );
}

function CubeSpinner({ size }) {
  return (
    <div className="cube-loader" style={{ "--cube-size": `${size}px` }}>
      <div />
      <div />
      <div />
      <div />
      <div />
      <div />
    </div>
  );
}

export default function LoadingSpinner({ label = "Loading...", variant = "default", size = 28 }) {
  return (
    <div className="flex items-center gap-3 text-gray-500 dark:text-gray-400 py-4">
      {variant === "cube" ? <CubeSpinner size={size} /> : <PlainSpinner />}
      <span>{label}</span>
    </div>
  );
}
