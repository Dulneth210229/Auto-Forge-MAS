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

import json
from pathlib import Path
from typing import Any

from git import GitCommandError, Repo

from app.core.config import settings
from app.services.in_memory_store import store
from app.utils.logger import get_logger
from app.utils.slugify import slugify

logger = get_logger(__name__)

MAIN_BRANCH = "main"

SCAFFOLD_GITIGNORE = """\
node_modules/
.env
dist/
build/
*.log
"""

ROOT_PACKAGE_JSON = """\
{
  "name": "auto-forge-generated-app",
  "private": true,
  "scripts": {
    "install:all": "npm install --prefix server && npm install --prefix client",
    "dev": "concurrently \\"npm run dev --prefix server\\" \\"npm run dev --prefix client\\"",
    "build": "npm run build --prefix client"
  },
  "devDependencies": {
    "concurrently": "^8.2.2"
  }
}
"""

SERVER_PACKAGE_JSON = """\
{
  "name": "auto-forge-server",
  "private": true,
  "type": "commonjs",
  "scripts": {
    "start": "node src/server.js",
    "dev": "nodemon src/server.js"
  },
  "dependencies": {
    "express": "^4.19.2",
    "cors": "^2.8.5",
    "dotenv": "^16.4.5",
    "mongoose": "^8.5.0",
    "helmet": "^7.1.0",
    "express-rate-limit": "^7.4.0"
  },
  "devDependencies": {
    "nodemon": "^3.1.4"
  }
}
"""

SERVER_APP_JS = """\
const express = require("express");
const cors = require("cors");
const helmet = require("helmet");
const rateLimit = require("express-rate-limit");

const app = express();

app.use(helmet());
app.use(cors());
app.use(express.json());

const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
});
app.use("/api/", apiLimiter);

app.get("/api/health", (req, res) => {
  res.json({ status: "ok" });
});

// FEATURE_ROUTES_START
// FEATURE_ROUTES_END

app.use((err, req, res, next) => {
  console.error(err.stack);
  const status = err.status || 500;
  res.status(status).json({ error: { message: err.message || "Internal Server Error" } });
});

module.exports = app;
"""

SERVER_SERVER_JS = """\
require("dotenv").config();
const mongoose = require("mongoose");
const app = require("./app");

const PORT = process.env.PORT || 5000;
const MONGODB_URI = process.env.MONGODB_URI;

async function start() {
  if (MONGODB_URI) {
    try {
      await mongoose.connect(MONGODB_URI);
      console.log("Connected to MongoDB");
    } catch (error) {
      console.error("Failed to connect to MongoDB:", error.message);
    }
  } else {
    console.warn("MONGODB_URI is not set -- starting without a database connection.");
  }

  app.listen(PORT, () => {
    console.log(`Server listening on port ${PORT}`);
  });
}

start();
"""

# Frozen, exact content of SERVER_APP_JS/SERVER_SERVER_JS before the
# helmet/rate-limit/mongoose.connect/error-handler upgrade above -- used by
# _upgrade_server_app_js/_upgrade_server_server_js to detect a file that is
# provably still the untouched original scaffold (safe to replace wholesale)
# versus one a feature has since customized (needs targeted insertion
# instead). Never change these two constants after the fact.
_LEGACY_SERVER_APP_JS_V1 = """\
const express = require("express");
const cors = require("cors");

const app = express();

app.use(cors());
app.use(express.json());

app.get("/api/health", (req, res) => {
  res.json({ status: "ok" });
});

module.exports = app;
"""

_LEGACY_SERVER_SERVER_JS_V1 = """\
require("dotenv").config();
const app = require("./app");

const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
"""

SERVER_ENV_EXAMPLE = """\
PORT=5000
MONGODB_URI=mongodb://localhost:27017/auto-forge-generated-app
JWT_SECRET=change-me
"""

CLIENT_PACKAGE_JSON = """\
{
  "name": "auto-forge-client",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.4.0"
  }
}
"""

CLIENT_VITE_CONFIG = """\
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
"""

CLIENT_INDEX_HTML = """\
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Auto-Forge Generated App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""

CLIENT_MAIN_JSX = """\
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
"""

CLIENT_APP_JSX = """\
import React from "react";
import { Routes, Route } from "react-router-dom";

function HomePage() {
  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>Auto-Forge Generated App</h1>
      <p>Feature pages are registered as routes below.</p>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
    </Routes>
  );
}
"""

CLIENT_INDEX_CSS = """\
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
"""

# path (relative to repo root) -> content. Anything already on disk is left
# untouched -- this is a backfill for what's missing, never an overwrite of
# whatever a feature branch/coding loop has since added on top.
SCAFFOLD_FILES: dict[str, str] = {
    "server/package.json": SERVER_PACKAGE_JSON,
    "server/src/app.js": SERVER_APP_JS,
    "server/src/server.js": SERVER_SERVER_JS,
    "server/.env.example": SERVER_ENV_EXAMPLE,
    "client/package.json": CLIENT_PACKAGE_JSON,
    "client/vite.config.js": CLIENT_VITE_CONFIG,
    "client/index.html": CLIENT_INDEX_HTML,
    "client/src/main.jsx": CLIENT_MAIN_JSX,
    "client/src/App.jsx": CLIENT_APP_JSX,
    "client/src/index.css": CLIENT_INDEX_CSS,
}


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
        Return the project's Git repo, initializing and scaffolding it on first
        use. Also backfills any missing runnable-scaffold files (Express
        server, Vite+React client) into an already-existing repo -- see
        _backfill_scaffold for why this matters even for repos created before
        the scaffold existed -- and backfills scaffold *upgrades* (security
        middleware, DB connection bootstrap, error handling) into a repo
        scaffolded before those existed -- see _backfill_scaffold_upgrades.
        """
        repo_path = self._repo_path(project_id)

        if (repo_path / ".git").exists():
            repo = Repo(repo_path)
            self._backfill_scaffold(repo, repo_path)
            self._backfill_scaffold_upgrades(repo, repo_path)
            return repo

        repo_path.mkdir(parents=True, exist_ok=True)
        repo = Repo.init(repo_path, initial_branch=MAIN_BRANCH)

        (repo_path / ".gitignore").write_text(SCAFFOLD_GITIGNORE, encoding="utf-8")
        (repo_path / "package.json").write_text(ROOT_PACKAGE_JSON, encoding="utf-8")

        for relative_path, content in SCAFFOLD_FILES.items():
            file_path = repo_path / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        repo.index.add([".gitignore", "package.json", *SCAFFOLD_FILES.keys()])
        repo.index.commit("Initial project scaffold: runnable Express server + Vite/React client")

        return repo

    def _backfill_scaffold(self, repo: Repo, repo_path: Path) -> None:
        """
        Add any scaffold file that's missing from the currently checked-out
        branch's working tree, without touching anything already there.

        This exists because a project's repo may have been created before
        this scaffold was introduced (or before a given scaffold file was
        added to it) -- without this, an old repo is permanently stuck with
        whatever bare-bones state ensure_project_repo used to create, since
        that method previously only ran its scaffolding logic once, at
        Repo.init time.

        Deliberately does NOT force a checkout to main first: it commits onto
        whatever branch is currently active. Called from start_feature_branch
        before that method's own checkout(MAIN_BRANCH), so the common case
        (repo idle on main between features) backfills main directly; called
        mid-coding-loop (build_coder_tools) it backfills the feature branch,
        which then carries the fix into main on the next merge either way.
        """
        missing = {
            relative_path: content
            for relative_path, content in SCAFFOLD_FILES.items()
            if not (repo_path / relative_path).exists()
        }

        changed_paths = list(missing.keys())

        for relative_path, content in missing.items():
            file_path = repo_path / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        if self._backfill_root_package_json(repo_path):
            changed_paths.append("package.json")

        if not changed_paths:
            return

        repo.index.add(changed_paths)
        repo.index.commit("Backfill missing runnable-scaffold files")

    def _backfill_root_package_json(self, repo_path: Path) -> bool:
        """
        Merge the root install:all/dev/build scripts and the concurrently
        devDependency into an existing root package.json, without touching
        any dependencies a pre-scaffold project may have declared there.

        This is separate from SCAFFOLD_FILES because the root package.json
        isn't a create-if-missing file -- ensure_project_repo guarantees it
        always exists, so the only thing that can be missing here is its
        scripts (e.g. a repo created before this scaffold existed at all).
        """
        return self._merge_package_json(
            repo_path / "package.json",
            scripts={
                "install:all": "npm install --prefix server && npm install --prefix client",
                "dev": 'concurrently "npm run dev --prefix server" "npm run dev --prefix client"',
                "build": "npm run build --prefix client",
            },
            dev_dependencies={"concurrently": "^8.2.2"},
        )

    def _merge_package_json(
        self,
        package_json_path: Path,
        scripts: dict[str, str] | None = None,
        dependencies: dict[str, str] | None = None,
        dev_dependencies: dict[str, str] | None = None,
    ) -> bool:
        """
        Add any of the given scripts/dependencies/devDependencies that are
        missing from an existing package.json, leaving everything else
        (including any already-present entry with the same key) untouched.
        Returns True if the file was changed.

        Purely additive, never destructive -- safe to call on a file that a
        feature has already customized, unlike the fingerprint-based
        wholesale-replace path used for app.js/server.js (a dependency list
        has no equivalent notion of "this line must come before that line,"
        so a plain dict merge is always safe here).
        """
        try:
            data = json.loads(package_json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False

        changed = False

        for section, entries in [
            ("scripts", scripts),
            ("dependencies", dependencies),
            ("devDependencies", dev_dependencies),
        ]:
            if not entries:
                continue

            existing = data.setdefault(section, {})
            for name, value in entries.items():
                if name not in existing:
                    existing[name] = value
                    changed = True

        if not changed:
            return False

        package_json_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return True

    def _backfill_scaffold_upgrades(self, repo: Repo, repo_path: Path) -> None:
        """
        Upgrade an already-scaffolded repo with security/DB/error-handling
        middleware added to the scaffold template after that repo was first
        created, without clobbering feature-specific customization already
        layered on top (e.g. a real feature's router mounted into app.js).

        Unlike _backfill_scaffold (pure file-existence check), the files
        touched here already exist in any repo scaffolded before this
        upgrade shipped, so "missing" never fires. Uses content
        fingerprinting instead: a file that still matches its own frozen
        legacy template exactly is provably untouched and gets replaced
        wholesale; anything else is assumed customized and gets targeted,
        anchor-based insertions instead (see _upgrade_server_app_js).
        """
        changed_paths: list[str] = []

        app_js_path = repo_path / "server" / "src" / "app.js"
        if app_js_path.exists() and self._upgrade_server_app_js(app_js_path):
            changed_paths.append("server/src/app.js")

        server_js_path = repo_path / "server" / "src" / "server.js"
        if server_js_path.exists() and self._upgrade_server_server_js(server_js_path):
            changed_paths.append("server/src/server.js")

        server_package_json_path = repo_path / "server" / "package.json"
        if server_package_json_path.exists() and self._merge_package_json(
            server_package_json_path,
            dependencies={"helmet": "^7.1.0", "express-rate-limit": "^7.4.0"},
        ):
            changed_paths.append("server/package.json")

        if not changed_paths:
            return

        repo.index.add(changed_paths)
        repo.index.commit(
            "Backfill scaffold upgrades: security middleware, DB connection, error handling"
        )

    def _upgrade_server_app_js(self, path: Path) -> bool:
        """
        Add helmet, rate limiting, a FEATURE_ROUTES marker pair, and a
        catch-all error handler to an existing server/src/app.js.

        Wholesale-replaces the file only if it's provably still the exact,
        untouched original scaffold. Otherwise anchors targeted insertions
        on `const app = express();` (guaranteed present -- nothing in this
        file works without it) and `module.exports = app;` (guaranteed
        present -- server.js's require("./app") depends on it), which stay
        valid regardless of whatever a feature has already added in
        between (e.g. a mounted router).
        """
        content = path.read_text(encoding="utf-8")

        if content == _LEGACY_SERVER_APP_JS_V1:
            path.write_text(SERVER_APP_JS, encoding="utf-8")
            return True

        if "const app = express();" not in content or "module.exports = app;" not in content:
            logger.warning(
                "server/src/app.js has diverged too far from the scaffold template to "
                "safely auto-upgrade (missing a required anchor line) -- skipping."
            )
            return False

        updated = content

        if "helmet" not in updated:
            updated = updated.replace(
                "const app = express();",
                'const helmet = require("helmet");\nconst app = express();\napp.use(helmet());',
                1,
            )

        if "FEATURE_ROUTES_START" not in updated:
            updated = updated.replace(
                "module.exports = app;",
                "// FEATURE_ROUTES_START\n// FEATURE_ROUTES_END\n\nmodule.exports = app;",
                1,
            )

        if "express-rate-limit" not in updated:
            updated = updated.replace(
                "module.exports = app;",
                'const rateLimit = require("express-rate-limit");\n'
                "const apiLimiter = rateLimit({\n"
                "  windowMs: 15 * 60 * 1000,\n"
                "  max: 100,\n"
                "  standardHeaders: true,\n"
                "  legacyHeaders: false,\n"
                "});\n"
                'app.use("/api/", apiLimiter);\n\n'
                "module.exports = app;",
                1,
            )

        if "err.stack" not in updated:
            updated = updated.replace(
                "module.exports = app;",
                "app.use((err, req, res, next) => {\n"
                "  console.error(err.stack);\n"
                "  const status = err.status || 500;\n"
                '  res.status(status).json({ error: { message: err.message || "Internal Server Error" } });\n'
                "});\n\n"
                "module.exports = app;",
                1,
            )

        if updated == content:
            return False

        path.write_text(updated, encoding="utf-8")
        return True

    def _upgrade_server_server_js(self, path: Path) -> bool:
        """
        Add a guarded mongoose.connect(...) startup step to an existing
        server/src/server.js. Wholesale-replaces only if the file is
        provably still the exact, untouched original scaffold; otherwise
        skips (logging a warning) rather than risk corrupting a boot
        sequence a feature has already customized -- unlike app.js's
        stable require/export anchors, a hand-modified server.js has no
        equally reliable universal insertion point to anchor on.
        """
        content = path.read_text(encoding="utf-8")

        if content == _LEGACY_SERVER_SERVER_JS_V1:
            path.write_text(SERVER_SERVER_JS, encoding="utf-8")
            return True

        if "mongoose.connect" in content:
            return False

        logger.warning(
            "server/src/server.js has already been customized and does not call "
            "mongoose.connect -- skipping automatic DB-connection backfill; add it "
            "manually if this project needs one."
        )
        return False

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

        return {**self._parse_name_status(name_status), "diff_text": diff_text}

    def get_touched_files(self, project_id: str, feature_id: str) -> dict[str, list[str]]:
        """
        Return {"added": [...], "modified": [...], "deleted": [...]} comparing
        the feature branch's CURRENT WORKING TREE (including uncommitted,
        even still-untracked changes) against main's tip.

        Unlike diff_against_main's committed-history-only triple-dot
        comparison, this is accurate mid-coding-loop, before commit_changes
        has run -- which is what makes it usable as a self-check tool
        during an agentic attempt (list_unimplemented_planned_files),
        not only after the loop has already finished.

        Stages everything first (git add -A) so a brand-new file the coding
        loop just wrote via write_file, still untracked, is correctly seen
        as "added" -- a plain `git diff <ref>` silently ignores untracked
        files entirely. This mirrors exactly what commit_changes will do
        moments later regardless, so it introduces no new inconsistency.
        """
        repo = self.ensure_project_repo(project_id)
        branch_name = self._feature_branch_name(feature_id)

        if repo.active_branch.name != branch_name:
            repo.git.checkout(branch_name)

        if repo.is_dirty(untracked_files=True):
            repo.git.add(A=True)

        name_status = repo.git.diff("--cached", MAIN_BRANCH, "--name-status")
        return self._parse_name_status(name_status)

    def _parse_name_status(self, name_status: str) -> dict[str, list[str]]:
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

        return {"added": added, "modified": modified, "deleted": deleted}

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
