"""
Coder Agent route checker.

Purpose:
plan_validator.py only ever checks that a *planned* endpoint appears in some
file's `maps_to` list -- it never checks the *generated code itself*, so a
plan that fully passes validation gives no guarantee the coding loop actually
implemented every endpoint it claimed to cover (e.g. a route stub that
registers a path but never does anything). This module closes that gap with
two deterministic, post-code, best-effort static checks:

- check_route_coverage: does a planned backend endpoint actually have a
  matching route registration in the file that was supposed to implement
  it? This is regex-based path matching, not a real router/AST analysis --
  it will miss unusual routing styles and can't verify behavior, only that
  a route handler was registered for roughly the right path. Treated as a
  hard gate in verify.py precisely because it targets the cheapest, most
  mechanical form of "claims to cover this endpoint but doesn't" bug.
- scan_for_placeholder_stubs: a phrase-based scan for the exact class of
  "in a real app, you would..." placeholder logic found in the real,
  already-merged Login feature. Deliberately informational only (never
  gates verification) -- these phrases are common enough in legitimate
  comments that treating every hit as a hard failure would be too
  false-positive-prone; it exists so a human reviewer sees it in the merge
  report, not so the pipeline blocks on it.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_ROUTE_REGISTRATION_PATTERN = re.compile(
    r"""\.(?:get|post|put|delete|patch)\(\s*(["'`])((?:(?!\1).)*)\1""",
    re.IGNORECASE,
)

_MOUNT_PATTERN = re.compile(
    r"""app\.use\(\s*(["'`])((?:(?!\1).)*)\1\s*,\s*([A-Za-z0-9_$]+)\s*\)""",
)

_REQUIRE_PATTERN = re.compile(
    r"""(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*require\(\s*(["'`])((?:(?!\2).)*)\2\s*\)""",
)

_PLACEHOLDER_PATTERNS = [
    re.compile(r"in a real app", re.IGNORECASE),
    re.compile(r"not (?:yet )?implemented", re.IGNORECASE),
    re.compile(r"for demonstration purposes", re.IGNORECASE),
    re.compile(r"\bTODO\b"),
    re.compile(r"\bfor now\b", re.IGNORECASE),
]


def check_route_coverage(workspace_root: Path, code_plan_json: dict[str, Any]) -> list[dict[str, str]]:
    """
    For each planned, non-deleted backend file (path starting with "server/")
    whose maps_to includes an endpoint-shaped string (starts with "/"),
    check whether that file actually registers a matching route -- either
    the literal full path, or (more commonly) a relative path that combines
    with the mount prefix app.js registers for this file's router to form
    the full endpoint.

    Returns [{"endpoint", "file", "status": "found"|"missing"}, ...].
    """
    app_js_path = workspace_root / "server" / "src" / "app.js"
    app_js_content = app_js_path.read_text(encoding="utf-8") if app_js_path.exists() else ""

    require_targets = {
        binding: target for binding, _quote, target in _REQUIRE_PATTERN.findall(app_js_content)
    }
    mount_prefix_by_binding = {
        match.group(3): match.group(2) for match in _MOUNT_PATTERN.finditer(app_js_content)
    }

    results: list[dict[str, str]] = []

    for file_entry in code_plan_json.get("files", []):
        if file_entry.get("action") == "delete":
            continue

        path = file_entry.get("path", "")
        if not path.startswith("server/"):
            continue

        endpoints = [
            item
            for item in file_entry.get("maps_to", []) or []
            if isinstance(item, str) and item.startswith("/")
        ]
        if not endpoints:
            continue

        file_path = workspace_root / path

        if not file_path.exists():
            results.extend({"endpoint": endpoint, "file": path, "status": "missing"} for endpoint in endpoints)
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            results.extend({"endpoint": endpoint, "file": path, "status": "missing"} for endpoint in endpoints)
            continue

        registered_relative = {match.group(2) for match in _ROUTE_REGISTRATION_PATTERN.finditer(content)}
        prefix = _resolve_mount_prefix(path, require_targets, mount_prefix_by_binding)

        for endpoint in endpoints:
            covered = endpoint in registered_relative

            if not covered and prefix and endpoint.startswith(prefix):
                suffix = endpoint[len(prefix):] or "/"
                if not suffix.startswith("/"):
                    suffix = "/" + suffix
                covered = suffix in registered_relative

            if not covered:
                last_segment = "/" + endpoint.rsplit("/", 1)[-1]
                covered = last_segment in registered_relative

            results.append({"endpoint": endpoint, "file": path, "status": "found" if covered else "missing"})

    return results


def _resolve_mount_prefix(
    path: str, require_targets: dict[str, str], mount_prefix_by_binding: dict[str, str]
) -> str | None:
    """
    Find the /api/... prefix app.js mounts this router file at, by matching
    this file's path (relative to server/src, extension-less) against each
    require(...) target app.js declares, then looking up that binding's
    app.use(prefix, binding) mount.
    """
    try:
        relative_to_src = Path(path).relative_to("server/src").as_posix()
    except ValueError:
        return None

    without_extension = relative_to_src.rsplit(".", 1)[0]

    for binding, target in require_targets.items():
        normalized_target = target if target.startswith(".") else f"./{target}"
        normalized_target = normalized_target.removeprefix("./")

        if normalized_target in (relative_to_src, without_extension) and binding in mount_prefix_by_binding:
            return mount_prefix_by_binding[binding]

    return None


def scan_for_placeholder_stubs(workspace_root: Path, touched_paths: list[str]) -> list[dict[str, Any]]:
    """
    Best-effort scan of every touched file for placeholder-stub language
    (e.g. "in a real app, you would...", "not implemented", "TODO").
    Never used as a pass/fail gate -- see module docstring.
    """
    findings: list[dict[str, Any]] = []

    for relative_path in touched_paths:
        file_path = workspace_root / relative_path

        if not file_path.exists() or not file_path.is_file():
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for line_number, line in enumerate(content.splitlines(), start=1):
            for pattern in _PLACEHOLDER_PATTERNS:
                if pattern.search(line):
                    findings.append({"file": relative_path, "line": line_number, "snippet": line.strip()})
                    break

    return findings
