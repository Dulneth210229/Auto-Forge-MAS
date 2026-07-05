"""
Unit tests for CoderVerifier -- exercised against a real throwaway git repo
(built via the real workspace_service scaffold, so server/ and client/ are
real Express/Vite projects) and the real sandbox_service (Docker), no LLM
involved.

Confirms: npm install runs for both server/ and client/ regardless of
code_plan_json (their package.json always exist thanks to the scaffold), the
server-boot and client-build smoke tests are hard failures/passes (not
skippable), and lint/test remain skip-if-absent since no such tooling is
scaffolded.
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
    """
    Yields (project_id, feature_id) with a real feature branch already
    checked out -- verify() now also computes touched files via
    workspace_service.get_touched_files, which requires a real feature
    branch to exist (mirrors CoderAgent.run()'s actual call order: plan ->
    start_feature_branch -> code -> verify).
    """
    project_id = generate_id("project")
    feature_id = generate_id("feature")
    store.projects[project_id] = {"project_id": project_id, "project_name": f"Verify Test {project_id}"}
    store.features[feature_id] = {
        "project_id": project_id,
        "feature_id": feature_id,
        "feature_name": "Verify Test Feature",
    }
    workspace_service.start_feature_branch(project_id, feature_id)

    yield project_id, feature_id

    repo_path = workspace_service.get_repo_path(project_id)
    workspace_service.ensure_project_repo(project_id).close()  # release Windows file handles
    store.database["projects"].delete_one({"project_id": project_id})
    store.database["features"].delete_one({"feature_id": feature_id})
    shutil.rmtree(repo_path.parent, onerror=_remove_readonly)


@pytest.fixture
def verifier():
    return CoderVerifier()


def test_verify_runs_npm_install_for_both_server_and_client(verifier, project):
    project_id, feature_id = project
    result = verifier.verify(project_id, feature_id, {"new_dependencies": []})
    statuses = {s["name"]: s["status"] for s in result["steps"]}

    assert statuses["npm install (server)"] == "passed"
    assert statuses["npm install (client)"] == "passed"


def test_verify_server_boots_and_responds_to_health_check(verifier, project):
    project_id, feature_id = project
    result = verifier.verify(project_id, feature_id, {"new_dependencies": []})
    statuses = {s["name"]: s["status"] for s in result["steps"]}

    assert statuses["server boot (curl /api/health)"] == "passed"


def test_verify_client_builds_successfully(verifier, project):
    project_id, feature_id = project
    result = verifier.verify(project_id, feature_id, {"new_dependencies": []})
    statuses = {s["name"]: s["status"] for s in result["steps"]}

    assert statuses["client build (vite build)"] == "passed"


def test_verify_passes_end_to_end_on_untouched_scaffold(verifier, project):
    project_id, feature_id = project
    result = verifier.verify(project_id, feature_id, {"new_dependencies": []})
    assert result["passed"] is True


def test_missing_root_lint_and_test_scripts_are_skipped_not_failed(verifier, project):
    # The scaffold's root package.json has no lint/test scripts configured.
    project_id, feature_id = project
    result = verifier.verify(project_id, feature_id, {"new_dependencies": []})

    statuses = {s["name"]: s["status"] for s in result["steps"]}
    assert statuses["npm run lint (root)"] == "skipped"
    assert statuses["npm run test (root)"] == "skipped"


def test_broken_server_boot_is_a_hard_failure(verifier, project):
    project_id, feature_id = project
    server_app_path = workspace_service.get_repo_path(project_id) / "server" / "src" / "app.js"
    server_app_path.write_text("throw new Error('intentionally broken for this test');", encoding="utf-8")

    result = verifier.verify(project_id, feature_id, {"new_dependencies": []})
    statuses = {s["name"]: s["status"] for s in result["steps"]}

    assert statuses["server boot (curl /api/health)"] == "failed"
    assert result["passed"] is False


def test_endpoint_route_coverage_passes_with_no_endpoint_plan(verifier, project):
    project_id, feature_id = project
    result = verifier.verify(project_id, feature_id, {"new_dependencies": []})
    statuses = {s["name"]: s["status"] for s in result["steps"]}

    assert statuses["endpoint route coverage"] == "passed"


def test_endpoint_route_coverage_fails_on_missing_route(verifier, project):
    project_id, feature_id = project
    code_plan_json = {
        "files": [
            {
                "path": "server/src/routes/never_written.routes.js",
                "action": "create",
                "maps_to": ["/api/widgets"],
            }
        ]
    }

    result = verifier.verify(project_id, feature_id, code_plan_json)
    statuses = {s["name"]: s["status"] for s in result["steps"]}

    assert statuses["endpoint route coverage"] == "failed"
    assert result["passed"] is False


def test_placeholder_stub_scan_is_informational_and_never_fails(verifier, project):
    project_id, feature_id = project
    stub_path = workspace_service.get_repo_path(project_id) / "server" / "src" / "routes" / "stub.routes.js"
    stub_path.parent.mkdir(parents=True, exist_ok=True)
    stub_path.write_text("// In a real app, you would send an email here\n", encoding="utf-8")

    result = verifier.verify(project_id, feature_id, {"new_dependencies": []})
    statuses = {s["name"]: s["status"] for s in result["steps"]}

    assert statuses["placeholder-stub scan"] == "info"
    assert result["passed"] is True
