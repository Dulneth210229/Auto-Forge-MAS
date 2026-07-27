"""
UI/UX Agent preview renderer.

Purpose:
Render one page's generated components into a PNG screenshot for human
review. Mirrors plantuml_service's idiom (deterministic file-in/bytes-out,
raise RuntimeError on failure) -- same pattern, new content type.

Rendering approach:
A static HTML shell mounts the *exact* generated .jsx source (the same text
that gets saved as the approvable artifact) using vendored UMD builds of
React, ReactDOM, and Babel standalone, plus the vendored Tailwind JIT script
-- all read from local files, no network access at render time. This gives a
pixel-faithful render of the literal component source a human approves,
without the cost/fragility of spinning up a per-component Vite dev server
(node_modules install, port management, readiness polling) just to produce a
review screenshot.

Playwright's sync API is used here (like a plain function), and the async
UIUXAgent calls it via asyncio.to_thread -- the sync API cannot run inside an
already-running asyncio event loop.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

VENDOR_DIR = Path(__file__).parent / "vendor"

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="{react_src}"></script>
<script src="{react_dom_src}"></script>
<script src="{babel_src}"></script>
<script src="{tailwind_src}"></script>
</head>
<body>
<div id="root" class="bg-white"></div>
<script type="text/babel">
const {{ useState, useEffect, useMemo, useCallback, useRef, useContext, useReducer }} = React;

{component_definitions}

function __Page() {{
  return (
    <div>
{component_mounts}
    </div>
  );
}}

const __root = ReactDOM.createRoot(document.getElementById('root'));
__root.render(<__Page />);
</script>
</body>
</html>
"""


class PreviewRenderError(RuntimeError):
    """Raised when a page could not be rendered to PNG."""


class UIUXPreviewRenderer:
    """
    Renders a page's components into a single PNG.
    """

    def render_page_png(self, components: list[dict[str, Any]]) -> bytes:
        """
        components: list of {"name": str, "jsx_code": str, "mock_props": dict}
        for every component on one page, in the order they should appear.

        Returns PNG bytes. Raises PreviewRenderError on failure.
        """

        if not components:
            raise PreviewRenderError("Cannot render a page with zero components.")

        html = self._build_html(components)

        with tempfile.TemporaryDirectory() as tmp_dir:
            html_path = Path(tmp_dir) / "preview.html"
            html_path.write_text(html, encoding="utf-8")

            try:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch()
                    try:
                        page = browser.new_page(viewport={"width": 900, "height": 700})

                        # Real testing showed content that renders correctly and quickly in
                        # isolation still occasionally hit Playwright's 30s default action
                        # timeout ("element is not visible") when run as part of the real
                        # pipeline -- Ollama/MongoDB/LangGraph all competing for CPU on modest
                        # hardware starves the browser of the cycles it needs to finish layout,
                        # not a rendering defect in the content itself. A generous default
                        # timeout gives it that headroom instead of failing prematurely under
                        # load. Note: passing timeout= directly to .screenshot() below does NOT
                        # reliably override Playwright's default in this version -- confirmed by
                        # direct testing (a "timeout=8000" call still took the full ~30s) -- only
                        # page.set_default_timeout() actually changes the wait duration.
                        page.set_default_timeout(90000)

                        console_errors: list[str] = []
                        page.on(
                            "console",
                            lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
                        )
                        page.on("pageerror", lambda exc: console_errors.append(f"pageerror: {exc}"))

                        page.goto(html_path.as_uri())
                        page.wait_for_timeout(800)  # allow Babel transform + Tailwind JIT to settle

                        root_locator = page.locator("#root")
                        if root_locator.count() == 0 or not root_locator.first.inner_html().strip():
                            raise PreviewRenderError(
                                "Preview root rendered empty. "
                                f"Browser console errors: {console_errors}"
                            )

                        return root_locator.first.screenshot()
                    finally:
                        browser.close()
            except PreviewRenderError:
                raise
            except Exception as error:
                raise PreviewRenderError(f"Playwright preview rendering failed: {error}") from error

    def _build_html(self, components: list[dict[str, Any]]) -> str:
        component_definitions = []
        component_mounts = []

        for index, component in enumerate(components):
            jsx_code = self._strip_export_default(component["jsx_code"])
            component_name = component["name"]
            mock_props = component.get("mock_props", {})
            mount_var = f"__mockProps{index}"

            component_definitions.append(jsx_code)
            component_definitions.append(
                f"const {mount_var} = {json.dumps(mock_props)};"
            )
            component_mounts.append(f"      <{component_name} {{...{mount_var}}} />")

        return HTML_TEMPLATE.format(
            react_src=self._vendor_uri("react.production.min.js"),
            react_dom_src=self._vendor_uri("react-dom.production.min.js"),
            babel_src=self._vendor_uri("babel.min.js"),
            tailwind_src=self._vendor_uri("tailwindcss.js"),
            component_definitions="\n".join(component_definitions),
            component_mounts="\n".join(component_mounts),
        )

    def _strip_export_default(self, jsx_code: str) -> str:
        """
        The saved artifact uses `export default function X(props) {...}` (real
        ES module syntax, correct for the file the Coder Agent will later
        consume). The preview harness has no module loader, so only the
        export syntax is stripped here -- the component logic is untouched.
        """
        return re.sub(r"^\s*export\s+default\s+", "", jsx_code, count=1)

    def _vendor_uri(self, filename: str) -> str:
        path = VENDOR_DIR / filename

        if not path.exists():
            raise PreviewRenderError(f"Vendored preview asset not found: {path}")

        return path.resolve().as_uri()


uiux_preview_renderer = UIUXPreviewRenderer()
