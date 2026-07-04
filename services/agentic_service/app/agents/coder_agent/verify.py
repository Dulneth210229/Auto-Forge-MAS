"""
Coder Agent verifier.

Purpose:
After the agentic coding loop believes it's done, do not trust its self-report
-- run real, sandboxed commands and report exactly what happened. This is
deterministic code: it decides what to run by reading package.json, not by
asking an LLM.

Step semantics: a script that doesn't exist in package.json is "skipped", not
a failure -- a project with no build/lint/test tooling configured yet (e.g.
its very first feature) cannot be held to a check it was never given the
means to pass. A script that exists and returns nonzero, or `npm install`
itself failing, is a hard failure.
"""

from __future__ import annotations

import json
from typing import Any

from app.services.sandbox_service import sandbox_service
from app.services.workspace_service import workspace_service

INSTALL_TIMEOUT_SECONDS = 180
SCRIPT_TIMEOUT_SECONDS = 120


class CoderVerifier:
    """
    Runs the deterministic build/lint/test gate for a coding-loop attempt.
    """

    def verify(self, project_id: str, code_plan_json: dict[str, Any]) -> dict[str, Any]:
        """
        Returns {"passed": bool, "steps": [{"name", "status", "output"}]}.
        status is one of "passed", "failed", "skipped".
        """
        scripts = self._read_package_scripts(project_id)
        steps: list[dict[str, str]] = []
        passed = True

        if code_plan_json.get("new_dependencies"):
            step = self._run_step(project_id, "npm install", "npm install", timeout=INSTALL_TIMEOUT_SECONDS)
        else:
            step = {
                "name": "npm install",
                "status": "skipped",
                "output": "code_plan_json.new_dependencies is empty -- nothing new to install.",
            }
        steps.append(step)
        passed = passed and step["status"] != "failed"

        for script_name in ["build", "lint", "test"]:
            display_name = f"npm run {script_name}"

            if script_name not in scripts:
                steps.append(
                    {
                        "name": display_name,
                        "status": "skipped",
                        "output": f"No \"{script_name}\" script configured in package.json.",
                    }
                )
                continue

            command = "npm test" if script_name == "test" else f"npm run {script_name}"
            step = self._run_step(project_id, display_name, command, timeout=SCRIPT_TIMEOUT_SECONDS)
            steps.append(step)
            passed = passed and step["status"] != "failed"

        return {"passed": passed, "steps": steps}

    def _read_package_scripts(self, project_id: str) -> dict[str, str]:
        package_json_path = workspace_service.get_repo_path(project_id) / "package.json"

        if not package_json_path.exists():
            return {}

        try:
            data = json.loads(package_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

        scripts = data.get("scripts", {})
        return scripts if isinstance(scripts, dict) else {}

    def _run_step(self, project_id: str, name: str, command: str, timeout: int) -> dict[str, str]:
        result = sandbox_service.run_command(project_id=project_id, command=command, timeout=timeout)

        status = "passed" if result["exit_code"] == 0 else "failed"
        output = f"exit_code: {result['exit_code']}\nstdout:\n{result['stdout']}\nstderr:\n{result['stderr']}"

        return {"name": name, "status": status, "output": output}


coder_verifier = CoderVerifier()
