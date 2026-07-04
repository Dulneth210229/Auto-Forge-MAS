"""
Workspace / Git service.

Each project gets exactly one persistent Git repository on disk:

    workspaces/{project_slug}/repo/

This is the real, growing MERN codebase the Coder Agent will edit feature by
feature. Git already gives us branching, diffing, and rollback for source code
specifically, so we use it directly instead of reinventing version tracking on
top of the artifact versioning system used for documents/diagrams.

Every feature is developed on its own branch (feature/{feature_slug}) and only
merged into main after human approval.
"""

from pathlib import Path
from typing import Any

from git import GitCommandError, Repo

from app.core.config import settings
from app.services.in_memory_store import store
from app.utils.slugify import slugify

MAIN_BRANCH = "main"

SCAFFOLD_GITIGNORE = """\
node_modules/
.env
dist/
build/
*.log
"""


class WorkspaceService:
    """
    Manages one persistent Git repository per project.
    """

    def _project_slug(self, project_id: str) -> str:
        project = store.projects.get(project_id)

        if not project:
            raise ValueError(f"Project not found: {project_id}")

        return slugify(project.get("project_name") or project_id)

    def _feature_slug(self, feature_id: str) -> str:
        feature = store.features.get(feature_id)

        if not feature:
            raise ValueError(f"Feature not found: {feature_id}")

        return slugify(feature.get("feature_name") or feature_id)

    def _repo_path(self, project_id: str) -> Path:
        return Path(settings.WORKSPACE_DIR) / self._project_slug(project_id) / "repo"

    def get_repo_path(self, project_id: str) -> Path:
        """
        Return the on-disk path of the project's repo (used by SandboxService to
        bind-mount the workspace). Does not require the repo to exist yet.
        """
        return self._repo_path(project_id)

    def _feature_branch_name(self, feature_id: str) -> str:
        return f"feature/{self._feature_slug(feature_id)}"

    def ensure_project_repo(self, project_id: str) -> Repo:
        """
        Return the project's Git repo, initializing and scaffolding it on first use.
        """
        repo_path = self._repo_path(project_id)

        if (repo_path / ".git").exists():
            return Repo(repo_path)

        repo_path.mkdir(parents=True, exist_ok=True)
        repo = Repo.init(repo_path, initial_branch=MAIN_BRANCH)

        (repo_path / "client").mkdir(exist_ok=True)
        (repo_path / "server").mkdir(exist_ok=True)
        (repo_path / "client" / ".gitkeep").touch()
        (repo_path / "server" / ".gitkeep").touch()
        (repo_path / ".gitignore").write_text(SCAFFOLD_GITIGNORE, encoding="utf-8")
        (repo_path / "package.json").write_text(
            '{\n  "name": "auto-forge-generated-app",\n  "private": true\n}\n',
            encoding="utf-8",
        )

        repo.index.add(["client/.gitkeep", "server/.gitkeep", ".gitignore", "package.json"])
        repo.index.commit("Initial project scaffold")

        return repo

    def start_feature_branch(self, project_id: str, feature_id: str) -> str:
        """
        Create (or reset) `feature/{feature_slug}` from main and check it out.

        Returns the branch name.
        """
        repo = self.ensure_project_repo(project_id)
        branch_name = self._feature_branch_name(feature_id)

        repo.git.checkout(MAIN_BRANCH)

        if branch_name in [head.name for head in repo.heads]:
            repo.git.branch("-D", branch_name)

        repo.git.checkout("-b", branch_name)

        return branch_name

    def commit_changes(self, project_id: str, feature_id: str, message: str) -> bool:
        """
        Stage and commit everything currently on the feature branch's working
        tree. Returns False (no-op) if there is nothing to commit.

        The coding loop's tools (write_file/apply_patch/run_shell) only ever
        touch the working tree -- they never commit. diff_against_main() and
        merge_feature_branch() both operate on committed history, so this is
        the deterministic step between "the agentic loop finished" and
        "there is a diff/mergeable commit to review."
        """
        repo = self.ensure_project_repo(project_id)
        branch_name = self._feature_branch_name(feature_id)

        if repo.active_branch.name != branch_name:
            repo.git.checkout(branch_name)

        if not repo.is_dirty(untracked_files=True):
            return False

        repo.git.add(A=True)
        repo.index.commit(message)

        return True

    def diff_against_main(self, project_id: str, feature_id: str) -> dict[str, Any]:
        """
        Return a structured diff of the feature branch against main:
            {
                "added": [...], "modified": [...], "deleted": [...],
                "diff_text": "<unified diff>",
            }

        This is computed deterministically from git, never from an LLM's self-report.
        """
        repo = self.ensure_project_repo(project_id)
        branch_name = self._feature_branch_name(feature_id)

        name_status = repo.git.diff(
            f"{MAIN_BRANCH}...{branch_name}", "--name-status"
        )
        diff_text = repo.git.diff(f"{MAIN_BRANCH}...{branch_name}")

        added, modified, deleted = [], [], []

        for line in name_status.splitlines():
            if not line.strip():
                continue

            status, _, path = line.partition("\t")

            if status.startswith("A"):
                added.append(path)
            elif status.startswith("D"):
                deleted.append(path)
            else:
                modified.append(path)

        return {
            "added": added,
            "modified": modified,
            "deleted": deleted,
            "diff_text": diff_text,
        }

    def merge_feature_branch(self, project_id: str, feature_id: str) -> None:
        """
        Merge the approved feature branch into main and delete the branch.
        """
        repo = self.ensure_project_repo(project_id)
        branch_name = self._feature_branch_name(feature_id)

        repo.git.checkout(MAIN_BRANCH)

        try:
            repo.git.merge(branch_name, "--no-ff", "-m", f"Merge {branch_name} into main")
        except GitCommandError:
            repo.git.merge("--abort")
            raise

        repo.git.branch("-d", branch_name)

    def discard_feature_branch(self, project_id: str, feature_id: str) -> None:
        """
        Discard a rejected feature branch's changes and return to main.
        """
        repo = self.ensure_project_repo(project_id)
        branch_name = self._feature_branch_name(feature_id)

        repo.git.checkout(MAIN_BRANCH)

        if branch_name in [head.name for head in repo.heads]:
            repo.git.branch("-D", branch_name)


workspace_service = WorkspaceService()
