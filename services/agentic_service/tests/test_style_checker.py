"""
Unit tests for the Coder Agent's style_checker module (best-effort static
"does this page/component use Tailwind classes" check). No LLM, no git, no
Docker -- these operate on a plain tmp_path directory tree, since
check_component_styling only ever takes a workspace_root Path.
"""

from app.agents.coder_agent.style_checker import check_component_styling


def _write(root, relative_path, content):
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_no_component_dirs_returns_empty(tmp_path):
    assert check_component_styling(tmp_path) == []


def test_file_with_class_name_is_styled(tmp_path):
    _write(
        tmp_path,
        "client/src/pages/TaskDetailPage.jsx",
        'export default function TaskDetailPage() { return <div className="p-4">Hi</div>; }',
    )
    results = check_component_styling(tmp_path)

    assert results == [{"path": "client/src/pages/TaskDetailPage.jsx", "status": "styled"}]


def test_file_with_only_inline_style_is_flagged(tmp_path):
    # Reproduces the real, confirmed bug: TaskflowHomePage.jsx used only
    # raw inline styles, zero className usage, and was missed by a real
    # agentic exploration run relying on manual list_dir/read_file alone.
    _write(
        tmp_path,
        "client/src/pages/TaskflowHomePage.jsx",
        'export default function TaskflowHomePage() { '
        'return <div style={{ padding: "2rem" }}>Home</div>; }',
    )
    results = check_component_styling(tmp_path)

    assert results == [{"path": "client/src/pages/TaskflowHomePage.jsx", "status": "inline_styles"}]


def test_file_with_neither_is_unstyled(tmp_path):
    _write(
        tmp_path,
        "client/src/components/Bare.jsx",
        "export default function Bare() { return <div>Hi</div>; }",
    )
    results = check_component_styling(tmp_path)

    assert results == [{"path": "client/src/components/Bare.jsx", "status": "unstyled"}]


def test_scans_both_pages_and_components_dirs(tmp_path):
    _write(tmp_path, "client/src/pages/A.jsx", "<div className='x'>A</div>")
    _write(tmp_path, "client/src/components/B.jsx", "<div>B</div>")

    results = check_component_styling(tmp_path)
    paths = {item["path"] for item in results}

    assert paths == {"client/src/pages/A.jsx", "client/src/components/B.jsx"}


def test_non_jsx_files_are_ignored(tmp_path):
    _write(tmp_path, "client/src/pages/A.jsx", "<div>A</div>")
    _write(tmp_path, "client/src/pages/A.test.js", "not a component")

    results = check_component_styling(tmp_path)

    assert len(results) == 1
    assert results[0]["path"] == "client/src/pages/A.jsx"
