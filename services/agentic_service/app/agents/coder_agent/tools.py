"""
Coder Agent tools.

These are the tools handed to the agentic coding loop (M4's
create_react_agent). All path-taking tools are hard-scoped to
workspaces/{project_slug}/repo -- any path that would resolve outside that
root is rejected, never executed.

Each tool returns a plain string, even on failure ("file not found",
"find text did not match exactly once", a rejected shell command, etc.)
rather than raising, so the agent loop can read the failure and react to it
instead of crashing.

Tools are built per-run by build_coder_tools(project_id, feature_id) rather
than defined as bare module-level @tool functions, because every tool needs
to already be bound to one project's workspace (and, for read_ui_component,
one feature's approved UI/UX output) -- the LLM-facing signatures below take
no project_id/feature_id argument at all, matching the build plan's literal
tool signatures.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool, tool

from app.core.enums import AgentName, ApprovalStatus, ArtifactFormat, ArtifactType
from app.services.in_memory_store import store
from app.services.project_memory_service import project_memory_service
from app.services.sandbox_service import sandbox_service
from app.services.workspace_service import workspace_service

ALLOWED_SHELL_COMMANDS = {"npm", "npx", "node"}
ALLOWED_GIT_SUBCOMMANDS = {"status", "diff"}

SEARCH_EXCLUDED_DIRS = {".git", "node_modules"}
SEARCH_MAX_RESULTS = 200
SEARCH_MAX_FILE_BYTES = 2_000_000  # skip huge/binary-ish files


class PathEscapesWorkspaceError(Exception):
    """Raised internally when a tool argument would resolve outside the workspace root."""


def _resolve_within(workspace_root: Path, path: str) -> Path:
    """
    Resolve `path` relative to workspace_root and guarantee the result stays
    inside it. Handles both '..'-style traversal and absolute-path arguments
    (pathlib silently discards the left operand when the right side of `/`
    is itself absolute, so the check must happen on the final resolved path,
    not on the raw string).
    """
    candidate = (workspace_root / path).resolve()

    if not candidate.is_relative_to(workspace_root):
        raise PathEscapesWorkspaceError(f"Path escapes workspace root: {path!r}")

    return candidate


def _is_allowed_shell_command(command: str) -> bool:
    tokens = command.strip().split()

    if not tokens:
        return False

    if tokens[0] in ALLOWED_SHELL_COMMANDS:
        return True

    if tokens[0] == "git" and len(tokens) >= 2 and tokens[1] in ALLOWED_GIT_SUBCOMMANDS:
        return True

    return False


def build_coder_tools(
    project_id: str, feature_id: str, code_plan_json: dict[str, Any] | None = None
) -> list[BaseTool]:
    """
    Build the Coder Agent tools, scoped to one project's workspace, one
    feature's approved UI/UX output, and (for list_unimplemented_planned_files)
    one run's approved code_plan_json.

    code_plan_json is optional so existing callers/tests that only need the
    file/shell tools don't have to supply a plan -- list_unimplemented_planned_files
    degrades to reporting "no plan available" rather than raising when omitted.
    """

    workspace_service.ensure_project_repo(project_id)
    workspace_root = workspace_service.get_repo_path(project_id).resolve()

    @tool
    def list_dir(path: str = ".") -> str:
        """List files and folders under `path` (relative to the workspace root)."""
        try:
            target = _resolve_within(workspace_root, path)
        except PathEscapesWorkspaceError as error:
            return str(error)

        if not target.exists():
            return f"Path not found: {path}"

        if not target.is_dir():
            return f"Not a directory: {path}"

        entries = sorted(target.iterdir(), key=lambda item: item.name)

        if not entries:
            return "(empty directory)"

        return "\n".join(
            f"{'[dir] ' if entry.is_dir() else '[file]'} {entry.name}" for entry in entries
        )

    @tool
    def read_file(path: str) -> str:
        """Read a file's contents as text."""
        try:
            target = _resolve_within(workspace_root, path)
        except PathEscapesWorkspaceError as error:
            return str(error)

        if not target.exists() or not target.is_file():
            return f"File not found: {path}"

        try:
            return target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"File is not valid UTF-8 text: {path}"

    @tool
    def write_file(path: str, content: str) -> str:
        """Create a new file (or fully overwrite an existing one) with `content`."""
        try:
            target = _resolve_within(workspace_root, path)
        except PathEscapesWorkspaceError as error:
            return str(error)

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        return f"Wrote {len(content)} characters to {path}"

    @tool
    def apply_patch(path: str, find: str, replace: str) -> str:
        """
        Replace an exact snippet in an existing file. `find` must match the
        file's current content exactly once -- if it matches zero or more
        than one time, nothing is written and an error explaining why is
        returned so the file can be re-read and retried.
        """
        try:
            target = _resolve_within(workspace_root, path)
        except PathEscapesWorkspaceError as error:
            return str(error)

        if not target.exists() or not target.is_file():
            return f"File not found: {path}"

        content = target.read_text(encoding="utf-8")
        occurrences = content.count(find)

        if occurrences == 0:
            return (
                "Patch failed: `find` text was not found in the file. "
                "Re-read the file and retry with an exact snippet."
            )

        if occurrences > 1:
            return (
                f"Patch failed: `find` text matched {occurrences} times, but must match "
                "exactly once. Include more surrounding context to make it unique."
            )

        target.write_text(content.replace(find, replace, 1), encoding="utf-8")

        return f"Patched {path} (1 replacement)."

    @tool
    def run_shell(command: str, cwd: str = ".", timeout: int = 120) -> str:
        """
        Run an allowlisted shell command (npm, npx, node, git status, git diff)
        inside a sandboxed container with the workspace mounted.
        """
        if not _is_allowed_shell_command(command):
            return (
                f"Command rejected: only npm, npx, node, 'git status', and 'git diff' "
                f"are allowed. Got: {command!r}"
            )

        result = sandbox_service.run_command(
            project_id=project_id, command=command, cwd=cwd, timeout=timeout
        )

        return (
            f"exit_code: {result['exit_code']}\n"
            f"stdout:\n{result['stdout']}\n"
            f"stderr:\n{result['stderr']}"
        )

    @tool
    def search_code(query: str) -> str:
        """
        Search the workspace for a regex pattern, returning path:line:content
        results (like ripgrep). Capped to avoid dumping unbounded output.
        """
        try:
            pattern = re.compile(query)
        except re.error:
            pattern = re.compile(re.escape(query))

        matches: list[str] = []

        for file_path in workspace_root.rglob("*"):
            if any(part in SEARCH_EXCLUDED_DIRS for part in file_path.parts):
                continue

            if not file_path.is_file():
                continue

            try:
                if file_path.stat().st_size > SEARCH_MAX_FILE_BYTES:
                    continue

                text = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue

            relative_path = file_path.relative_to(workspace_root)

            for line_number, line in enumerate(text.splitlines(), start=1):
                if pattern.search(line):
                    matches.append(f"{relative_path}:{line_number}:{line.strip()}")

                    if len(matches) >= SEARCH_MAX_RESULTS:
                        matches.append(f"... truncated at {SEARCH_MAX_RESULTS} matches ...")
                        return "\n".join(matches)

        if not matches:
            return f"No matches found for: {query}"

        return "\n".join(matches)

    @tool
    def read_project_manifest() -> str:
        """Return the project's manifest (existing routes/models/components) as JSON text."""
        manifest = project_memory_service.load_project_manifest(project_id)
        return json.dumps(manifest, indent=2, default=str)

    @tool
    def read_ui_component(component_name: str) -> str:
        """Read the approved .jsx file the UI/UX Agent produced for this feature."""
        artifact = _find_approved_component_artifact(feature_id, component_name)

        if not artifact:
            return f"No approved UI component found for this feature named: {component_name}"

        return Path(artifact["file_path"]).read_text(encoding="utf-8")

    @tool
    def list_unimplemented_planned_files() -> str:
        """
        Compare the approved plan's file list against what has actually been
        created/modified/deleted so far in this workspace (computed from git,
        not from memory of your own tool calls) and report any planned file
        you have not yet touched. Call this before ending your turn -- do not
        rely on your own recollection of what you've done; check here first.
        """
        if not code_plan_json:
            return "No code_plan_json was provided for this run -- nothing to check against."

        touched = workspace_service.get_touched_files(project_id, feature_id)
        touched_paths = set(touched["added"]) | set(touched["modified"]) | set(touched["deleted"])

        gaps = []
        for file_entry in code_plan_json.get("files", []):
            path = file_entry.get("path")
            action = file_entry.get("action")

            if not path or path in touched_paths:
                continue

            gaps.append(f"- {path} (action: {action}, rationale: {file_entry.get('rationale', '')})")

        if not gaps:
            return "All planned files have been created, modified, or deleted as required."

        return (
            "The following planned files have NOT been touched yet -- address these "
            "before ending your turn:\n" + "\n".join(gaps)
        )

    @tool
    def check_syntax(path: str) -> str:
        """
        Run a fast syntax check on a single .js/.jsx file you just wrote or
        patched, without the cost of a full install/build. Use this right
        after write_file/apply_patch on any .js/.jsx file, before moving on.
        """
        try:
            target = _resolve_within(workspace_root, path)
        except PathEscapesWorkspaceError as error:
            return str(error)

        if not target.exists() or not target.is_file():
            return f"File not found: {path}"

        suffix = target.suffix.lower()
        if suffix not in {".js", ".jsx", ".mjs", ".cjs"}:
            return f"check_syntax only supports .js/.jsx/.mjs/.cjs files, got: {path}"

        relative_path = target.relative_to(workspace_root).as_posix()
        is_jsx = suffix == ".jsx"

        if is_jsx:
            check_script = (
                "const fs = require('fs');"
                "const { parse } = require('@babel/parser');"
                f"const code = fs.readFileSync('{relative_path}', 'utf-8');"
                "try {"
                "  parse(code, { sourceType: 'module', plugins: ['jsx'] });"
                "  console.log('SYNTAX_OK');"
                "} catch (error) {"
                "  console.error('SYNTAX_ERROR: ' + error.message);"
                "  process.exit(1);"
                "}"
            )
            command = f"node -e \"{check_script}\""
        else:
            command = f"node --check {relative_path}"

        result = sandbox_service.run_command(project_id=project_id, command=command, cwd=".", timeout=30)

        if result["exit_code"] == 0:
            return f"{path}: syntax OK."

        return f"{path}: syntax error.\n{result['stderr'] or result['stdout']}"

    return [
        list_dir,
        read_file,
        write_file,
        apply_patch,
        run_shell,
        search_code,
        read_project_manifest,
        read_ui_component,
        list_unimplemented_planned_files,
        check_syntax,
    ]


def _find_approved_component_artifact(feature_id: str, component_name: str) -> dict[str, Any] | None:
    slug = re.sub(r"[^a-z0-9]+", "_", component_name.lower()).strip("_")

    matching = []

    for artifact in store.artifacts.values():
        if artifact.get("feature_id") != feature_id:
            continue
        if artifact.get("agent_name") not in [AgentName.UIUX, AgentName.UIUX.value]:
            continue
        if artifact.get("artifact_type") not in [ArtifactType.UI_COMPONENT_CODE, ArtifactType.UI_COMPONENT_CODE.value]:
            continue
        if artifact.get("artifact_format") not in [ArtifactFormat.CODE, ArtifactFormat.CODE.value]:
            continue
        if artifact.get("approval_status") not in [ApprovalStatus.APPROVED, ApprovalStatus.APPROVED.value]:
            continue
        if slug not in str(artifact.get("file_path", "")).lower():
            continue

        matching.append(artifact)

    if not matching:
        return None

    return max(matching, key=lambda item: item.get("version", 1))
