"""
Unit tests for the Coder Agent's nav_checker module (best-effort static
page-reachability check). No LLM, no git, no Docker -- these operate on a
plain tmp_path directory tree, since check_page_reachability only ever takes
a workspace_root Path.
"""

from app.agents.coder_agent.nav_checker import check_page_reachability


def _write(root, relative_path, content):
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_no_app_jsx_returns_empty(tmp_path):
    assert check_page_reachability(tmp_path) == []


def test_only_root_route_returns_empty(tmp_path):
    _write(
        tmp_path,
        "client/src/App.jsx",
        '<Route path="/" element={<HomePage />} />',
    )
    assert check_page_reachability(tmp_path) == []


def test_reproduces_the_real_bug_route_with_no_link_is_unreachable(tmp_path):
    # Exactly the real, confirmed shape: a feature added a <Route> but
    # nothing links to it -- the bug this checker exists to catch.
    _write(
        tmp_path,
        "client/src/App.jsx",
        '<Route path="/" element={<HomePage />} />\n'
        '<Route path="/login" element={<LoginPage />} />',
    )
    results = check_page_reachability(tmp_path)
    assert results == [{"route": "/login", "status": "unreachable"}]


def test_direct_link_makes_route_reachable(tmp_path):
    _write(
        tmp_path,
        "client/src/App.jsx",
        '<Route path="/" element={<HomePage />} />\n'
        '<Route path="/login" element={<LoginPage />} />\n'
        '<Link to="/login">Login</Link>',
    )
    results = check_page_reachability(tmp_path)
    assert results == [{"route": "/login", "status": "reachable"}]


def test_link_in_a_different_file_still_counts(tmp_path):
    _write(
        tmp_path,
        "client/src/App.jsx",
        '<Route path="/" element={<HomePage />} />\n'
        '<Route path="/login" element={<LoginPage />} />',
    )
    _write(
        tmp_path,
        "client/src/components/Nav.jsx",
        '<Link to="/login">Login</Link>',
    )
    results = check_page_reachability(tmp_path)
    assert results == [{"route": "/login", "status": "reachable"}]


def test_anchor_href_also_counts(tmp_path):
    _write(
        tmp_path,
        "client/src/App.jsx",
        '<Route path="/" element={<HomePage />} />\n'
        '<Route path="/login" element={<LoginPage />} />\n'
        '<a href="/login">Login</a>',
    )
    results = check_page_reachability(tmp_path)
    assert results == [{"route": "/login", "status": "reachable"}]


def test_parameterized_route_unreachable_without_a_linked_list_page(tmp_path):
    _write(
        tmp_path,
        "client/src/App.jsx",
        '<Route path="/" element={<HomePage />} />\n'
        '<Route path="/tasks/:taskId" element={<TaskDetailPage />} />',
    )
    results = check_page_reachability(tmp_path)
    assert results == [{"route": "/tasks/:taskId", "status": "unreachable"}]


def test_parameterized_route_reachable_via_linked_list_page(tmp_path):
    _write(
        tmp_path,
        "client/src/App.jsx",
        '<Route path="/" element={<HomePage />} />\n'
        '<Route path="/tasks" element={<TaskListPage />} />\n'
        '<Route path="/tasks/:taskId" element={<TaskDetailPage />} />\n'
        '<Link to="/tasks">Tasks</Link>',
    )
    results = {item["route"]: item["status"] for item in check_page_reachability(tmp_path)}
    assert results["/tasks"] == "reachable"
    assert results["/tasks/:taskId"] == "reachable"


def test_parameterized_route_unreachable_if_list_page_itself_unlinked(tmp_path):
    _write(
        tmp_path,
        "client/src/App.jsx",
        '<Route path="/" element={<HomePage />} />\n'
        '<Route path="/tasks" element={<TaskListPage />} />\n'
        '<Route path="/tasks/:taskId" element={<TaskDetailPage />} />',
    )
    results = {item["route"]: item["status"] for item in check_page_reachability(tmp_path)}
    assert results["/tasks"] == "unreachable"
    assert results["/tasks/:taskId"] == "unreachable"


def test_template_literal_link_with_interpolation_resolves_to_static_prefix(tmp_path):
    _write(
        tmp_path,
        "client/src/App.jsx",
        '<Route path="/" element={<HomePage />} />\n'
        '<Route path="/tasks" element={<TaskListPage />} />\n'
        '<Route path="/tasks/:taskId" element={<TaskDetailPage />} />\n'
        '<Link to="/tasks">Tasks</Link>',
    )
    _write(
        tmp_path,
        "client/src/pages/TaskListPage.jsx",
        "tasks.map(task => <Link to={`/tasks/${task._id}`}>{task.title}</Link>)",
    )
    results = {item["route"]: item["status"] for item in check_page_reachability(tmp_path)}
    assert results["/tasks"] == "reachable"
    assert results["/tasks/:taskId"] == "reachable"
