"""
Coder Agent runtime-render checker.

Purpose:
Prove that pages the Coder Agent's client build produces actually render
without crashing when loaded in a real browser -- not just that they
compile (verify.py's `client build` step) and are linked
(nav_checker.check_page_reachability). Neither of those static checks can
catch a page that is reachable and compiles cleanly but throws at runtime
(e.g. an undefined prop access) -- this closes that gap.

Deliberately NOT a live dev-server + iterate-until-correct loop (that
approach was evaluated and rejected -- see CLAUDE.md for the full
reasoning: no reliable domain-agnostic way to judge "does this look right"
beyond what this check already does, real added cost per coding attempt,
and it would inherit this project's already-documented Docker-contention
flakiness). Instead:
- Serves the ALREADY-BUILT client/dist output via `vite preview` (correctly
  handles client-side SPA routing, unlike a bare static file server, which
  would 404 on any path but "/") -- no extra build, reuses what verify.py's
  `client build` step already produced.
- One-shot check per verify() call, not a retry loop.
- Uses Playwright's sync API (same dependency and calling convention as
  uiux_agent/preview_renderer.py) from the HOST process to navigate to each
  page and check for zero `pageerror` events and non-empty rendered
  content -- the same minimal bar preview_renderer.py already uses.

Gate strictness (decided, not this module's concern to enforce -- verify.py
wires the result up this way): the home page failing is a hard gate (cheap,
no data dependency, exactly the thing that was silently broken project-wide
before nav_checker/render_checker existed). Feature pages are checked too
but reported informationally only, since their rendering can legitimately
vary with backend data state (e.g. an empty list before any data exists).
"""

from __future__ import annotations

import concurrent.futures
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from app.services.sandbox_service import sandbox_service

VITE_PREVIEW_CONTAINER_PORT = 4173
VITE_PREVIEW_COMMAND = f"npx vite preview --host 0.0.0.0 --port {VITE_PREVIEW_CONTAINER_PORT}"
READINESS_POLL_ATTEMPTS = 20
READINESS_POLL_INTERVAL_SECONDS = 1


class RenderCheckError(Exception):
    """Raised when the runtime-render check itself could not run (infra failure, not a page defect)."""


def check_runtime_render(project_id: str, reachable_routes: list[str]) -> dict[str, Any]:
    """
    Serves the built client/dist output and checks the home page plus every
    given route for JS errors / empty rendering.

    reachable_routes: routes already proven reachable by nav_checker (only
    those are worth checking here -- an unreachable route's render state
    isn't actionable for a human anyway).

    Returns:
        {
            "home_page": {"status": "passed"|"failed", "output": str},
            "feature_pages": [{"route": str, "status": "passed"|"failed", "output": str}, ...],
        }

    Raises RenderCheckError if the preview server itself never became
    reachable (an infra problem, distinct from a page rendering badly).

    Runs the actual check in a dedicated worker thread. Playwright's sync
    API (used here, and by preview_renderer.py) refuses to run on any thread
    with an already-running asyncio event loop -- and this function's real
    caller, CoderAgent.run()/revise(), is itself async, invoked from a sync
    graph node via asyncio.run(...) (see CLAUDE.md deviation #13), so an
    event loop genuinely is running on the calling thread for every real
    invocation. Confirmed directly: a standalone sync script calling this
    (no event loop) worked fine, while the real end-to-end revise() run hit
    "Playwright Sync API inside the asyncio loop" and failed every attempt.
    A fresh worker thread has no event loop of its own, sidestepping this
    regardless of the caller's context, with no change to this function's
    signature or its callers.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(_check_runtime_render_on_worker_thread, project_id, reachable_routes).result()


def _check_runtime_render_on_worker_thread(project_id: str, reachable_routes: list[str]) -> dict[str, Any]:
    service = sandbox_service.start_background_service(
        project_id=project_id,
        command=VITE_PREVIEW_COMMAND,
        cwd="client",
        container_port=VITE_PREVIEW_CONTAINER_PORT,
    )
    host_port = service["host_port"]
    container = service["container"]

    try:
        base_url = f"http://localhost:{host_port}"
        _wait_until_ready(base_url)

        home_result = _check_page(base_url, "/")
        feature_results = [
            {"route": route, **_check_page(base_url, route)} for route in reachable_routes if route != "/"
        ]

        return {"home_page": home_result, "feature_pages": feature_results}

    finally:
        sandbox_service.stop_background_service(container)


def _wait_until_ready(base_url: str) -> None:
    for _ in range(READINESS_POLL_ATTEMPTS):
        try:
            urllib.request.urlopen(base_url, timeout=2)
            return
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(READINESS_POLL_INTERVAL_SECONDS)

    raise RenderCheckError(
        f"vite preview never became reachable at {base_url} after "
        f"{READINESS_POLL_ATTEMPTS * READINESS_POLL_INTERVAL_SECONDS}s."
    )


def _check_page(base_url: str, route: str) -> dict[str, str]:
    url = base_url + route

    console_errors: list[str] = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                page.on(
                    "console",
                    lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
                )
                page.on("pageerror", lambda exc: console_errors.append(f"pageerror: {exc}"))

                page.goto(url, timeout=15_000)
                page.wait_for_timeout(500)

                root_locator = page.locator("#root")
                root_is_empty = root_locator.count() == 0 or not root_locator.first.inner_html().strip()
            finally:
                browser.close()
    except Exception as error:
        return {"status": "failed", "output": f"Failed to load {route}: {error}"}

    if console_errors:
        return {
            "status": "failed",
            "output": f"{route} rendered with JS errors: {console_errors}",
        }

    if root_is_empty:
        return {"status": "failed", "output": f"{route} rendered an empty root element."}

    return {"status": "passed", "output": f"{route} rendered with no JS errors and non-empty content."}
