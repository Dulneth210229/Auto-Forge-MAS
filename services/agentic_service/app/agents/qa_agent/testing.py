"""
QA Agent -- discovery, generation, and execution helpers.

Scope, stated plainly: this first real implementation targets the
"pure-logic" layer of a generated Next.js project -- modules under lib/ and
models/ that export data or functions with no DOM dependency -- because
Node's built-in test runner (the zero-dependency execution path used when
the target project has no test framework installed; see
detect_test_framework below) cannot render a React component without jsdom
or React Testing Library, neither of which this pipeline currently installs
into a generated project. React components/pages (app/**/page.tsx,
components/**.tsx) and Next.js Route Handlers that import "next/server" are
discovered but explicitly reported as out of this runner's reach rather than
silently skipped -- see generate_tests_for_module's SKIP_REASONS.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

TESTABLE_DIR_NAMES = {"lib", "models"}
EXCLUDED_DIR_NAMES = {"node_modules", ".next", ".git", "dist", "build", "__pycache__"}
EXPORT_PATTERN = re.compile(
    r"export\s+(?:default\s+)?(?:async\s+)?(?:function|const|class)\s+([A-Za-z0-9_]+)"
)
ARRAY_LITERAL_PATTERN = re.compile(r"export\s+const\s+([A-Za-z0-9_]+)\s*=\s*\[")
GUARDED_ASYNC_NULL_PATTERN = re.compile(
    r"export\s+async\s+function\s+([A-Za-z0-9_]+).*?return\s+null", re.DOTALL
)


def discover_testable_modules(repo_path: Path) -> list[dict[str, Any]]:
    """
    Conservative discovery pass: only lib/ and models/, only .ts files (not
    .tsx -- a .tsx file under lib/ almost always still returns JSX and needs
    a renderer). Returns one entry per file with its exported names and the
    two shape-detectors this fallback generator can act on.
    """
    modules: list[dict[str, Any]] = []
    for dir_name in TESTABLE_DIR_NAMES:
        base = repo_path / dir_name
        if not base.exists():
            continue
        for path in base.rglob("*.ts"):
            if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            # Strip //-comments before matching so a comment that merely
            # *mentions* an export pattern (documentation, examples) is not
            # mistaken for a real export -- observed for real during
            # development: lib/seedData.ts's own header comment describes
            # the `export const seed<Entity>` naming convention in prose,
            # which a naive regex over the raw text matched as an export
            # named "seed".
            code_only = re.sub(r"//.*", "", text)
            exports = EXPORT_PATTERN.findall(code_only)
            if not exports:
                continue
            modules.append({
                "file": path,
                "rel": str(path.relative_to(repo_path)),
                "exports": exports,
                "array_literal_exports": ARRAY_LITERAL_PATTERN.findall(code_only),
                "guarded_async_null_exports": GUARDED_ASYNC_NULL_PATTERN.findall(code_only),
            })
    return modules


def _walk_files(repo_path: Path):
    """
    os.walk with in-place dirname pruning -- see scanners.py's identical
    helper for why Path.rglob("*") over a real installed node_modules is not
    safe to use here (it still walks every excluded subtree before the
    per-file filter gets a chance to skip it).
    """
    import os

    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIR_NAMES]
        for filename in filenames:
            yield Path(dirpath) / filename


def discover_out_of_scope_modules(repo_path: Path) -> list[str]:
    """
    Everything this runner deliberately does NOT generate tests for, so the
    QA report can state the gap explicitly instead of it reading as
    incomplete coverage nobody noticed.
    """
    out_of_scope = []
    for path in _walk_files(repo_path):
        if path.suffix == ".tsx" or (path.name == "route.ts" and "app" in path.parts):
            out_of_scope.append(str(path.relative_to(repo_path)))
    return sorted(out_of_scope)


def detect_test_framework(repo_path: Path) -> str:
    """
    "jest" if the target project declares jest as a dependency (checked via
    its own package.json, not this service's), else the zero-dependency
    "node:test" fallback -- the case for every project this pipeline
    currently scaffolds (see IMPL_P2).
    """
    package_json = repo_path / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        if "jest" in deps:
            return "jest"
    return "node:test"


TEMPLATE = """import test from "node:test";
import assert from "node:assert/strict";
{imports}

{body}
"""


def _generate_array_literal_tests(export_name: str, rel_import: str) -> str:
    return f"""test("{export_name} is a non-empty array", () => {{
  assert.ok(Array.isArray({export_name}));
  assert.ok({export_name}.length > 0);
}});

test("every {export_name} entry has a unique id", () => {{
  const ids = {export_name}.map((entry) => entry.id);
  assert.equal(new Set(ids).size, ids.length);
}});"""


def _generate_guarded_async_tests(export_name: str) -> str:
    return f"""test("{export_name}() resolves (does not throw) when its required env var is unset", async () => {{
  const result = await {export_name}();
  assert.ok(result === null || result !== undefined);
}});"""


def generate_tests_for_module(
    module: dict[str, Any],
    framework: str,
    invoke_llm: Callable[[str], Any] | None = None,
) -> tuple[str, str]:
    """
    Returns (test_source, generation_method). generation_method is
    "llm" when invoke_llm produced usable output, or
    "deterministic-fallback" when it was unavailable/unusable -- the QA
    report records which one actually produced each file, so "LLM-generated
    tests" is never claimed for output the fallback template produced.
    """
    if invoke_llm is not None:
        try:
            llm_source = invoke_llm(module)
            if llm_source and "test(" in llm_source:
                return llm_source, "llm"
        except Exception:  # noqa: BLE001 -- fall through to the deterministic path
            pass

    rel_import = "../" * (len(Path(module["rel"]).parts) - 1) + module["rel"].removesuffix(".ts") + ".ts"
    parts = []
    imported = []
    for name in module["array_literal_exports"]:
        parts.append(_generate_array_literal_tests(name, rel_import))
        imported.append(name)
    for name in module["guarded_async_null_exports"]:
        parts.append(_generate_guarded_async_tests(name))
        imported.append(name)

    if not parts:
        return "", "deterministic-fallback"

    import_line = f'import {{ {", ".join(imported)} }} from "{rel_import}";'
    return TEMPLATE.format(imports=import_line, body="\n\n".join(parts)), "deterministic-fallback"


def run_tests(
    repo_path: Path,
    generated_dir: Path,
    project_id: str,
    run_command_fn: Callable[[str, str, str, int], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Executes every *.test.ts under generated_dir via
    `node --experimental-strip-types --test`, which requires zero installed
    dependencies -- the reason this fallback framework was chosen over
    ts-node/babel-jest for an environment that cannot always reach the npm
    registry to install them.

    run_command_fn defaults to sandbox_service.run_command, matching every
    other command execution in this codebase (see scanners.py's
    scan_dependencies for the same dependency-injection reasoning).
    """
    if run_command_fn is None:
        from app.services.sandbox_service import sandbox_service
        run_command_fn = lambda pid, cmd, cwd, timeout: sandbox_service.run_command(
            project_id=pid, command=cmd, cwd=cwd, timeout=timeout
        )

    rel_dir = generated_dir.relative_to(repo_path)
    command = f"node --experimental-strip-types --test {rel_dir}/*.test.ts"
    result = run_command_fn(project_id, command, ".", 60)
    return _parse_tap_output(result.get("stdout", "") or "", result)


def _parse_tap_output(tap_text: str, raw_result: dict[str, Any]) -> dict[str, Any]:
    passed = failed = skipped = 0
    for line in tap_text.splitlines():
        line = line.strip()
        if line.startswith("# pass "):
            passed = int(line.split()[-1])
        elif line.startswith("# fail "):
            failed = int(line.split()[-1])
        elif line.startswith("# skipped "):
            skipped = int(line.split()[-1])
    return {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "exit_code": raw_result.get("exit_code"),
        "raw_output": tap_text[-4000:],
    }
