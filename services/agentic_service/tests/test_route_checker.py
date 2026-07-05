"""
Unit tests for the Coder Agent's route_checker module (best-effort static
route-coverage + placeholder-stub scanning). No LLM, no Docker, no git --
these operate on a plain tmp_path directory tree, since check_route_coverage/
scan_for_placeholder_stubs only ever take a workspace_root Path.
"""

from app.agents.coder_agent.route_checker import check_route_coverage, scan_for_placeholder_stubs


def _write(root, relative_path, content):
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_check_route_coverage_finds_route_registered_via_mount_prefix(tmp_path):
    _write(
        tmp_path,
        "server/src/app.js",
        'const authRoutes = require("./routes/auth.routes");\n'
        'app.use("/api/auth", authRoutes);\n',
    )
    _write(
        tmp_path,
        "server/src/routes/auth.routes.js",
        "router.post('/login', (req, res) => res.json({}));\n",
    )

    code_plan_json = {
        "files": [
            {
                "path": "server/src/routes/auth.routes.js",
                "action": "create",
                "maps_to": ["/api/auth/login"],
            }
        ]
    }

    results = check_route_coverage(tmp_path, code_plan_json)

    assert results == [{"endpoint": "/api/auth/login", "file": "server/src/routes/auth.routes.js", "status": "found"}]


def test_check_route_coverage_flags_missing_route(tmp_path):
    _write(
        tmp_path,
        "server/src/app.js",
        'const authRoutes = require("./routes/auth.routes");\n'
        'app.use("/api/auth", authRoutes);\n',
    )
    _write(
        tmp_path,
        "server/src/routes/auth.routes.js",
        "router.post('/login', (req, res) => res.json({}));\n",
    )

    code_plan_json = {
        "files": [
            {
                "path": "server/src/routes/auth.routes.js",
                "action": "create",
                # /signup is never registered anywhere in the file.
                "maps_to": ["/api/auth/signup"],
            }
        ]
    }

    results = check_route_coverage(tmp_path, code_plan_json)

    assert results == [{"endpoint": "/api/auth/signup", "file": "server/src/routes/auth.routes.js", "status": "missing"}]


def test_check_route_coverage_finds_full_literal_path_without_mount_prefix(tmp_path):
    _write(tmp_path, "server/src/app.js", "")
    _write(
        tmp_path,
        "server/src/routes/health.routes.js",
        "app.get('/api/auth/login', (req, res) => res.json({}));\n",
    )

    code_plan_json = {
        "files": [
            {
                "path": "server/src/routes/health.routes.js",
                "action": "create",
                "maps_to": ["/api/auth/login"],
            }
        ]
    }

    results = check_route_coverage(tmp_path, code_plan_json)

    assert results[0]["status"] == "found"


def test_check_route_coverage_flags_missing_file(tmp_path):
    code_plan_json = {
        "files": [
            {
                "path": "server/src/routes/never_written.routes.js",
                "action": "create",
                "maps_to": ["/api/widgets"],
            }
        ]
    }

    results = check_route_coverage(tmp_path, code_plan_json)

    assert results == [
        {"endpoint": "/api/widgets", "file": "server/src/routes/never_written.routes.js", "status": "missing"}
    ]


def test_check_route_coverage_ignores_non_backend_and_deleted_files(tmp_path):
    code_plan_json = {
        "files": [
            {"path": "client/src/services/authService.js", "action": "create", "maps_to": ["/api/auth/login"]},
            {"path": "server/src/routes/old.routes.js", "action": "delete", "maps_to": ["/api/old"]},
        ]
    }

    assert check_route_coverage(tmp_path, code_plan_json) == []


def test_check_route_coverage_ignores_files_with_no_endpoint_maps_to(tmp_path):
    _write(tmp_path, "server/src/models/User.js", "module.exports = {};")

    code_plan_json = {
        "files": [
            {"path": "server/src/models/User.js", "action": "create", "maps_to": ["User Credentials"]},
        ]
    }

    assert check_route_coverage(tmp_path, code_plan_json) == []


def test_scan_for_placeholder_stubs_finds_known_phrases(tmp_path):
    _write(
        tmp_path,
        "server/src/routes/auth.routes.js",
        "// In a real app, you would generate a reset token and send an email\n"
        "res.json({ message: 'ok' });\n",
    )

    findings = scan_for_placeholder_stubs(tmp_path, ["server/src/routes/auth.routes.js"])

    assert len(findings) == 1
    assert findings[0]["file"] == "server/src/routes/auth.routes.js"
    assert findings[0]["line"] == 1
    assert "In a real app" in findings[0]["snippet"]


def test_scan_for_placeholder_stubs_clean_file_reports_nothing(tmp_path):
    _write(
        tmp_path,
        "server/src/routes/auth.routes.js",
        "router.post('/login', async (req, res) => { res.json({ token: 'x' }); });\n",
    )

    assert scan_for_placeholder_stubs(tmp_path, ["server/src/routes/auth.routes.js"]) == []


def test_scan_for_placeholder_stubs_ignores_untouched_or_missing_files(tmp_path):
    assert scan_for_placeholder_stubs(tmp_path, ["server/src/routes/does_not_exist.js"]) == []
