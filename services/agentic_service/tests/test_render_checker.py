"""
Real, Docker+Playwright-backed tests for the Coder Agent's runtime-render
checker (app/agents/coder_agent/render_checker.py). No mocking of Docker or
Playwright here -- this is infra-level (like test_coder_verify.py's real
npm-install/boot/build tests), proving the actual mechanism works: serving
a real built client/dist via vite preview in a container with a published
port, and a real host-side Playwright browser navigating to it.
"""

import os
import shutil
import stat

import pytest

from app.agents.coder_agent.render_checker import check_runtime_render
from app.services.in_memory_store import store
from app.services.sandbox_service import sandbox_service
from app.services.workspace_service import workspace_service
from app.utils.id_generator import generate_id


def _remove_readonly(func, path, _exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


@pytest.fixture
def built_project():
    """
    A real throwaway project with the client actually built (vite build),
    so there's a real client/dist for vite preview to serve.
    """
    project_id = generate_id("project")
    store.projects[project_id] = {"project_id": project_id, "project_name": f"Render Test {project_id}"}
    workspace_service.ensure_project_repo(project_id)

    install_result = sandbox_service.run_command(project_id, "npm install", cwd="client", timeout=180)
    assert install_result["exit_code"] == 0, install_result["stderr"]

    build_result = sandbox_service.run_command(project_id, "npm run build", cwd="client", timeout=180)
    assert build_result["exit_code"] == 0, build_result["stderr"]

    yield project_id

    repo_path = workspace_service.get_repo_path(project_id)
    workspace_service.ensure_project_repo(project_id).close()
    store.database["projects"].delete_one({"project_id": project_id})
    shutil.rmtree(repo_path.parent, onerror=_remove_readonly)


def test_home_page_renders_cleanly_on_untouched_scaffold(built_project):
    result = check_runtime_render(built_project, reachable_routes=[])

    assert result["home_page"]["status"] == "passed"
    assert result["feature_pages"] == []


def test_check_runtime_render_works_when_called_from_a_running_event_loop(built_project):
    """
    Reproduces a real bug found running CoderAgent.revise() end-to-end:
    check_runtime_render's real caller (verify(), called synchronously from
    inside CoderAgent.run()/revise(), both async, without its own thread)
    always executes with an asyncio event loop already running on that
    thread. Playwright's sync API raises if used directly on such a thread
    -- every real coding attempt failed "home page render" with "Playwright
    Sync API inside the asyncio loop" before this was fixed (running the
    check's Playwright work in its own dedicated worker thread internally).
    A plain synchronous call, like the test above, does not exercise this at
    all -- calling it directly (not via asyncio.to_thread, which would
    already dodge the bug) from inside a running coroutine is what
    reproduces the exact real call pattern.
    """
    import asyncio

    async def _drive():
        return check_runtime_render(built_project, [])  # called directly, not awaited/threaded

    result = asyncio.run(_drive())

    assert result["home_page"]["status"] == "passed"


def test_sandbox_background_service_publishes_a_reachable_port(built_project):
    service = sandbox_service.start_background_service(
        project_id=built_project,
        command="npx vite preview --host 0.0.0.0 --port 4173",
        cwd="client",
        container_port=4173,
    )
    try:
        assert isinstance(service["host_port"], int)
        assert service["host_port"] > 0

        import urllib.request

        for _ in range(20):
            try:
                response = urllib.request.urlopen(f"http://localhost:{service['host_port']}", timeout=2)
                assert response.status == 200
                break
            except Exception:
                import time

                time.sleep(1)
        else:
            pytest.fail("vite preview never became reachable on the published host port")
    finally:
        sandbox_service.stop_background_service(service["container"])
