"""
Coder Agent verifier.

Purpose:
After the agentic coding loop believes it's done, do not trust its self-report
-- run real, sandboxed commands and report exactly what happened. This is
deterministic code: it decides what to run by reading package.json, not by
asking an LLM.

The project's server/ and client/ folders are a deterministic, always-present
scaffold (see workspace_service.SCAFFOLD_FILES) -- a real Express app and a
real Vite+React app, not something the LLM has to invent. That means, unlike
before this scaffold existed, "does the app actually run" is something this
verifier can and must prove for every feature, not just an optional script
that may or may not have been configured:
  - npm install in server/ and client/ (their package.json always exist).
  - server boot smoke test: start the real Express server in the sandbox,
    hit its /api/health route, and confirm it responds -- a hard failure
    here means the backend genuinely does not start.
  - client build smoke test: `npm run build` in client/ via Vite -- a hard
    failure here means the frontend does not compile.
lint/test remain skip-if-absent: no lint/test tooling is scaffolded yet, and
holding a feature to a check it has no way to pass would be meaningless.

Two more steps close a real gap the checks above can't: booting and building
prove the app *runs*, but prove nothing about whether the plan's specific
endpoints were actually implemented (route_checker.check_route_coverage,
a hard gate) versus left as unreachable/placeholder logic
(route_checker.scan_for_placeholder_stubs, informational only -- see that
module's docstring for why it never gates passed).

A further gate closes the frontend mirror of that same gap: a page can
compile and have a registered route while still being unreachable by a
human, because nothing links to it (nav_checker.check_page_reachability,
a hard gate -- confirmed real bug: every feature built so far added a
`<Route>` but never a `<Link>`, so the app's home page never changed no
matter what was actually built).

One last check closes the gap neither static check above can: a page can
compile, have a registered route, AND be linked, while still crashing at
runtime (e.g. an undefined prop access) -- render_checker.check_runtime_render
serves the already-built client and loads each reachable page in a real
browser. The home page failing is a hard gate (cheap, no data dependency,
exactly what was silently broken project-wide); feature pages are checked
too but only reported informationally, since their rendering can
legitimately vary with backend data state.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.coder_agent.nav_checker import check_page_reachability
from app.agents.coder_agent.render_checker import RenderCheckError, check_runtime_render
from app.agents.coder_agent.route_checker import check_route_coverage, scan_for_placeholder_stubs
from app.services.sandbox_service import sandbox_service
from app.services.workspace_service import workspace_service

INSTALL_TIMEOUT_SECONDS = 180
SCRIPT_TIMEOUT_SECONDS = 120
SERVER_BOOT_TIMEOUT_SECONDS = 45
CLIENT_BUILD_TIMEOUT_SECONDS = 180

_HEALTH_CHECK_JS = (
    "fetch('http://localhost:5000/api/health')"
    ".then(r => process.exit(r.ok ? 0 : 1))"
    ".catch(() => process.exit(1))"
)

# node:20-slim has no curl (see CLAUDE.md's git-binary gotcha for the same
# root cause: the -slim image is intentionally minimal) -- use Node's own
# native fetch (stable since Node 18) instead, so this never depends on a
# tool that may not be in the sandbox image.
# 30 retries at 1s apart (up to ~30s, within the 45s container timeout) --
# widened from an earlier 10-attempt/~10s window after a real run showed a
# false-negative failure under heavy concurrent Docker load (a separate,
# simultaneous test suite run competing for the same daemon): the server had
# actually printed its "listening" line, but the health-check loop gave up
# before a delayed container got scheduled enough CPU to answer the request.
SERVER_BOOT_SMOKE_TEST_COMMAND = (
    "node src/server.js & "
    "SERVER_PID=$!; "
    "STATUS=1; "
    "for i in $(seq 1 30); do "
    f'  if node -e "{_HEALTH_CHECK_JS}"; then STATUS=0; break; fi; '
    "  sleep 1; "
    "done; "
    "kill $SERVER_PID 2>/dev/null; "
    "exit $STATUS"
)


class CoderVerifier:
    """
    Runs the deterministic build/lint/test + runnability gate for a coding-loop attempt.
    """

    def verify(self, project_id: str, feature_id: str, code_plan_json: dict[str, Any]) -> dict[str, Any]:
        """
        Returns {"passed": bool, "steps": [{"name", "status", "output"}]}.
        status is one of "passed", "failed", "skipped" (and, for the
        placeholder-stub scan only, "info" -- a status that never affects
        `passed`).
        """
        steps: list[dict[str, str]] = []
        passed = True

        for label, cwd in [("server", "server"), ("client", "client")]:
            step = self._run_step(
                project_id,
                f"npm install ({label})",
                "npm install",
                cwd=cwd,
                timeout=INSTALL_TIMEOUT_SECONDS,
            )
            steps.append(step)
            passed = passed and step["status"] != "failed"

        server_boot_step = self._run_step(
            project_id,
            "server boot (curl /api/health)",
            SERVER_BOOT_SMOKE_TEST_COMMAND,
            cwd="server",
            timeout=SERVER_BOOT_TIMEOUT_SECONDS,
        )
        steps.append(server_boot_step)
        passed = passed and server_boot_step["status"] != "failed"

        client_build_step = self._run_step(
            project_id,
            "client build (vite build)",
            "npm run build",
            cwd="client",
            timeout=CLIENT_BUILD_TIMEOUT_SECONDS,
        )
        steps.append(client_build_step)
        passed = passed and client_build_step["status"] != "failed"

        root_scripts = self._read_package_scripts(project_id, cwd=".")
        for script_name in ["lint", "test"]:
            display_name = f"npm run {script_name} (root)"

            if script_name not in root_scripts:
                steps.append(
                    {
                        "name": display_name,
                        "status": "skipped",
                        "output": f"No \"{script_name}\" script configured in the root package.json.",
                    }
                )
                continue

            command = "npm test" if script_name == "test" else f"npm run {script_name}"
            step = self._run_step(project_id, display_name, command, cwd=".", timeout=SCRIPT_TIMEOUT_SECONDS)
            steps.append(step)
            passed = passed and step["status"] != "failed"

        workspace_root = workspace_service.get_repo_path(project_id)
        touched = workspace_service.get_touched_files(project_id, feature_id)
        touched_paths = sorted(
            set(touched["added"]) | set(touched["modified"]) | set(touched["deleted"])
        )

        route_coverage_step = self._build_route_coverage_step(workspace_root, code_plan_json)
        steps.append(route_coverage_step)
        passed = passed and route_coverage_step["status"] != "failed"

        page_reachability_results = check_page_reachability(workspace_root)
        page_reachability_step = self._build_page_reachability_step(page_reachability_results)
        steps.append(page_reachability_step)
        passed = passed and page_reachability_step["status"] != "failed"

        if client_build_step["status"] == "passed":
            reachable_routes = [
                item["route"] for item in page_reachability_results if item["status"] == "reachable"
            ]
            home_page_step, feature_page_step = self._build_runtime_render_steps(project_id, reachable_routes)
        else:
            skip_output = "Skipped because the client did not build successfully."
            home_page_step = {"name": "home page render", "status": "skipped", "output": skip_output}
            feature_page_step = {"name": "feature page render", "status": "skipped", "output": skip_output}

        steps.append(home_page_step)
        steps.append(feature_page_step)
        passed = passed and home_page_step["status"] != "failed"

        steps.append(self._build_placeholder_stub_step(workspace_root, touched_paths))

        return {"passed": passed, "steps": steps}

    def _build_route_coverage_step(self, workspace_root, code_plan_json: dict[str, Any]) -> dict[str, str]:
        results = check_route_coverage(workspace_root, code_plan_json)
        missing = [item for item in results if item["status"] == "missing"]

        if not results:
            return {
                "name": "endpoint route coverage",
                "status": "passed",
                "output": "No planned backend files with endpoint maps_to entries to check.",
            }

        if missing:
            lines = [f"- {item['endpoint']} (expected in {item['file']})" for item in missing]
            return {
                "name": "endpoint route coverage",
                "status": "failed",
                "output": "These planned endpoints have no matching route registration found:\n"
                + "\n".join(lines),
            }

        return {
            "name": "endpoint route coverage",
            "status": "passed",
            "output": f"All {len(results)} planned endpoint(s) have a matching route registration.",
        }

    def _build_page_reachability_step(self, results: list[dict[str, str]]) -> dict[str, str]:
        unreachable = [item for item in results if item["status"] == "unreachable"]

        if not results:
            return {
                "name": "page reachability",
                "status": "passed",
                "output": "No non-root page routes registered yet to check.",
            }

        if unreachable:
            lines = [f"- {item['route']}" for item in unreachable]
            return {
                "name": "page reachability",
                "status": "failed",
                "output": "These pages have no way to reach them by clicking from \"/\":\n"
                + "\n".join(lines),
            }

        return {
            "name": "page reachability",
            "status": "passed",
            "output": f"All {len(results)} registered page route(s) are reachable from \"/\".",
        }

    def _build_runtime_render_steps(
        self, project_id: str, reachable_routes: list[str]
    ) -> tuple[dict[str, str], dict[str, str]]:
        try:
            result = check_runtime_render(project_id, reachable_routes)
        except RenderCheckError as error:
            home_page_step = {"name": "home page render", "status": "failed", "output": str(error)}
            feature_page_step = {
                "name": "feature page render",
                "status": "info",
                "output": "Skipped: the runtime-render check's preview server never became reachable, "
                "so feature pages could not be checked either.",
            }
            return home_page_step, feature_page_step

        home_page_step = {
            "name": "home page render",
            "status": result["home_page"]["status"],
            "output": result["home_page"]["output"],
        }

        feature_pages = result["feature_pages"]

        if not feature_pages:
            feature_page_step = {
                "name": "feature page render",
                "status": "info",
                "output": "No reachable feature pages to check.",
            }
        else:
            failed_pages = [item for item in feature_pages if item["status"] == "failed"]
            lines = [f"- {item['route']}: {item['output']}" for item in feature_pages]
            summary = (
                f"{len(failed_pages)} of {len(feature_pages)} feature page(s) had rendering issues "
                "(does not fail verification, review before approving):\n"
                if failed_pages
                else f"All {len(feature_pages)} feature page(s) rendered cleanly:\n"
            )
            feature_page_step = {
                "name": "feature page render",
                "status": "info",
                "output": summary + "\n".join(lines),
            }

        return home_page_step, feature_page_step

    def _build_placeholder_stub_step(self, workspace_root, touched_paths: list[str]) -> dict[str, str]:
        findings = scan_for_placeholder_stubs(workspace_root, touched_paths)

        if not findings:
            return {
                "name": "placeholder-stub scan",
                "status": "info",
                "output": "None found.",
            }

        lines = [f"- {item['file']}:{item['line']}: {item['snippet']}" for item in findings]
        return {
            "name": "placeholder-stub scan",
            "status": "info",
            "output": "Found possible placeholder/stub logic (does not fail verification, "
            "review before approving):\n" + "\n".join(lines),
        }

    def _read_package_scripts(self, project_id: str, cwd: str) -> dict[str, str]:
        package_json_path = workspace_service.get_repo_path(project_id)
        if cwd not in (".", ""):
            package_json_path = package_json_path / cwd
        package_json_path = package_json_path / "package.json"

        if not package_json_path.exists():
            return {}

        try:
            data = json.loads(package_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

        scripts = data.get("scripts", {})
        return scripts if isinstance(scripts, dict) else {}

    def _run_step(self, project_id: str, name: str, command: str, cwd: str, timeout: int) -> dict[str, str]:
        result = sandbox_service.run_command(project_id=project_id, command=command, cwd=cwd, timeout=timeout)

        status = "passed" if result["exit_code"] == 0 else "failed"
        output = f"exit_code: {result['exit_code']}\nstdout:\n{result['stdout']}\nstderr:\n{result['stderr']}"

        return {"name": name, "status": status, "output": output}


coder_verifier = CoderVerifier()
