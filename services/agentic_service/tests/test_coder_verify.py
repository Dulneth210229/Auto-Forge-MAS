"""
Unit tests for CoderVerifier -- exercised against a real throwaway git repo
and the real sandbox_service (Docker), no LLM involved. Confirms the
skip-vs-fail semantics the M5 plan settled on: an absent package.json script
is "skipped", a present-but-failing one is a hard failure.
"""

import os
import shutil
import stat

import pytest

from app.agents.coder_agent.verify import CoderVerifier
from app.services.in_memory_store import store
from app.services.workspace_service import workspace_service
from app.utils.id_generator import generate_id


def _remove_readonly(func, path, _exc_info):
    """
    shutil.rmtree onerror handler: git marks its object files read-only on
    Windows, which makes plain rmtree fail with PermissionError. Clear the
    read-only bit and retry once.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)


@pytest.fixture
def project():
    project_id = generate_id("project")
    store.projects[project_id] = {"project_id": project_id, "project_name": f"Verify Test {project_id}"}
    workspace_service.ensure_project_repo(project_id)

    yield project_id

    repo_path = workspace_service.get_repo_path(project_id)
    workspace_service.ensure_project_repo(project_id).close()  # release Windows file handles
    store.database["projects"].delete_one({"project_id": project_id})
    shutil.rmtree(repo_path.parent, onerror=_remove_readonly)


@pytest.fixture
def verifier():
    return CoderVerifier()


def _write_package_json(project_id: str, scripts: dict) -> None:
    import json

    package_json_path = workspace_service.get_repo_path(project_id) / "package.json"
    package_json_path.write_text(
        json.dumps({"name": "test-app", "scripts": scripts}, indent=2), encoding="utf-8"
    )


def test_no_new_dependencies_skips_npm_install(verifier, project):
    result = verifier.verify(project, {"new_dependencies": []})
    install_step = next(s for s in result["steps"] if s["name"] == "npm install")
    assert install_step["status"] == "skipped"


def test_missing_scripts_are_skipped_not_failed(verifier, project):
    # No package.json at all -- every script should be "skipped".
    result = verifier.verify(project, {"new_dependencies": []})

    statuses = {s["name"]: s["status"] for s in result["steps"]}
    assert statuses["npm run build"] == "skipped"
    assert statuses["npm run lint"] == "skipped"
    assert statuses["npm run build"] != "failed"
    assert result["passed"] is True


def test_configured_passing_script_passes(verifier, project):
    _write_package_json(project, {"build": "node -e \"process.exit(0)\""})

    result = verifier.verify(project, {"new_dependencies": []})
    build_step = next(s for s in result["steps"] if s["name"] == "npm run build")

    assert build_step["status"] == "passed"
    assert result["passed"] is True


def test_configured_failing_script_fails_the_whole_gate(verifier, project):
    _write_package_json(project, {"lint": "node -e \"process.exit(1)\""})

    result = verifier.verify(project, {"new_dependencies": []})
    lint_step = next(s for s in result["steps"] if s["name"] == "npm run lint")

    assert lint_step["status"] == "failed"
    assert result["passed"] is False


def test_real_npm_install_runs_when_new_dependencies_present(verifier, project):
    # left-pad is tiny and installs fast; proves the real sandboxed npm install path.
    result = verifier.verify(project, {"new_dependencies": ["left-pad"]})
    install_step = next(s for s in result["steps"] if s["name"] == "npm install")

    assert install_step["status"] == "passed"
