"""
Sandbox / shell execution service.

The Coder Agent (and later Security/QA agents) need to run real shell commands
(npm install, npm run build, npm test, npm audit, ...) against a project's
generated codebase. This must never run directly on the host: it runs inside a
disposable Docker container with the project's workspace bind-mounted.

This service never raises for a failed *command* -- a nonzero exit code, a
build failure, or a timeout are all returned as data ({exit_code, stdout,
stderr}) so an agentic loop can read the failure and try to self-correct.
Only setup problems (e.g. Docker itself unreachable) raise, since there is
nothing an agent loop could do about that.
"""

from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException

from app.services.workspace_service import workspace_service

SANDBOX_IMAGE = "node:20-slim"
DEFAULT_TIMEOUT_SECONDS = 120


class SandboxService:
    """
    Runs shell commands for a project inside a disposable, isolated container.
    """

    def __init__(self, image: str = SANDBOX_IMAGE):
        self.image = image

    def run_command(
        self,
        project_id: str,
        command: str,
        cwd: str = ".",
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        """
        Run `command` inside a fresh container with the project's workspace
        mounted read-write at /workspace.

        Returns {"exit_code": int, "stdout": str, "stderr": str}. Never raises
        for command failure or timeout.
        """
        repo_path = workspace_service.get_repo_path(project_id)
        repo_path.mkdir(parents=True, exist_ok=True)

        working_dir = "/workspace" if cwd in (".", "") else f"/workspace/{cwd.lstrip('/')}"

        try:
            client = docker.from_env()
        except DockerException as error:
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": f"Sandbox unavailable: could not reach Docker daemon: {error}",
            }

        container = None

        try:
            container = client.containers.run(
                self.image,
                command=["sh", "-c", command],
                working_dir=working_dir,
                volumes={str(Path(repo_path).resolve()): {"bind": "/workspace", "mode": "rw"}},
                mem_limit="1g",
                detach=True,
            )

            try:
                result = container.wait(timeout=timeout)
                exit_code = result.get("StatusCode", 1)
                timed_out = False
            except Exception:
                container.kill()
                exit_code = 124  # conventional timeout exit code
                timed_out = True

            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

            if timed_out:
                stderr = (stderr + f"\n[sandbox] command timed out after {timeout}s").strip()

            return {"exit_code": exit_code, "stdout": stdout, "stderr": stderr}

        except DockerException as error:
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": f"Sandbox execution error: {error}",
            }

        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except DockerException:
                    pass


sandbox_service = SandboxService()
