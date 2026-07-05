"""
Unit tests for workspace_service's deterministic runnable scaffold
(server/ Express app, client/ Vite+React app) and its idempotent backfill
into repos that predate a given scaffold file. No LLM, no Docker -- these
only assert on-disk file presence/content and git history, not runnability
(verify.py's tests cover the real npm-install/boot/build proof).
"""

import os
import shutil
import stat

import pytest

from app.services.in_memory_store import store
from app.services.workspace_service import (
    SCAFFOLD_FILES,
    _LEGACY_SERVER_APP_JS_V1,
    _LEGACY_SERVER_SERVER_JS_V1,
    workspace_service,
)
from app.utils.id_generator import generate_id


def _remove_readonly(func, path, _exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


@pytest.fixture
def project_id():
    pid = generate_id("project")
    store.projects[pid] = {"project_id": pid, "project_name": f"Scaffold Test {pid}"}

    yield pid

    repo_path = workspace_service.get_repo_path(pid)
    if (repo_path / ".git").exists():
        workspace_service.ensure_project_repo(pid).close()
    store.database["projects"].delete_one({"project_id": pid})
    if repo_path.parent.exists():
        shutil.rmtree(repo_path.parent, onerror=_remove_readonly)


def test_fresh_project_gets_full_scaffold_on_disk(project_id):
    workspace_service.ensure_project_repo(project_id)
    repo_path = workspace_service.get_repo_path(project_id)

    for relative_path in SCAFFOLD_FILES:
        assert (repo_path / relative_path).exists(), f"missing {relative_path}"


def test_scaffold_committed_on_main(project_id):
    repo = workspace_service.ensure_project_repo(project_id)

    assert repo.active_branch.name == "main"
    assert not repo.is_dirty(untracked_files=True)

    committed_files = repo.git.ls_tree("-r", "--name-only", "HEAD").splitlines()
    for relative_path in SCAFFOLD_FILES:
        assert relative_path in committed_files


def test_server_scaffold_uses_express_and_exposes_health_route(project_id):
    workspace_service.ensure_project_repo(project_id)
    repo_path = workspace_service.get_repo_path(project_id)

    app_js = (repo_path / "server" / "src" / "app.js").read_text(encoding="utf-8")
    assert "express" in app_js
    assert "/api/health" in app_js

    server_package_json = (repo_path / "server" / "package.json").read_text(encoding="utf-8")
    assert '"express"' in server_package_json


def test_client_scaffold_is_a_real_vite_react_app(project_id):
    workspace_service.ensure_project_repo(project_id)
    repo_path = workspace_service.get_repo_path(project_id)

    client_package_json = (repo_path / "client" / "package.json").read_text(encoding="utf-8")
    assert '"vite"' in client_package_json
    assert '"react"' in client_package_json

    assert (repo_path / "client" / "index.html").exists()
    assert (repo_path / "client" / "vite.config.js").exists()

    main_jsx = (repo_path / "client" / "src" / "main.jsx").read_text(encoding="utf-8")
    assert "createRoot" in main_jsx


def test_backfill_adds_missing_scaffold_file_without_touching_existing_ones(project_id):
    repo = workspace_service.ensure_project_repo(project_id)
    repo_path = workspace_service.get_repo_path(project_id)

    # Simulate an old repo created before client/src/index.css was part of
    # the scaffold, and simulate a feature having already customized app.js.
    (repo_path / "client" / "src" / "index.css").unlink()
    repo.index.remove(["client/src/index.css"])
    repo.index.commit("simulate pre-scaffold-fix repo state")

    custom_app_js = "// customized by a prior feature\n" + (repo_path / "server" / "src" / "app.js").read_text(
        encoding="utf-8"
    )
    (repo_path / "server" / "src" / "app.js").write_text(custom_app_js, encoding="utf-8")
    repo.index.add(["server/src/app.js"])
    repo.index.commit("simulate a prior feature's customization")

    reopened_repo = workspace_service.ensure_project_repo(project_id)

    assert (repo_path / "client" / "src" / "index.css").exists()
    assert (repo_path / "server" / "src" / "app.js").read_text(encoding="utf-8") == custom_app_js
    assert not reopened_repo.is_dirty(untracked_files=True)


def test_backfill_adds_root_scripts_without_touching_existing_dependencies(project_id):
    # Simulate a pre-scaffold repo (the actual state the real, already-in-progress
    # e-commerce-platform project was found in): a root package.json with real
    # declared dependencies but no install:all/dev/build scripts, and no
    # server/client folders at all yet.
    repo_path = workspace_service.get_repo_path(project_id)
    repo_path.mkdir(parents=True, exist_ok=True)
    from git import Repo

    repo = Repo.init(repo_path, initial_branch="main")
    (repo_path / "package.json").write_text(
        '{\n  "name": "auto-forge-generated-app",\n  "private": true,\n'
        '  "dependencies": {\n    "axios": "^1.18.1"\n  }\n}\n',
        encoding="utf-8",
    )
    repo.index.add(["package.json"])
    repo.index.commit("pre-scaffold-fix state")

    workspace_service.ensure_project_repo(project_id)

    data = (repo_path / "package.json").read_text(encoding="utf-8")
    import json as _json

    parsed = _json.loads(data)

    assert parsed["dependencies"] == {"axios": "^1.18.1"}
    assert parsed["scripts"]["dev"] == 'concurrently "npm run dev --prefix server" "npm run dev --prefix client"'
    assert parsed["scripts"]["install:all"] == "npm install --prefix server && npm install --prefix client"
    assert "concurrently" in parsed["devDependencies"]

    for relative_path in SCAFFOLD_FILES:
        assert (repo_path / relative_path).exists()


def test_backfill_is_idempotent_when_nothing_missing(project_id):
    workspace_service.ensure_project_repo(project_id)
    repo = workspace_service.ensure_project_repo(project_id)
    commit_count_before = sum(1 for _ in repo.iter_commits())

    workspace_service.ensure_project_repo(project_id)

    commit_count_after = sum(1 for _ in repo.iter_commits())
    assert commit_count_after == commit_count_before


def _reset_to_legacy_scaffold(repo, repo_path, app_js_content: str, server_js_content: str) -> None:
    """
    Rewrite an already-scaffolded repo's app.js/server.js/package.json back
    to their pre-upgrade (legacy) shape, to simulate a repo that was
    scaffolded before the helmet/rate-limit/mongoose-connect/error-handler
    upgrade shipped -- exactly the real e-commerce-platform project's state
    at the time this upgrade was written.
    """
    import json

    (repo_path / "server" / "src" / "app.js").write_text(app_js_content, encoding="utf-8")
    (repo_path / "server" / "src" / "server.js").write_text(server_js_content, encoding="utf-8")

    package_json_path = repo_path / "server" / "package.json"
    data = json.loads(package_json_path.read_text(encoding="utf-8"))
    data["dependencies"].pop("helmet", None)
    data["dependencies"].pop("express-rate-limit", None)
    package_json_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    repo.index.add(["server/src/app.js", "server/src/server.js", "server/package.json"])
    repo.index.commit("simulate pre-upgrade legacy scaffold state")


def test_upgrade_backfill_replaces_untouched_legacy_app_js_and_server_js_wholesale(project_id):
    repo = workspace_service.ensure_project_repo(project_id)
    repo_path = workspace_service.get_repo_path(project_id)
    _reset_to_legacy_scaffold(repo, repo_path, _LEGACY_SERVER_APP_JS_V1, _LEGACY_SERVER_SERVER_JS_V1)

    workspace_service.ensure_project_repo(project_id)

    app_js = (repo_path / "server" / "src" / "app.js").read_text(encoding="utf-8")
    server_js = (repo_path / "server" / "src" / "server.js").read_text(encoding="utf-8")
    package_json = (repo_path / "server" / "package.json").read_text(encoding="utf-8")

    assert "helmet" in app_js
    assert "express-rate-limit" in app_js
    assert "FEATURE_ROUTES_END" in app_js
    assert "err.stack" in app_js
    assert "mongoose.connect" in server_js
    assert '"helmet"' in package_json
    assert '"express-rate-limit"' in package_json


def test_upgrade_backfill_preserves_a_customized_app_js_router_mount(project_id):
    repo = workspace_service.ensure_project_repo(project_id)
    repo_path = workspace_service.get_repo_path(project_id)

    # Simulate the real e-commerce-platform scenario: a feature already
    # mounted its own router into the legacy app.js before this upgrade
    # existed.
    customized_app_js = _LEGACY_SERVER_APP_JS_V1.replace(
        'const cors = require("cors");\n',
        'const cors = require("cors");\nconst authRoutes = require("./routes/auth.routes");\n',
    ).replace(
        "module.exports = app;",
        'app.use("/api/auth", authRoutes);\n\nmodule.exports = app;',
    )
    _reset_to_legacy_scaffold(repo, repo_path, customized_app_js, _LEGACY_SERVER_SERVER_JS_V1)

    workspace_service.ensure_project_repo(project_id)

    app_js = (repo_path / "server" / "src" / "app.js").read_text(encoding="utf-8")

    assert 'app.use("/api/auth", authRoutes);' in app_js
    assert "helmet" in app_js
    assert "express-rate-limit" in app_js
    assert "FEATURE_ROUTES_END" in app_js
    assert "err.stack" in app_js


def test_upgrade_backfill_is_idempotent_on_customized_app_js(project_id):
    repo = workspace_service.ensure_project_repo(project_id)
    repo_path = workspace_service.get_repo_path(project_id)
    customized_app_js = _LEGACY_SERVER_APP_JS_V1.replace(
        "module.exports = app;", 'app.use("/api/auth", authRoutes);\n\nmodule.exports = app;'
    )
    _reset_to_legacy_scaffold(repo, repo_path, customized_app_js, _LEGACY_SERVER_SERVER_JS_V1)

    workspace_service.ensure_project_repo(project_id)
    first_pass = (repo_path / "server" / "src" / "app.js").read_text(encoding="utf-8")

    workspace_service.ensure_project_repo(project_id)
    second_pass = (repo_path / "server" / "src" / "app.js").read_text(encoding="utf-8")

    assert first_pass == second_pass
    assert first_pass.count("helmet()") == 1
    assert first_pass.count("FEATURE_ROUTES_END") == 1


def test_upgrade_backfill_skips_customized_server_js_without_corrupting_it(project_id):
    repo = workspace_service.ensure_project_repo(project_id)
    repo_path = workspace_service.get_repo_path(project_id)
    customized_server_js = _LEGACY_SERVER_SERVER_JS_V1 + "\n// a feature added this comment\n"
    _reset_to_legacy_scaffold(repo, repo_path, _LEGACY_SERVER_APP_JS_V1, customized_server_js)

    workspace_service.ensure_project_repo(project_id)

    server_js = (repo_path / "server" / "src" / "server.js").read_text(encoding="utf-8")
    assert server_js == customized_server_js
    assert "mongoose.connect" not in server_js
