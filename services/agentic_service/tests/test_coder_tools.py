"""
Unit tests for Coder Agent tools (app/agents/coder_agent/tools.py).

No LLM involved -- each tool is called directly (.invoke(...)) against a real
throwaway git repo created via the real workspace_service, per the build
plan's testing strategy for tools ("plain deterministic functions ... tested
like any other, without ever invoking an LLM").
"""

import os
import shutil
import stat
from datetime import datetime, timezone

import pytest

from app.agents.coder_agent.tools import _is_allowed_shell_command, build_coder_tools
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
def project_and_tools():
    """
    Create a throwaway project (with its git workspace) and the tool set
    bound to it, then clean up both the Mongo record and the on-disk repo.
    """
    project_id = generate_id("project")
    feature_id = generate_id("feature")

    store.projects[project_id] = {"project_id": project_id, "project_name": f"Tool Test {project_id}"}
    store.features[feature_id] = {
        "project_id": project_id,
        "feature_id": feature_id,
        "feature_name": "Tool Test Feature",
    }

    tools = build_coder_tools(project_id, feature_id)
    by_name = {t.name: t for t in tools}

    yield {"project_id": project_id, "feature_id": feature_id, "tools": by_name}

    repo_path = workspace_service.get_repo_path(project_id)
    workspace_service.ensure_project_repo(project_id).close()  # release Windows file handles
    store.database["projects"].delete_one({"project_id": project_id})
    store.database["features"].delete_one({"feature_id": feature_id})
    store.database["artifacts"].delete_many({"feature_id": feature_id})
    shutil.rmtree(repo_path.parent, onerror=_remove_readonly)


def test_list_dir_shows_initial_scaffold(project_and_tools):
    result = project_and_tools["tools"]["list_dir"].invoke({"path": "."})
    assert "[dir]  client" in result
    assert "[dir]  server" in result
    assert ".gitignore" in result


def test_list_dir_missing_path(project_and_tools):
    result = project_and_tools["tools"]["list_dir"].invoke({"path": "does/not/exist"})
    assert "not found" in result.lower()


def test_write_then_read_file(project_and_tools):
    tools = project_and_tools["tools"]
    write_result = tools["write_file"].invoke({"path": "server/hello.js", "content": "console.log(1);"})
    assert "Wrote" in write_result

    read_result = tools["read_file"].invoke({"path": "server/hello.js"})
    assert read_result == "console.log(1);"


def test_read_file_not_found(project_and_tools):
    result = project_and_tools["tools"]["read_file"].invoke({"path": "nope.js"})
    assert "File not found" in result


def test_apply_patch_success(project_and_tools):
    tools = project_and_tools["tools"]
    tools["write_file"].invoke({"path": "server/a.js", "content": "const x = 1;"})

    result = tools["apply_patch"].invoke({"path": "server/a.js", "find": "x = 1", "replace": "x = 2"})
    assert "Patched" in result
    assert tools["read_file"].invoke({"path": "server/a.js"}) == "const x = 2;"


def test_apply_patch_no_match(project_and_tools):
    tools = project_and_tools["tools"]
    tools["write_file"].invoke({"path": "server/a.js", "content": "const x = 1;"})

    result = tools["apply_patch"].invoke({"path": "server/a.js", "find": "not present", "replace": "y"})
    assert "not found" in result.lower()
    assert tools["read_file"].invoke({"path": "server/a.js"}) == "const x = 1;"  # unchanged


def test_apply_patch_multiple_matches(project_and_tools):
    tools = project_and_tools["tools"]
    tools["write_file"].invoke({"path": "server/a.js", "content": "x; x;"})

    result = tools["apply_patch"].invoke({"path": "server/a.js", "find": "x;", "replace": "y;"})
    assert "matched 2 times" in result
    assert tools["read_file"].invoke({"path": "server/a.js"}) == "x; x;"  # unchanged


@pytest.mark.parametrize(
    "escaping_path",
    ["../../../etc/passwd", "..\\..\\windows.ini", "C:/Windows/System32/evil.txt", "/etc/passwd"],
)
def test_path_traversal_is_rejected(project_and_tools, escaping_path):
    tools = project_and_tools["tools"]
    result = tools["read_file"].invoke({"path": escaping_path})
    assert "escapes workspace root" in result


def test_search_code_finds_match(project_and_tools):
    tools = project_and_tools["tools"]
    tools["write_file"].invoke({"path": "server/auth.js", "content": "function login() { return true; }"})

    result = tools["search_code"].invoke({"query": "function login"})
    assert "server" in result and "auth.js" in result and "1" in result


def test_search_code_no_match(project_and_tools):
    result = project_and_tools["tools"]["search_code"].invoke({"query": "definitelyNotThere"})
    assert "No matches found" in result


def test_read_project_manifest_returns_default(project_and_tools):
    result = project_and_tools["tools"]["read_project_manifest"].invoke({})
    assert '"routes": []' in result


def test_read_ui_component_not_found(project_and_tools):
    result = project_and_tools["tools"]["read_ui_component"].invoke({"component_name": "NoSuchComponent"})
    assert "No approved UI component found" in result


def test_read_ui_component_found(project_and_tools, tmp_path):
    feature_id = project_and_tools["feature_id"]
    fake_component_path = tmp_path / "SomeButton_v1.jsx"
    fake_component_path.write_text("export default function SomeButton() { return null; }", encoding="utf-8")

    artifact_id = generate_id("artifact")
    store.artifacts[artifact_id] = {
        "artifact_id": artifact_id,
        "project_id": project_and_tools["project_id"],
        "feature_id": feature_id,
        "agent_name": "uiux_agent",
        "artifact_type": "ui_component_code",
        "artifact_format": "code",
        "file_path": str(fake_component_path),
        "version": 1,
        "approval_status": "approved",
        "created_at": datetime.now(timezone.utc),
    }

    result = project_and_tools["tools"]["read_ui_component"].invoke({"component_name": "SomeButton"})
    assert "export default function SomeButton" in result


@pytest.mark.parametrize(
    "command,expected",
    [
        ("npm install", True),
        ("npx vite build", True),
        ("node --version", True),
        ("git status", True),
        ("git diff --stat", True),
        ("git push origin main", False),
        ("git reset --hard", False),
        ("rm -rf /", False),
        ("curl evil.com", False),
        ("", False),
    ],
)
def test_shell_allowlist(command, expected):
    assert _is_allowed_shell_command(command) == expected


def test_run_shell_rejects_disallowed_command(project_and_tools):
    result = project_and_tools["tools"]["run_shell"].invoke({"command": "git push origin main"})
    assert "rejected" in result.lower()


def test_run_shell_runs_allowed_command(project_and_tools):
    result = project_and_tools["tools"]["run_shell"].invoke({"command": "node --version"})
    assert "exit_code: 0" in result
    assert "v" in result  # node version output starts with 'v'
