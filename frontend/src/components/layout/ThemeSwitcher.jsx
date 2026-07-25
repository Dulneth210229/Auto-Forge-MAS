import { useEffect, useRef, useState } from "react";
import { applyTheme, loadSavedTheme, saveTheme, THEME_PRESETS } from "../../lib/theme";

export default function ThemeSwitcher() {
  const [current, setCurrent] = useState(loadSavedTheme());
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    applyTheme(current);
  }, [current]);

  useEffect(() => {
    function handleClickOutside(event) {
      if (ref.current && !ref.current.contains(event.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function choose(themeKey) {
    setCurrent(themeKey);
    saveTheme(themeKey);
    setOpen(false);
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        title="Change color theme"
        className="w-7 h-7 rounded-full border-2 border-white shadow ring-1 ring-gray-200"
        style={{ backgroundColor: THEME_PRESETS[current].swatch }}
      />
      {open && (
        <div className="absolute right-0 mt-2 bg-white border border-gray-200 rounded-lg shadow-lg p-2 z-20 w-40">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-wide px-1 pb-1">Theme</p>
          <div className="flex flex-col gap-0.5">
            {Object.entries(THEME_PRESETS).map(([key, preset]) => (
              <button
                key={key}
                onClick={() => choose(key)}
                className="flex items-center gap-2 px-1.5 py-1.5 rounded hover:bg-gray-50 text-sm text-gray-700"
              >
                <span className="w-4 h-4 rounded-full flex-shrink-0" style={{ backgroundColor: preset.swatch }} />
                {preset.label}
                {key === current && <span className="ml-auto text-xs text-gray-400">&#10003;</span>}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
