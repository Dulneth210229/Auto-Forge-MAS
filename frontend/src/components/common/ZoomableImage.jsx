import { TransformWrapper, TransformComponent, useControls } from "react-zoom-pan-pinch";

// Small on-screen control cluster -- must render INSIDE <TransformWrapper> since useControls()
// needs its context. Bottom-right, semi-transparent, matching this app's existing dark-mode-aware
// button conventions -- a reviewer may not know wheel-zoom/drag-pan/double-click gestures exist.
function ZoomControls() {
  const { zoomIn, zoomOut, resetTransform } = useControls();

  return (
    <div className="absolute bottom-3 right-3 z-10 flex items-center gap-1 bg-white/90 dark:bg-gray-900/90 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm p-1">
      <button
        type="button"
        onClick={() => zoomOut()}
        title="Zoom out"
        className="w-7 h-7 flex items-center justify-center rounded text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/10 text-lg font-bold leading-none"
      >
        &minus;
      </button>
      <button
        type="button"
        onClick={() => resetTransform()}
        title="Reset zoom"
        className="w-7 h-7 flex items-center justify-center rounded text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/10 text-xs font-semibold"
      >
        1:1
      </button>
      <button
        type="button"
        onClick={() => zoomIn()}
        title="Zoom in"
        className="w-7 h-7 flex items-center justify-center rounded text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/10 text-lg font-bold leading-none"
      >
        +
      </button>
    </div>
  );
}

// Generic zoom/pan wrapper -- takes a raw `src`, not an artifact id, so it has zero coupling to
// artifact-fetching concerns and is reusable anywhere an image needs to be zoomable (e.g. the
// UI/UX Agent's page-preview screenshots later), not just Architecture diagrams.
export default function ZoomableImage({ src, alt, className }) {
  return (
    <div className={`relative w-full h-full bg-gray-50 dark:bg-gray-950 rounded overflow-hidden ${className || ""}`}>
      <TransformWrapper
        initialScale={1}
        minScale={0.5}
        maxScale={6}
        wheel={{ step: 0.15 }}
        pinch={{ step: 5 }}
        doubleClick={{ mode: "toggle" }}
        limitToBounds
      >
        <ZoomControls />
        <TransformComponent
          wrapperStyle={{ width: "100%", height: "100%" }}
          contentStyle={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}
        >
          <img src={src} alt={alt || "Diagram"} className="max-w-full max-h-full object-contain" />
        </TransformComponent>
      </TransformWrapper>
    </div>
  );
}
