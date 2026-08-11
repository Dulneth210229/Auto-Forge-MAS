"""
Coder Agent verifier (Next.js).

Purpose:
After the agentic coding loop believes it's done, do not trust its self-report
-- run real, sandboxed commands and report exactly what happened. This is
deterministic code: it decides what to run by reading package.json/
next.config.mjs, not by asking an LLM.

The project's root is a deterministic, always-present Next.js App Router
scaffold (see workspace_service.NEXTJS_SCAFFOLD_FILES) -- a real Next.js app,
not something the LLM has to invent. That means "does the app actually run"
is something this verifier can and must prove for every feature:
  - one root `npm install` (a single package.json now, not a server/client
    split).
  - `next build`: the single build-AND-typecheck gate -- a hard failure here
    means the app does not compile or does not typecheck.
  - server boot smoke test: `next start` on the just-built output, hit
    /api/health, confirm it responds -- a hard failure here means the app
    genuinely does not boot in production mode. Skipped (not run against a
    stale .next) if the build step failed.
  - next.config.mjs integrity: a cheap, deterministic anti-cheat check (grep
    for `ignoreBuildErrors`/`ignoreDuringBuilds`) -- a struggling model's
    easiest escape hatch from a real type/lint error is to suppress it at
    the config level instead of fixing it, so this is a hard gate.
`test` remains skip-if-absent (root package.json only): no test framework is
scaffolded, and holding a feature to a check it has no way to pass would be
meaningless. `lint` is intentionally NOT run as a gate here even though the
scaffold declares a real "lint" script (next lint, with eslint-config-next) --
ESLint's ruleset flags real-but-non-blocking style issues (unused imports,
exhaustive-deps hints) that would make verification fail on cosmetic grounds
for an already-fragile local-model coding loop; a human can still run
`npm run lint` themselves.

Two more steps close a real gap the checks above can't: booting and building
prove the app *runs*, but prove nothing about whether the plan's specific
endpoints were actually implemented (route_checker.check_route_coverage,
a hard gate) versus left as unreachable/placeholder logic
(route_checker.scan_for_placeholder_stubs, informational only -- see that
module's docstring for why it never gates passed).

A further gate closes the frontend mirror of that same gap: a page can
compile and have a file under app/ while still being unreachable by a
human, because nothing links to it (nav_checker.check_page_reachability,
a hard gate -- confirmed real bug, pre-migration: every feature built so far
added a route but never a link, so the app's home page never changed no
matter what was actually built).

One last check closes the gap neither static check above can: a page can
compile, exist under app/, AND be linked, while still crashing at runtime
(e.g. an undefined prop access, a Server Component that throws) --
render_checker.check_runtime_render serves the already-built app via
`next start` and loads each reachable page in a real browser, checking the
real HTTP response status. The home page failing is a hard gate (cheap, no
data dependency, exactly what was silently broken project-wide); feature
pages are checked too but only reported informationally, since their
rendering can legitimately vary with backend data state.

One final, informational-only step (_build_relevance_scan_step) closes a
different gap than any of the above: every other check asks "does the app
still run/build," never "does this diff actually address what the human
asked for." Given the human's own literal request text, it checks how many
distinctive words from that request show up anywhere in the files this
attempt actually touched -- a cheap, deterministic nudge for a human
reviewer when a diff shares suspiciously little vocabulary with the
request, never a hard gate (legitimate diffs routinely use different words
than the request).
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents.coder_agent.db_fallback_checker import (
    check_db_null_guard_coverage,
    scan_for_db_fallback_quality,
)
from app.agents.coder_agent.nav_checker import check_page_reachability
from app.agents.coder_agent.render_checker import RenderCheckError, check_runtime_render
from app.agents.coder_agent.route_checker import check_route_coverage, scan_for_placeholder_stubs
from app.services.sandbox_service import sandbox_service
from app.services.workspace_service import workspace_service

# Widened from 300 -- adding Tailwind CSS's devDependencies (tailwindcss,
# postcss, autoprefixer) to the scaffold pulls in a substantially heavier
# dependency tree (the postcss plugin ecosystem, lightningcss's native
# binary, etc.). Confirmed directly against the real sandbox image/mount
# path (not just a throwaway directory): a clean, genuinely still-
# progressing `npm install` (no error, just more packages to resolve/
# download over a slow Windows-Docker-Desktop bind mount) took as long as
# ~7 minutes end to end -- 300s and even 480s were both too tight and killed
# a real, otherwise-successful install mid-flight. 600s leaves real margin
# above that observed worst case.
INSTALL_TIMEOUT_SECONDS = 600
SCRIPT_TIMEOUT_SECONDS = 120
SERVER_BOOT_TIMEOUT_SECONDS = 60
BUILD_TIMEOUT_SECONDS = 300

_HEALTH_CHECK_JS = (
    "fetch('http://localhost:3000/api/health')"
    ".then(r => process.exit(r.ok ? 0 : 1))"
    ".catch(() => process.exit(1))"
)

# `next start`'s cold start (loading the production server, its route
# manifest, etc.) is slower than the old `node src/server.js` boot -- widened
# retry budget accordingly (50 attempts at 1s apart, within the 60s container
# timeout), matching the same "don't mistake a slow boot for a broken one"
# lesson the MERN-era version already learned once under Docker contention.
SERVER_BOOT_SMOKE_TEST_COMMAND = (
    "npx next start -p 3000 & "
    "SERVER_PID=$!; "
    "STATUS=1; "
    "for i in $(seq 1 50); do "
    f'  if node -e "{_HEALTH_CHECK_JS}"; then STATUS=0; break; fi; '
    "  sleep 1; "
    "done; "
    "kill $SERVER_PID 2>/dev/null; "
    "exit $STATUS"
)

_BUILD_ERROR_SUPPRESSION_FLAGS = [
    ("ignoreBuildErrors", "typescript.ignoreBuildErrors"),
    ("ignoreDuringBuilds", "eslint.ignoreDuringBuilds"),
]


class CoderVerifier:
    """
    Runs the deterministic build/lint/test + runnability gate for a coding-loop attempt.
    """

    def verify(
        self,
        project_id: str,
        feature_id: str,
        code_plan_json: dict[str, Any],
        original_request: str | None = None,
    ) -> dict[str, Any]:
        """
        Returns {"passed": bool, "steps": [{"name", "status", "output"}]}.
        status is one of "passed", "failed", "skipped" (and, for the
        placeholder-stub/db-fallback-quality/relevance scans, "info" -- a
        status that never affects `passed`).

        original_request, when given, is the human's own literal words (the
        human_comment/revision_comment this code_plan_json was generated
        from) -- used only for the informational relevance scan below, never
        for anything that gates `passed`.
        """
        steps: list[dict[str, str]] = []
        passed = True

        workspace_root = workspace_service.get_repo_path(project_id)

        anti_cheat_step = self._build_anti_cheat_step(workspace_root)
        steps.append(anti_cheat_step)
        passed = passed and anti_cheat_step["status"] != "failed"

        install_step = self._run_step(
            project_id, "npm install", "npm install", cwd=".", timeout=INSTALL_TIMEOUT_SECONDS
        )
        steps.append(install_step)
        passed = passed and install_step["status"] != "failed"

        build_step = self._run_step(
            project_id, "next build", "npm run build", cwd=".", timeout=BUILD_TIMEOUT_SECONDS
        )
        steps.append(build_step)
        passed = passed and build_step["status"] != "failed"

        if build_step["status"] == "passed":
            server_boot_step = self._run_step(
                project_id,
                "server boot (next start + /api/health)",
                SERVER_BOOT_SMOKE_TEST_COMMAND,
                cwd=".",
                timeout=SERVER_BOOT_TIMEOUT_SECONDS,
            )
        else:
            server_boot_step = {
                "name": "server boot (next start + /api/health)",
                "status": "skipped",
                "output": "Skipped because `next build` did not succeed -- would run against a stale "
                "or absent .next build.",
            }
        steps.append(server_boot_step)
        passed = passed and server_boot_step["status"] != "failed"

        root_scripts = self._read_package_scripts(project_id, cwd=".")
        for script_name in ["test"]:
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

        touched = workspace_service.get_touched_files(project_id, feature_id)
        touched_paths = sorted(
            set(touched["added"]) | set(touched["modified"]) | set(touched["deleted"])
        )

        route_coverage_step = self._build_route_coverage_step(workspace_root, code_plan_json)
        steps.append(route_coverage_step)
        passed = passed and route_coverage_step["status"] != "failed"

        db_null_guard_step = self._build_db_null_guard_step(workspace_root, code_plan_json)
        steps.append(db_null_guard_step)
        passed = passed and db_null_guard_step["status"] != "failed"

        page_reachability_results = check_page_reachability(workspace_root)
        page_reachability_step = self._build_page_reachability_step(page_reachability_results)
        steps.append(page_reachability_step)
        passed = passed and page_reachability_step["status"] != "failed"

        if build_step["status"] == "passed":
            reachable_routes = [
                item["route"] for item in page_reachability_results if item["status"] == "reachable"
            ]
            home_page_step, feature_page_step = self._build_runtime_render_steps(project_id, reachable_routes)
        else:
            skip_output = "Skipped because the app did not build successfully."
            home_page_step = {"name": "home page render", "status": "skipped", "output": skip_output}
            feature_page_step = {"name": "feature page render", "status": "skipped", "output": skip_output}

        steps.append(home_page_step)
        steps.append(feature_page_step)
        passed = passed and home_page_step["status"] != "failed"

        steps.append(self._build_placeholder_stub_step(workspace_root, touched_paths))
        steps.append(self._build_db_fallback_quality_step(workspace_root, touched_paths))
        steps.append(self._build_relevance_scan_step(workspace_root, touched_paths, original_request))

        return {"passed": passed, "steps": steps}

    def _build_anti_cheat_step(self, workspace_root) -> dict[str, str]:
        next_config_path = workspace_root / "next.config.mjs"

        if not next_config_path.exists():
            return {
                "name": "next.config.mjs integrity",
                "status": "passed",
                "output": "next.config.mjs not found -- nothing to check.",
            }

        try:
            content = next_config_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as error:
            return {
                "name": "next.config.mjs integrity",
                "status": "passed",
                "output": f"Could not read next.config.mjs ({error}) -- skipping.",
            }

        hits = [label for needle, label in _BUILD_ERROR_SUPPRESSION_FLAGS if needle in content]

        if hits:
            return {
                "name": "next.config.mjs integrity",
                "status": "failed",
                "output": "next.config.mjs sets a build-error-suppression flag, which is forbidden "
                "(fix the underlying error instead): " + ", ".join(hits),
            }

        return {
            "name": "next.config.mjs integrity",
            "status": "passed",
            "output": "No build-error-suppression flags found.",
        }

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

    def _build_db_null_guard_step(self, workspace_root, code_plan_json: dict[str, Any]) -> dict[str, str]:
        results = check_db_null_guard_coverage(workspace_root, code_plan_json)

        if not results:
            return {
                "name": "database null-guard coverage",
                "status": "passed",
                "output": "No planned Route Handler calls connectToDatabase() without a null-guard "
                "branch already in place.",
            }

        lines = [f"- {item['file']}" for item in results]
        return {
            "name": "database null-guard coverage",
            "status": "failed",
            "output": "These Route Handlers call connectToDatabase() but have no branch guarding "
            "against a null (no-database-configured) result -- this crashes instead of serving "
            "seed data:\n" + "\n".join(lines),
        }

    def _build_db_fallback_quality_step(self, workspace_root, touched_paths: list[str]) -> dict[str, str]:
        findings = scan_for_db_fallback_quality(workspace_root, touched_paths)

        if not findings:
            return {
                "name": "database fallback quality scan",
                "status": "info",
                "output": "None found.",
            }

        lines = [f"- {item['file']}:{item['line']}: {item['snippet']}" for item in findings]
        return {
            "name": "database fallback quality scan",
            "status": "info",
            "output": "These null-guard branches look like a bare empty/error response rather than "
            "seed data (does not fail verification, review before approving):\n" + "\n".join(lines),
        }

    _RELEVANCE_SCAN_STOPWORDS = {
        "the", "and", "for", "with", "that", "this", "from", "into", "also",
        "have", "has", "was", "were", "are", "you", "your", "please", "make",
        "makes", "should", "would", "could", "add", "adds", "added", "remove",
        "removes", "removed", "change", "changes", "changed", "update",
        "updates", "updated", "fix", "fixes", "fixed", "code", "page", "app",
        "application", "feature", "does", "not", "did", "will", "some",
        "these", "those", "them", "they", "which", "when", "then", "than",
    }

    def _build_relevance_scan_step(
        self, workspace_root, touched_paths: list[str], original_request: str | None
    ) -> dict[str, str]:
        """
        Cheap, deterministic, informational-only signal that a diff might not
        actually address what was asked -- extracts meaningful words from the
        human's own literal request and checks how many of them show up
        anywhere in the touched files' current content. Deliberately never a
        hard gate: legitimate diffs routinely use different words than the
        request phrased things in (e.g. "add the footer back" -> a diff full
        of `<Footer />`/`export function Footer`, sharing only "footer"), so
        this can only ever be a nudge for a human reviewer, never a rejection.
        """
        if not original_request or not original_request.strip():
            return {
                "name": "request relevance scan",
                "status": "info",
                "output": "No original request text available to compare against.",
            }

        words = {
            token
            for token in re.findall(r"[a-zA-Z]{4,}", original_request.lower())
            if token not in self._RELEVANCE_SCAN_STOPWORDS
        }
        if not words:
            return {
                "name": "request relevance scan",
                "status": "info",
                "output": "Request text had no distinctive words to check for.",
            }

        content_parts: list[str] = []
        for relative_path in touched_paths:
            file_path = workspace_root / relative_path
            if not file_path.is_file():
                continue
            try:
                content_parts.append(file_path.read_text(encoding="utf-8", errors="ignore").lower())
            except OSError:
                continue
        combined_content = "\n".join(content_parts)

        matched = {word for word in words if word in combined_content}
        overlap_ratio = len(matched) / len(words)

        if not touched_paths:
            return {
                "name": "request relevance scan",
                "status": "info",
                "output": "No files were touched this attempt -- nothing to compare against the "
                "request.",
            }

        if overlap_ratio < 0.2 and len(words) >= 3:
            return {
                "name": "request relevance scan",
                "status": "info",
                "output": (
                    "This diff shares few or no words with your request -- please double-check "
                    "it actually addresses what you asked. Distinctive request words not found "
                    "in any touched file: " + ", ".join(sorted(words - matched))
                ),
            }

        return {
            "name": "request relevance scan",
            "status": "info",
            "output": f"{len(matched)}/{len(words)} distinctive request word(s) found in the touched "
            "files.",
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
