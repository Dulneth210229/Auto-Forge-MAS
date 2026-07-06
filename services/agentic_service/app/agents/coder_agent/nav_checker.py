"""
Coder Agent navigation/page-reachability checker.

Purpose:
Prove every page a feature adds is actually reachable by a human clicking
through the app starting from "/", not just that it compiles and its route
is registered. Confirmed real bug this targets: every project's scaffold
seeds a HomePage at "/" with no navigation, and every feature so far (Login,
Signup, Task Comments) correctly added a `<Route>` for its new page but
never a `<Link>` to it -- so opening the app always showed only the static
placeholder, regardless of what had actually been built.

This is a best-effort, regex-based static check (like route_checker.py's
check_route_coverage), not a real JSX/AST parser or a live browser check --
it will miss unusual routing styles (e.g. programmatic navigation with no
<Link> at all) and can't verify that clicking a link actually works at
runtime, only that a route and a link to it both exist in the source.

Algorithm:
- Every `<Route path="X">` in client/src/App.jsx (other than "/", which is
  the entry point and trivially reachable) is a route that must be proven
  reachable.
- A non-parameterized route is reachable if some `<Link to="X">` (or
  `<a href="X">`) exists ANYWHERE under client/src -- not just in App.jsx's
  HomePage, since a link to a detail page often lives in a separate list
  page component file.
- A parameterized route (contains a `:segment`) can never be linked to
  directly (there is no real id value at the nav level) -- it is reachable
  only if its static prefix (e.g. "/tasks" for "/tasks/:taskId") is itself
  a registered route that is, in turn, linked from somewhere. This mirrors
  the planner prompt's guidance: a parameterized detail route needs a
  reachable list/index page ancestor.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROUTE_PATTERN = re.compile(r'<Route\s+path="([^"]+)"')

_LINK_PATTERNS = [
    re.compile(r'<Link\s+to="([^"]+)"'),
    re.compile(r'<Link\s+to=\{`([^`$]*)\$\{'),  # to={`/prefix/${id}`} -> captures "/prefix/"
    re.compile(r'<Link\s+to=\{`([^`]*)`\}'),  # to={`/fully/static`} (no interpolation)
    re.compile(r'<a\s+href="([^"]+)"'),
]

_EXCLUDED_DIRS = {"node_modules", ".git"}


def check_page_reachability(workspace_root: Path) -> list[dict[str, str]]:
    """
    Returns [{"route": "/login", "status": "reachable"|"unreachable"}, ...]
    for every top-level `<Route path="...">` in client/src/App.jsx other
    than "/". Returns [] if there's no client/src/App.jsx or no non-root
    routes registered yet.
    """
    app_jsx_path = workspace_root / "client" / "src" / "App.jsx"

    if not app_jsx_path.exists():
        return []

    app_jsx_content = app_jsx_path.read_text(encoding="utf-8")
    route_paths = [
        match.group(1) for match in _ROUTE_PATTERN.finditer(app_jsx_content) if match.group(1) != "/"
    ]

    if not route_paths:
        return []

    registered_paths = set(route_paths)
    linked_paths = _collect_linked_paths(workspace_root / "client" / "src")

    results: list[dict[str, str]] = []

    for route_path in route_paths:
        if _is_parameterized(route_path):
            prefix = _static_prefix(route_path)
            reachable = prefix in registered_paths and _path_is_linked(prefix, linked_paths)
        else:
            reachable = _path_is_linked(route_path, linked_paths)

        results.append({"route": route_path, "status": "reachable" if reachable else "unreachable"})

    return results


def _collect_linked_paths(client_src_root: Path) -> set[str]:
    linked: set[str] = set()

    if not client_src_root.exists():
        return linked

    for file_path in client_src_root.rglob("*.jsx"):
        if any(part in _EXCLUDED_DIRS for part in file_path.parts):
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for pattern in _LINK_PATTERNS:
            for match in pattern.finditer(content):
                linked.add(match.group(1))

    return linked


def _path_is_linked(path: str, linked_paths: set[str]) -> bool:
    normalized = path.rstrip("/")
    return any(linked.rstrip("/") == normalized for linked in linked_paths)


def _is_parameterized(path: str) -> bool:
    return any(segment.startswith(":") for segment in path.split("/"))


def _static_prefix(path: str) -> str:
    static_segments: list[str] = []

    for segment in path.split("/"):
        if segment.startswith(":"):
            break
        static_segments.append(segment)

    return "/".join(static_segments) or "/"
