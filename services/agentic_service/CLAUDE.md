# Auto-Forge MAS — UI/UX + Coder Agent Build — Working Notes

This file is durable cross-milestone memory for the build described in
`instructions .md`. Read it before continuing this build in a new session —
it records real decisions, deviations from the spec, and gotchas discovered
during implementation that the original spec doesn't (and can't) know about.

The per-milestone implementation plan lives at
`C:\Users\ASUS\.claude\plans\soft-petting-star.md` and gets overwritten each
milestone — that file is scratch, **this file is the durable one**.

## Status

| Milestone | Status |
|---|---|
| M0 — Foundation (enums, workspace/sandbox/project-memory services, graph orchestrator) | DONE |
| M1 — UI/UX Agent steps 1-3 (metadata modeling + coverage validation) | DONE |
| M2 — UI/UX Agent steps 4-8 (component gen, preview rendering, artifacts, design system persistence) | DONE |
| M3 — Coder Agent planning (plan_node + plan_validator + tools) | DONE |
| M4 — Coder Agent loop (create_agent + tools, manual run) | DONE |
| M5 — Coder Agent verification + diff + merge | DONE |
| M6 — Full graph wiring (real uiux_node/coder_node) | DONE |
| M7 — Security/QA placeholders | DONE |
| M8 — Second feature (Signup) proving reuse | not started |

## Environment facts (verified, not assumed — re-check if anything seems off)

- **MongoDB is a real Atlas cluster**, not localhost — `.env`'s `MONGODB_URI` overrides the
  `localhost` default in `config.py`. The real project **"E-commerce Platform"**
  (`proj_a2e3d529`) / feature **"Login"** (`feature_a44033b8`) already has: approved SRS v3,
  approved Architecture Plan v5 (saved under the **legacy `sds` artifact type**, not the newer
  `architecture_plan` type — both are handled via fallback lookup), approved UI/UX v1
  (`ui_metadata` + the `LoginForm.jsx` component, both approved).
- **Default LLM model is `qwen3-coder:latest` via Ollama**, not `gemma4` — changed (both live
  Mongo `llm_settings` and `.env` `DEFAULT_LLM_MODEL`) in M1 because `gemma4` could not reliably
  follow the structured JSON schemas the UI/UX and Coder planning prompts require.
- **Agentic (tool-calling) model** is also `qwen3-coder:latest` via
  `app/providers/agentic_model_factory.py` (`AGENTIC_MODEL_OVERRIDE` in `.env`/`config.py`).
- Docker Desktop is installed and used by `sandbox_service` for `run_shell`, but is **not always
  already running** — it does not auto-start with Windows in this environment. If
  `sandbox_service.run_command` returns `exit_code: 1` with `"Sandbox unavailable: could not reach
  Docker daemon"`, that's this, not a code bug: launch
  `C:\Program Files\Docker\Docker\Docker Desktop.exe` and poll `docker version` until it responds
  (took ~10s in practice) before retrying.
- Playwright + Chromium are installed. UI/UX preview rendering uses **vendored UMD bundles**
  (React/ReactDOM/Babel-standalone/Tailwind CDN script) at `app/agents/uiux_agent/vendor/` and a
  static HTML shell — **not** a Vite dev server. Gotcha: the babel `<script type="text/babel">`
  tag must **not** have a `data-presets="react"` attribute — adding it breaks rendering under
  `file://` navigation (Chromium treats Babel's transform output as an ES module, which is
  blocked by CORS under `file://`). Default (no `data-presets`) works fine and still handles JSX.
- System `rg` (ripgrep) is **not installed** and not installable without admin in this
  environment — `search_code` (Coder Agent tool) uses a pure-Python regex line-walker instead,
  capped at 200 results.
- `requirements.txt` periodically reverts to UTF-16 encoding on disk for unclear reasons (not
  something my edits cause directly). If `Edit` fails with "string not found" on this file,
  re-`Read` it fresh, decode if needed, and `Write` the whole file back as UTF-8.

## Key deviations from `instructions .md` (and why)

1. Graph orchestrator (M0) stage nodes are plain pass-through functions, not calls into real
   agents — intentional, matches the roadmap's own intent that M6 is when real agents get wired
   into the graph.
2. Security/QA graph stages are already auto-approved pass-through nodes with no human
   `interrupt()` (anticipating M7) — no `security_agent`/`qa_agent` stub *modules* exist yet,
   only the graph nodes; M7 adds the actual stub classes.
3. Added `ArtifactType.UI_INTEGRATION_MANIFEST` (not in the doc's original enum list). Reusing
   `UI_METADATA` for both the metadata JSON and the integration manifest created a real
   ambiguity for any future lookup (`apply_design_system_patch`, future Coder Agent context
   loading) — caught during M2 testing, fixed properly rather than patched around.
4. UI/UX component generation uses a **delimited text format**
   (`---MOCK_PROPS_JSON---` / `---JSX_CODE---`), not JSON with an embedded multi-line code
   string — avoids JSON-escaping failures for real JSX source text.
5. `design_system.json` persistence (UI/UX step 7) is triggered from
   `approval_service.submit_approval` directly (checks `agent_name=uiux_agent` +
   `artifact_type=UI_METADATA` + approved), **not** from the graph node — the real `uiux_node`
   doesn't exist until M6, so this hook had to live somewhere that already fires today.
6. Coder Agent tools (M3) are built by a per-run factory `build_coder_tools(project_id,
   feature_id)`, not bare module-level `@tool` functions — required because every tool's
   LLM-facing signature (per the doc itself) takes no `project_id` argument, so each tool must
   already be bound to one workspace (and one feature's approved UI components) at construction
   time.
7. **`langgraph.prebuilt.create_react_agent` is deprecated** in the installed version (moved to
   `langchain.agents.create_agent`) — M4 uses `create_agent` instead, per the doc's own explicit
   instruction to use whichever API is current. Signature/behavior is equivalent for this
   build's purposes (`model`, `tools`, `system_prompt=`, state keyed on `"messages"`).
8. **Added `workspace_service.commit_changes(project_id, feature_id, message)`** (not in the
   original doc's `workspace_service` method list). The coding loop's tools only ever touch the
   working tree, never git — `diff_against_main()`/`merge_feature_branch()` both operate on
   *committed* history, so without an explicit commit step between "the agentic loop finished"
   and "there is a diff to review," `diff_against_main()` silently returns an empty diff even
   though real files were written (confirmed directly: `git status`/`find` showed all 6 real
   files on disk while `diff_against_main()` reported `added: []`). M5's `diff_node` should call
   `commit_changes(...)` right after the coding loop (or after `verify_node` passes) and before
   computing the diff.
9. **M5's `verify_node` skips (doesn't fail) a build/lint/test script that isn't defined in
   `package.json`** — user decision, since the real project has zero build tooling scaffolded
   yet (see below). Only a script that exists and returns nonzero, or `npm install` itself
   failing, is a hard failure.
10. **`CoderAgentInput`/`CoderAgentOutput` (`coder_agent/schemas.py`) were rewritten** from the
    original artifact-ID-based sketch to the already-loaded-context shape, matching
    `ArchitectureAgentInput`/`UIUXAgentInput`'s established convention (same change UI/UX went
    through between its stub and M1). `CoderAgentOutput` kept its original 5 fields and gained
    `code_plan_json`, `verification_passed`, `artifact_ids`.
11. **`ArtifactType.CODE_DIFF` is the merge-gating artifact type** for the Coder Agent (shared
    across both `file_tree_json` (JSON format) and `merge_report_markdown` (MARKDOWN format), same
    pattern as `UI_METADATA`). `approval_service.py`'s Coder Agent hook triggers
    `merge_approved_feature`/`discard_rejected_feature` on this type regardless of format.
12. **M6: `domain` moved from `GATED_STAGES` to `AUTO_APPROVED_STAGES`** in
    `graph_orchestrator_service.py`, joining `security`/`qa`. This was a real, pre-existing gap,
    not a new decision invented for M6: with `domain` gated, the graph would pause at
    `approve_domain` forever with no Domain Agent artifact a human could ever approve through the
    normal `POST /artifacts/{id}/approval` flow (there is no way to advance except calling
    `resume()` directly, bypassing the approval system entirely). `STAGE_SEQUENCE` (the true
    pipeline order, used for edge-wiring) is now separate from `GATED_STAGES` (which stages get a
    real `approve_*` node) -- previously these were conflated via `GATED_STAGES + AUTO_APPROVED_STAGES`
    concatenation, which only worked because auto-approved stages happened to all be at the end.
13. **M6: `uiux_node`/`coder_node` are real calls, bridged from sync graph-node functions into the
    async `UIUXAgent.run()`/`CoderAgent.run()` via `asyncio.run(...)`**, not by converting the
    graph/orchestrator/approval chain to async. This works because every current caller of
    `graph.invoke()`/`resume()` is a sync FastAPI route handler running in a worker thread with no
    event loop already active -- **if that ever changes (a route becomes `async def` and calls the
    orchestrator directly on the main event loop thread), this bridge breaks** and needs to become
    a threadsafe one (`asyncio.run_coroutine_threadsafe`). Documented directly in the node
    docstrings so this assumption isn't silently invalidated later.
14. **Discovered, not designed**: when a graph node raises (e.g. `coder_node`'s
    `CodePlanValidationError`), LangGraph's checkpoint stays at "this node is next" rather than
    either corrupting state or silently advancing past the failure -- confirmed directly
    (`get_status()` returned `next: ["coder_node"]` after the real failure below). A future
    `resume()` call would cleanly retry the same node from scratch. This is a genuinely useful
    emergent property, not something built -- worth knowing before assuming a failed node needs
    manual checkpoint surgery to recover from.
15. **`approval_service.py`'s existing broad `except Exception` around the graph-resume call
    (added in M0 to swallow `GraphNotRunningError` for artifacts approved outside a graph run)
    turns out to also correctly handle "the graph run failed downstream" for free**: when
    `coder_node` raised `CodePlanValidationError` during the real M6 end-to-end test, the human's
    `POST /artifacts/{id}/approval` call still returned its normal 200 OK (their approval action
    genuinely succeeded) while the failure was logged separately
    (`logger.exception("Failed to resume graph run...")`), not silently lost and not surfaced as a
    misleading 500 to someone who did nothing wrong. Worth keeping in mind if this error handling
    is ever "tightened" -- the current broad catch is load-bearing for more than its original
    purpose.
16. **M7: `app/agents/security_agent/` and `app/agents/qa_agent/` created**, matching the exact
    stub convention `deployment_agent/` already used (`agent.py`/`prompt.py`/`schemas.py`, no
    `__init__.py` -- matches every stub agent, not just the two implemented ones which happen to
    have one). Both `SecurityAgent.run()`/`QAAgent.run()` are `async def` returning
    `{"status": "skipped", "message": "... not yet implemented."}` verbatim per the doc's own
    snippet. `graph_orchestrator_service.py`'s `security_node`/`qa_node` now call these real
    (still-placeholder) classes via the same `asyncio.run()` bridge pattern `uiux_node`/
    `coder_node` established in M6, instead of the generic M0 pass-through function -- behavior is
    identical (auto-approved, no gate, no artifacts), but the graph now has real node targets to
    route to per the doc's Milestone 7 instruction, so implementing these agents for real later
    only means changing their own `agent.py` internals, not touching the graph again.
17. **Post-M8: Coder Agent output was not actually runnable — fixed with a deterministic
    Express+Vite scaffold.** The user reported directly (independent of the milestone plan) that
    generated projects had no way to actually run: the backend had no Express app at all, the
    frontend had no Vite/React project at all. Root cause: `workspace_service.ensure_project_repo`
    only ever created empty `client/`/`server/` folders with `.gitkeep` files and a bare root
    `package.json` (name/private only -- no deps, no scripts) -- every feature's entire runnable
    skeleton (package.json deps/scripts, `vite.config.js`, entrypoints, Express bootstrap) was
    left for the LLM planner + coding loop to invent from scratch every run, and the planner was
    already documented (below) as unreliable even at planning backend *route* files, let alone
    scaffold-level infrastructure. `verify.py` also never actually proved anything ran: it only
    checked for `build`/`lint`/`test` scripts in the **root** `package.json` (never populated)
    and silently skipped if absent. Confirmed against the real, already-merged Login feature
    before fixing: `server/` had `routes/auth.routes.js` and `models/UserCredentials.js` but no
    `app.js`/`server.js`/`package.json`; `client/` had `components/LoginForm.jsx`,
    `pages/LoginPage.jsx`, `services/authService.js` but no `main.jsx`/`App.jsx`/`index.html`/
    `vite.config.js`/`package.json` -- exactly the reported bug. Fix:
    - `workspace_service.py`: `SCAFFOLD_FILES` now defines a real, working MERN skeleton --
      `server/package.json` (express, cors, dotenv, mongoose, nodemon; `start`/`dev` scripts),
      `server/src/app.js` (Express app: cors, json body parsing, `/api/health`, exports `app`
      for routers to be `app.use(...)`'d onto), `server/src/server.js` (`app.listen`),
      `server/.env.example`; `client/package.json` (react, react-dom, react-router-dom, vite,
      `@vitejs/plugin-react`; `dev`/`build`/`preview` scripts), `client/vite.config.js`,
      `client/index.html`, `client/src/main.jsx` (renders `<App/>` inside `<BrowserRouter>`),
      `client/src/App.jsx` (a `<Routes>` tree new pages get added to), `client/src/index.css`.
      Root `package.json` gets real `install:all`/`dev`/`build` scripts (via `concurrently`) so
      `npm run install:all && npm run dev` actually boots both sides.
    - **Idempotent backfill, not just first-init**: `ensure_project_repo` now calls
      `_backfill_scaffold` on every call (not just at `Repo.init` time), which adds any
      `SCAFFOLD_FILES` entry missing from whatever branch is currently checked out (without
      touching anything already there) and separately merges the root `install:all`/`dev`/`build`
      scripts + `concurrently` devDependency into an existing root `package.json` via
      `_backfill_root_package_json` (parses/merges/rewrites JSON, preserves any dependencies
      already declared there). This is what let the already-in-progress, already-merged
      `e-commerce-platform` project (not just brand-new projects) get retrofitted automatically
      just by calling `ensure_project_repo` again -- no migration script, no special-casing.
      Deliberately does not force a `git checkout main` first -- it commits onto whatever branch
      is active, so the common case (repo idle on `main` between features) backfills `main`
      directly, and a mid-coding-loop call (`build_coder_tools` also calls `ensure_project_repo`)
      backfills the feature branch, which still reaches `main` on the next merge either way.
    - `prompt.py`'s `CODE_PLANNER_SYSTEM_PROMPT` gained hard rule 9: the scaffold already exists
      and works, do not re-plan it; to add a route, plan a "create" for the new router file AND
      a "modify" on `server/src/app.js` to `require`+`app.use(...)` it; to add a page, plan a
      "create" for the page AND a "modify" on `client/src/App.jsx` to add its `<Route>`. This is
      unconditional (in the system prompt, not the user-prompt context built from
      `project_manifest_json`), so it holds even for a project's very first feature, when the
      manifest is still empty.
    - `verify.py` was rewritten: `npm install` now always runs in both `server/` and `client/`
      (their `package.json` always exist thanks to the scaffold, regardless of whether
      `code_plan_json.new_dependencies` is empty), plus two new hard, non-skippable checks --
      `SERVER_BOOT_SMOKE_TEST_COMMAND` (backgrounds `node src/server.js`, polls `/api/health`
      using Node's own `fetch`, not `curl` -- `node:20-slim` has no `curl`, same root cause as
      the already-documented missing-`git` gotcha below -- then kills the server; nonzero exit
      is a hard failure) and a client build check (`npm run build` in `client/`, i.e. a real
      `vite build`). `lint`/`test` remain skip-if-absent (root `package.json` only) since no
      such tooling is scaffolded.
    - `diff_builder.py`'s `build_setup_instructions_markdown` now always shows the real
      `npm run install:all` / `npm run dev` commands (previously: nothing at all unless the
      plan happened to declare `new_dependencies`/`env_vars_needed`).
    - **Real fix applied to the actual `e-commerce-platform` project**, not just new projects:
      called `ensure_project_repo` to backfill the scaffold onto `main`, then hand-wired the
      already-merged Login feature into it (one-time, deterministic, not LLM-authored -- mirrors
      exactly what the updated planner prompt now instructs for every future feature):
      `server/src/app.js` now `require`s and `app.use("/api/auth", ...)`s the existing
      `auth.routes.js`; `client/src/App.jsx` now imports and routes `/login` to the existing
      `LoginPage`. Also relocated `bcrypt`/`jsonwebtoken` (used by `auth.routes.js`/
      `UserCredentials.js`, previously installed flat at the repo root with no script to ever
      run them) into `server/package.json`, and `axios`/`jwt-decode` (used by `authService.js`)
      into `client/package.json`. Verified for real: `coder_verifier.verify()` against this
      exact project -- `npm install (server)`: passed (135 packages), `npm install (client)`:
      passed (91 packages), `server boot (curl /api/health)`: passed (Express actually boots
      with the real Login routes mounted), `client build (vite build)`: passed (36 modules,
      including `LoginForm`/`LoginPage`/`authService`, actually compile). `result["passed"]`:
      `True`. Resulting lockfiles and the wiring commit are real, intentional state on `main`
      (see "Real state changes" below), not test debris.
    - Tests: `tests/test_workspace_scaffold.py` (new -- scaffold presence, git commit, backfill
      of a missing file without touching existing customizations, backfill of root-package.json
      scripts without touching existing dependencies, idempotency), `tests/test_coder_verify.py`
      (rewritten -- server/client-scoped installs, hard boot/build checks including a deliberately
      broken `app.js` producing a hard failure, root lint/test still skip-if-absent),
      `tests/test_coder_diff_builder.py` (setup-instructions assertions updated for the new
      always-present run commands). Full suite: 83 passed.
    - **Known remaining gap, not fixed by this change**: `authService.js` (generated before this
      fix, untouched by it) reads `process.env.REACT_APP_API_BASE_URL` -- a Create-React-App-style
      env var that does not exist under Vite (Vite exposes `import.meta.env.VITE_*` instead).
      This does not break `vite build` (the reference is never evaluated at bundle time, and the
      `||` fallback provides a working default that happens to match the scaffold's port 5000),
      but it would throw `ReferenceError: process is not defined` if that code path actually ran
      in a browser with that env var set. Not fixed here -- it's a pre-existing LLM-generated-
      code correctness bug, a different concern from "is there a scaffold to run it in at all,"
      and out of this fix's scope.
18. **Post-scaffold-fix: Coder Agent output was "partially implemented," not accurate/complete --
    fixed with tighter intra-loop verification, deterministic post-code checks, and prompt
    hardening (Upgrade 2 of 2; Upgrade 1, per-agent multi-provider LLM config, is a separate,
    not-yet-started follow-up -- see below).** The user reported the real, already-merged Login
    feature was broken in ways a human had to discover by hand: `LoginForm.jsx` never actually
    rendered (its markup was gated on `props.state`, which `LoginPage.jsx` never passed --
    literally invisible in the running app), its submit handler hardcoded a fake
    `setTimeout`-based credential check instead of calling the real, already-written
    `authService.js` (100% dead code as a result), `/forgot-password`/`/reset-password` were
    non-functional stubs ("in a real app, you would..." comments), and **no file anywhere called
    `mongoose.connect(...)`** despite `mongoose` being a dependency and models being defined --
    the DB was never actually connected. Root cause, confirmed by reading the actual pipeline
    code: verification only ever ran *after* the whole agentic coding loop declared itself done,
    against a brand-new agent instance each retry with zero memory of the previous attempt
    (`CoderAgent._code_with_retries` rebuilding `build_coder_react_agent` from scratch every
    time); nothing checked that every planned file was actually touched before the loop was
    allowed to stop (purely self-reported completion); the one self-check tool the system prompt
    already encouraged (`git status`/`git diff`) silently failed with exit 127 because
    `node:20-slim` has no `git` binary; and `verify.py` (even after the scaffold fix) only ever
    proved the app *boots and builds*, never that any specific planned endpoint was actually
    implemented rather than left as an unreachable stub.
    - `workspace_service.py` (`SCAFFOLD_FILES` templates): `SERVER_APP_JS` gained `helmet()`,
      an `express-rate-limit` limiter on `/api/`, a `// FEATURE_ROUTES_START` /
      `// FEATURE_ROUTES_END` marker pair (a stable `apply_patch` anchor for every future
      feature's router-mount line, regardless of how large the file grows), and a catch-all
      Express error-handling middleware; `SERVER_SERVER_JS` gained a **guarded**
      `mongoose.connect(process.env.MONGODB_URI)` (skips cleanly with a `console.warn` if the
      env var isn't set -- the sandbox's Docker containers never see host env vars, so this
      guard is what keeps the boot smoke test passing for every feature, not just DB-backed
      ones); `SERVER_PACKAGE_JSON` gained `helmet`/`express-rate-limit` deps. New
      `_backfill_scaffold_upgrades`/`_upgrade_server_app_js`/`_upgrade_server_server_js`: since
      these files already exist in any repo scaffolded before this upgrade, existence-based
      backfill (`_backfill_scaffold`) can't detect what's missing -- content **fingerprinting**
      does instead: a file that still matches its own frozen legacy template
      (`_LEGACY_SERVER_APP_JS_V1`/`_LEGACY_SERVER_SERVER_JS_V1`) exactly is provably untouched
      and gets replaced wholesale; anything else (e.g. the real e-commerce-platform's `app.js`,
      which already had Login's router mounted) gets **targeted, anchor-based insertions**
      instead, anchored on `const app = express();` and `module.exports = app;` (the two lines
      guaranteed present in every version of this file) so it's safe regardless of whatever a
      feature has already added in between. `_merge_package_json` is a new, generic, purely
      additive dict-merge helper, refactored out of the pre-existing `_backfill_root_package_json`
      and reused for `server/package.json` too.
    - **Sandbox image swap**: `docker/coder-sandbox.Dockerfile` (new) builds
      `autoforge-coder-sandbox:latest` from `node:20` (not `-slim`, which ships without `git` --
      confirmed root cause of the already-documented `git status`/`git diff` exit-127 gotcha)
      plus a globally-installed `@babel/parser` (with `NODE_PATH=/usr/local/lib/node_modules` so
      a plain `require()` from any cwd can actually find it -- npm's global install location
      isn't on Node's default require search path otherwise, a real gotcha hit while building
      this). `sandbox_service.SANDBOX_IMAGE` now points at this custom tag. Full suite re-run
      immediately after the swap to catch any regression from the larger base image -- none
      found.
    - **New self-check tools** (`app/agents/coder_agent/tools.py`, `build_coder_tools` gained an
      optional `code_plan_json` parameter): `list_unimplemented_planned_files` -- computes
      touched files from **git**, via new `workspace_service.get_touched_files(project_id,
      feature_id)` (compares the feature branch's current working tree, including still-
      untracked writes, against main's tip -- correct mid-loop, before `commit_changes` has run,
      unlike the existing `diff_against_main`'s committed-history-only triple-dot comparison),
      and reports any planned file not yet created/modified/deleted -- the model is told to call
      this before ending its turn, so plan completeness stops being self-reported.
      `check_syntax` -- runs `node --check` (`.js`) or a `@babel/parser` JSX parse (`.jsx`) on a
      single file inside the sandbox, giving fast, cheap per-file feedback instead of waiting for
      the next full install/build cycle to surface a typo.
    - **`route_checker.py`** (new module): `check_route_coverage` -- best-effort, regex-based
      static check that a planned backend file's endpoint (`maps_to` entries starting with `/`)
      actually has a matching route registration in that file, resolving the file's mount prefix
      by cross-referencing `app.js`'s `require(...)`/`app.use(prefix, binding)` pairs against the
      file's own relative route registrations (e.g. `router.post('/login', ...)` mounted at
      `/api/auth` correctly resolves to `/api/auth/login`). Explicitly a heuristic (regex, not a
      real router/AST analysis) -- documented as such in the module docstring. `verify.py` now
      runs this as a new **hard** gate ("endpoint route coverage"). `scan_for_placeholder_stubs`
      -- phrase-based scan (`"in a real app"`, `"not implemented"`, `"TODO"`, `"for now"`, etc.)
      of every touched file, wired in as a new **informational-only** step ("placeholder-stub
      scan", a new `"info"` status that never affects `passed`) -- deliberately not a hard gate,
      since these phrases are common enough in legitimate comments that blocking on them would be
      too false-positive-prone; it exists purely so a human reviewer sees it.
      `diff_builder.build_merge_report_markdown` previously only ever printed each verify step's
      `name`/`status`, silently dropping `output` -- now also renders `output` for `failed`/`info`
      steps specifically, otherwise the new placeholder-stub findings (informational by design)
      would be invisible in the human-facing report.
    - **`agent.py`'s `_code_with_retries`**: new pre-verify gate -- after `commit_changes`, before
      the expensive `verifier.verify(...)` call (2x `npm install`, server boot, `vite build`),
      deterministically diff the plan's file list against `workspace_service.get_touched_files`
      (new `_find_plan_gaps`/`_format_plan_gaps` helpers); if anything's missing, skip `verify()`
      entirely for this attempt and feed back the precise list of untouched files. **Targeted
      retries**: `coding_loop.build_task_message` gained an `already_touched` parameter -- a
      retry's task message now lists exactly which files already exist from the previous attempt
      (`"do not redo unless the failure below specifically points at them"`), so a fresh agent
      instance (each attempt still starts with zero memory of the last one, by design -- this
      pass did not change that) at least starts with better situational awareness instead of a
      fully generic re-prompt. `verify()`'s signature gained a required `feature_id` parameter
      (needed for `get_touched_files`) -- every call site and test updated.
    - **`CODER_AGENT_SYSTEM_PROMPT` hardening** (`prompt.py`), directly targeting the exact
      anti-patterns found in the real Login feature: never wire a handler to hardcoded/fake logic
      when a real service module exists to call instead; never leave placeholder-stub logic
      without explicitly naming it, by file, in the final summary; always validate required
      `req.body` fields before use (400 on missing/malformed); when rendering a component you
      didn't author (e.g. via `read_ui_component`), read its actual prop usage and wire every
      prop its logic depends on -- don't render it with zero props and assume it works; call
      `check_syntax` after every `.js`/`.jsx` write/patch and `list_unimplemented_planned_files`
      before ending the turn. The planner prompt's rule 9 (scaffold-awareness, from the prior
      milestone) gained an addendum: patch the `// FEATURE_ROUTES_END` marker specifically, never
      `module.exports = app;` directly. `CODING_LOOP_RECURSION_LIMIT` bumped 50 -> 65 to
      accommodate the new self-check tool calls without prematurely hitting the cap on otherwise-
      legitimate work.
    - **Real E2E test**: with a fresh `autoforge-coder-sandbox` image and all of the above live,
      approved the previously-pending Signup UI/UX v2 (see item 17's LoginForm-reuse-fix context)
      through the real approval endpoint, which resumed the real LangGraph run straight into the
      real `coder_node` for `feature_f74fb38a` (Signup) against the real e-commerce-platform
      project. Notable, real findings:
      - The real planner **passed `plan_validator` on the first attempt** for this feature (a
        `modify`-only plan against the already-existing `auth.routes.js`/`UserCredentials.js` --
        simpler than Login's from-scratch backend, and the first time in this project's history
        the real planner has driven a `CoderAgent.run()` past planning unattended). The
        already-documented from-scratch backend-under-planning gotcha (below) is unchanged/still
        open -- this one case succeeding doesn't contradict it.
      - The generated `/api/auth/signup` route genuinely validates required fields
        (`if (!email || !password || !fullName) return res.status(400)...`), checks for an
        existing user before creating one, and issues a JWT on success -- directly reflecting the
        new "validate `req.body` before use" prompt rule, and a real, concrete quality
        improvement over the original Login route (which had zero such validation).
      - `endpoint route coverage`: passed (the new checker correctly resolved `/api/auth/signup`
        against `auth.routes.js`'s `router.post('/signup', ...)` via `app.js`'s mount prefix).
      - `placeholder-stub scan`: correctly surfaced the **pre-existing** (from the original Login
        feature, untouched by this run) forgot/reset-password stub comments as informational
        findings, without blocking -- proof the scan works and correctly doesn't gate on them.
      - All 3 coding attempts nonetheless recorded `verification_passed: False` in the artifacts
        first saved from this run, because the `server boot (curl /api/health)` step failed on
        every attempt with a **false negative**: a real full pytest regression run (also
        Docker-heavy) happened to be running concurrently on this machine, and the original
        10-attempt/~10-second health-check retry window wasn't always enough for a container to
        get scheduled CPU under that contention -- confirmed by re-running the exact same
        `SERVER_BOOT_SMOKE_TEST_COMMAND` against the identical generated code in isolation
        immediately afterward: `exit_code: 0`, passed cleanly. **Fixed**: widened the retry loop
        from 10 attempts/1s apart to 30 (`SERVER_BOOT_TIMEOUT_SECONDS` 30 -> 45 to give the
        container itself enough wall-clock budget too), re-ran `tests/test_coder_verify.py` (9/9
        passed) and the full suite (115/115 passed) to confirm. Re-verified the Signup code a
        second time, fully cleanly (no concurrent load): every step passed, including server
        boot, `endpoint route coverage`, and build. Saved as a fresh, accurate v2 artifact set
        (`CoderAgentOutput` rebuilt deterministically from the *same* already-generated code plus
        this clean `verify_result` -- no re-planning, no re-invoking the LLM, since nothing about
        the actual generated code changed, only the environment's contention) so the artifact a
        human reviews next reflects reality (`verification_passed: True`) rather than the earlier
        contention-confounded false failure. **Lesson for future real-agentic-pipeline testing on
        this machine**: don't run the full Docker-heavy pytest suite at the same time as a real
        end-to-end agent run that also hits the sandbox -- they compete for the same Docker
        daemon and can produce exactly this kind of false negative.
    - Tests: `tests/test_coder_tools.py` (+8: `list_unimplemented_planned_files` gap-detection/
      clearing/no-plan-provided cases, `check_syntax` valid/invalid `.js`/`.jsx`/unsupported-
      extension cases), `tests/test_route_checker.py` (new, 9 tests: mount-prefix resolution,
      missing route, literal full-path match, missing file, non-backend/deleted files ignored,
      no-endpoint-maps_to ignored, placeholder-stub true/true-negative/untouched-file cases, all
      pure `tmp_path`-based, no git/Docker/LLM), `tests/test_coder_verify.py` (+3: route-coverage
      pass/fail, placeholder-stub-is-informational-and-never-fails; fixture now also creates a
      feature and starts its branch, since `verify()` needs `feature_id`), `tests/
      test_coder_diff_builder.py` (+1: failed/info step output surfaced, passed step output
      stays terse), `tests/test_coder_prompt.py` (new, 7 trivial substring-presence tests locking
      in the new hard rules -- these prove the rules are in the prompt text, not that the model
      follows them; the real E2E run above is what proves that). Full suite: **115 passed**
      (up from 87 before this pass), confirmed clean (no concurrent load) after the retry-window
      fix.

## Known model-quality gotchas (not code bugs — prompts already account for these)

- `qwen3-coder:latest` sometimes emits function-valued mock props (e.g. `"onSubmit": () => {}`)
  inside what must be strict JSON. Fixed in `uiux_agent/prompt.py`'s
  `COMPONENT_GENERATOR_SYSTEM_PROMPT` by requiring self-contained components (internal
  `useState`, no callback props expected from outside).
- The Coder Agent planner (M3) reliably plans frontend files correctly but has repeatedly
  under-planned backend routes/models for the same feature, even after explicit "this is
  full-stack, you MUST plan both sides" instructions. `plan_validator` correctly rejects these
  incomplete plans every time it happened (5/5 real attempts across M3+M5) — this is the
  guardrail working as designed, not a bug to silently work around. **M5 implemented and tested
  the retry-with-validator-feedback loop this gotcha called for (`CoderAgent._plan_with_retries`,
  `MAX_PLANNING_ATTEMPTS=2`), and it only partially helps**: given the specific error
  "does not cover these API endpoints: [...]" plus the previous (rejected) plan, the second
  attempt correctly added the missing *data entity* (a `UserCredentials.js` file) but still never
  created an actual backend route file for the missing *endpoints* — it seems to treat a
  frontend `authService.js` that *calls* `/api/auth/login` as if that satisfies "cover this
  endpoint," not understanding it also needs the file that *implements* the endpoint
  server-side. Real end-to-end runs (`CoderAgent.run()`) currently exhaust both planning
  attempts and raise `CodePlanValidationError` for this exact feature every time — this is
  correct, cheap-failure behavior per the design (no workspace touched), but means the real
  planner cannot currently drive a real backend feature through `run()` unattended. The
  hand-validated plan (see `scripts/run_coder_pipeline_manual.py`) remains the way to exercise
  everything downstream of planning until this is improved further (candidates: even more
  explicit endpoint-vs-caller wording, one-shot few-shot example in the prompt, or accepting a
  human-edited plan as a valid input to the pipeline instead of only ever an LLM-generated one).
- The planner is prone to anchoring on the shape of context JSON shown to it (e.g. it once
  echoed the `project_manifest.json` shape back as if it were the required output). Fixed by
  explicitly marking all context as read-only and restating the exact required output schema
  immediately before generation. If a new prompt shows the model a JSON blob right before asking
  for JSON output, watch for this.
- **Ollama's server-side default context window silently truncates long agentic conversations.**
  The very first M4 coding-loop run produced a coherent tool-use trace right up through
  `read_ui_component` (which returns a whole real `.jsx` file, several KB), then a single empty
  final `AIMessage` with no tool calls and no content — the loop just stopped, having written
  zero files. This was **not** model flakiness; it was `ChatOllama` using Ollama's default
  `num_ctx` (historically 2048-4096), which the conversation blew past once a real file's
  contents entered it. Fixed in `app/providers/agentic_model_factory.py` by explicitly setting
  `num_ctx=settings.AGENTIC_OLLAMA_NUM_CTX` (32768, configurable via `.env`) whenever the
  provider is `ollama`. **If a new agentic tool ever returns large content (another full file,
  a big shell command output), re-check this budget** — 32768 is comfortable for the current
  Login feature's tool outputs but isn't unlimited.
- The `node:20-slim` sandbox image (`sandbox_service`) has **no `git` binary** — the coding loop
  tried `run_shell("git status")` at the end of its M4 run and got `exit_code: 127, sh: git: not
  found`. It's on the `run_shell` allowlist (matching the doc's spec) but currently
  non-functional inside the sandbox. The model handled the failure gracefully and finished
  anyway, so this didn't block M4, but **`git status`/`git diff` via `run_shell` will never
  actually work until the sandbox image includes git** (switch to `node:20` instead of
  `-slim`, or install git in a custom image) — worth fixing before any future prompt relies on
  the agent self-checking its own diff via that tool.
- **M4's `jsonwebtoken`-missing bug was fixed in M5's hand-validated plan** (added to
  `new_dependencies`) specifically so M5 could demonstrate a genuinely *passing* verify gate, not
  just a failing one — both matter and both were proven this build: M4 showed the merge-gate
  will faithfully surface a real problem when one exists; M5 shows it lets a real, correct
  change through when `npm install` (the only step that could run, since no build/lint/test
  scripts exist yet) actually succeeds. **Caveat, stated plainly**: because there is still no
  test suite or build step that actually executes `auth.routes.js`, a *future* missing-`require`
  bug in this project would again not be caught until a real test suite exists (M7/QA Agent
  territory) — `npm install` alone only checks that declared dependencies resolve, not that
  the code correctly declares every dependency it uses.
- **Windows: `shutil.rmtree` on a git repo directory reliably fails** with either a
  `PermissionError` from git's read-only object files, or (worse, and non-obvious) "the process
  cannot access the file because it is being used by another process" from GitPython's `Repo`
  object holding an open file handle even after the test using it has gone out of scope. Fixed
  in `tests/test_coder_tools.py`/`tests/test_coder_verify.py` by (1) explicitly calling
  `workspace_service.ensure_project_repo(project_id).close()` before `rmtree`, and (2) passing
  an `onerror` handler that clears the read-only bit and retries. **Any new test that creates a
  real git repo via `workspace_service` needs both of these in its teardown**, or leftover
  `workspaces/*` directories will silently accumulate (this happened once already in M5 --
  `ignore_errors=True` was masking the failures rather than fixing them).
- **Docker Desktop does not auto-start with Windows in this environment.** If
  `sandbox_service.run_command` returns `exit_code: 1` with `"Sandbox unavailable: could not reach
  Docker daemon"`, that's this, not a code bug -- launch
  `C:\Program Files\Docker\Docker\Docker Desktop.exe` and poll `docker version` until it responds
  (~10s in practice) before retrying.
- **Running the full Docker-heavy pytest suite at the same time as a real agentic pipeline run
  that also uses the sandbox causes false-negative verify failures**, specifically in the
  server-boot smoke test: both compete for the same Docker daemon, and a container can be too
  slow to get scheduled CPU to answer the health check within its retry window even though the
  server process itself started fine (confirmed directly: a real 3-attempt `CoderAgent.run()`
  recorded `server boot` as failed on every attempt while a full pytest run happened to be
  running concurrently; re-running the identical check against the identical generated code in
  isolation immediately after passed cleanly, `exit_code: 0`). Widened the health-check retry
  loop (10 -> 30 attempts, `SERVER_BOOT_TIMEOUT_SECONDS` 30 -> 45) to make this less likely, but
  the safest thing is still: don't run the full suite and a real end-to-end agent run at the same
  time on this machine.

## Testing conventions established

- `tests/` at `services/agentic_service/tests/`, pytest (installed via pip; not yet added to
  `requirements.txt` as a formal dependency since it's dev-only so far).
- Deterministic/validator logic: hand-crafted fixtures, no LLM, fast, golden-file style where
  applicable (e.g. `test_uiux_integration_manifest_builder.py`, `test_coder_diff_builder.py`).
- LLM-touching pipelines: also verified manually at least once per milestone against the **real**
  approved Login feature data (not just synthetic fixtures) — screenshots and generated code
  visually/manually inspected, not just asserted on structurally.
- Any project/feature/artifact created purely for isolated testing is deleted from Mongo + disk
  afterward (never left as debris) -- see the Windows `shutil.rmtree` gotcha above for the
  correct teardown pattern for git-repo-backed fixtures. The real `e-commerce-platform` /
  `Login` feature data is the intentional running example and is **left in its real, evolving
  state** between milestones.
- Docker containers are checked (`docker ps -a`) after every `sandbox_service`-touching test run
  to confirm none are left running.

## Real state changes made to the actual project (not test debris — don't "clean" these up)

- `outputs/e-commerce-platform/_project/design_system.json` — created in M2, contains the
  approved `LoginForm` component entry.
- `outputs/e-commerce-platform/_project/project_manifest.json` — created in M5 by the real
  `merge_approved_feature` approval hook, contains the real routes/api_endpoints/models/
  shared_components/features derived from the merged Login feature.
- `artifact_83e3692d` (`LoginForm.jsx`, `uiux_agent`, v1) was approved during M3 tool testing
  specifically to validate `read_ui_component`'s happy path against real data. This is a
  legitimate approval (it's a genuinely good component from M2), not a mistake to revert.
- **`workspaces/e-commerce-platform/repo/` — `main` now contains the real, merged Login feature**
  (as of M5): a `--no-ff` merge commit ("Merge feature/login into main") on top of the original
  scaffold commit. `main` has: `client/src/pages/LoginPage.jsx`,
  `client/src/components/LoginForm.jsx` (the actual approved UI/UX component, integrated
  verbatim via `read_ui_component`, not regenerated), `client/src/services/authService.js`,
  `server/src/routes/auth.routes.js`, `server/src/models/UserCredentials.js`, and
  `package.json`/`package-lock.json` (real `npm install` of `axios`, `bcrypt`, `dotenv`,
  `jsonwebtoken`, `jwt-decode`). The `feature/login` branch no longer exists (deleted by
  `merge_feature_branch` after the merge). **This was approved and merged through the real,
  unchanged `POST /artifacts/{id}/approval` endpoint** (`artifact_94797be2`, `code_diff`/json),
  driven by `CoderAgent.merge_approved_feature`. Verification for this merge showed
  `npm install: passed`, `build/lint/test: skipped` (no scripts configured yet in this project —
  see gotchas above for what that does and doesn't prove). M4's earlier manual-run commit on
  `feature/login` (with the then-missing `jsonwebtoken`) was superseded when M5 recreated the
  branch from scratch, as anticipated in M4's own notes.
- **The real planner (`CodePlanner`) cannot currently drive `CoderAgent.run()` unattended for
  this feature** — it exhausts both planning attempts and `run()` raises
  `CodePlanValidationError` (see gotchas above). The merge above was driven by the
  hand-validated plan in `scripts/run_coder_pipeline_manual.py`, exercising every stage
  downstream of planning (coding loop, verify, diff, artifacts, approval, merge) for real. This
  is the same precedent M4 set and is not a workaround unique to this session — expect to keep
  using it for real pipeline testing until the planner prompt is improved further.
- **M6 real end-to-end graph run for Login**: `graph_orchestrator_service.start(...)` →
  `resume("approved")` (SRS already approved) → auto-passed domain → paused at
  `approve_architecture` → `resume("approved")` (Architecture Plan already approved) → **real
  `uiux_node` ran**, producing a genuine v2 of every UI/UX artifact
  (`login_ui_metadata_v2.json`, `login_integration_manifest_v2.json`, `login_ui_design_v2.md`,
  `login_loginform_v2.jsx`, `login_login_page_v2.png` — visually confirmed, a clean styled login
  form) → paused at `approve_uiux` with the real v2 artifact IDs surfaced in graph state. Approved
  `artifact_26d13fb2` (`ui_metadata` v2) through the real `POST /artifacts/{id}/approval`
  endpoint, which (a) ran `apply_design_system_patch` again (correctly a no-op: `LoginForm`
  already existed, 0 new components/tokens merged — idempotent) and (b) resumed the graph into
  the **real `coder_node`**, which ran the real planner (both attempts, ~45s each), hit the
  documented `CodePlanValidationError`, and the exception was caught by
  `approval_service`'s existing broad exception handler (see gotcha #15 above) — the approval
  HTTP call still returned 200 OK normally. `graph_orchestrator_service.get_status(...)` now
  shows `next: ["coder_node"]` for this feature/thread — a future approval-triggered resume (or
  a fixed planner) would cleanly retry `coder_node` from there. This is the intended, correct M6
  outcome: the graph faithfully delegates to the real agents, successes and failures alike,
  through the exact same human-facing approval endpoint used throughout this whole build.
- `login_ui_metadata_v2.json` etc. (the v2 UI/UX artifacts from the run above) are real outputs
  of this milestone's verification, not test debris — left in place alongside the v1 set from M2.
- **`workspaces/e-commerce-platform/repo`'s `main` now has a real, working Express+Vite scaffold**
  (post-M8 fix, see deviation #17): `server/{package.json,src/app.js,src/server.js,.env.example}`
  and `client/{package.json,vite.config.js,index.html,src/{main.jsx,App.jsx,index.css}}` were
  backfilled via `ensure_project_repo`, and the already-merged Login feature was hand-wired into
  them (`app.js` mounts `auth.routes.js` at `/api/auth`; `App.jsx` routes `/login` to
  `LoginPage`), plus `bcrypt`/`jsonwebtoken`/`axios`/`jwt-decode` relocated into the correct
  `server`/`client` `package.json`. `client/package-lock.json` and `server/package-lock.json`
  are also real, committed output of the verification run (not debris). `git log --oneline -6`
  on `main` at time of writing: `c44825f` (lockfiles) → `d272f24` (Login wiring) → `de4de30`/
  `cbc1ac9` (scaffold backfill) → `667b0ef` (Login merge) → `c8bd481` (M4 manual coding attempt)
  → `0f5fcb3` (original bare scaffold, now superseded).
- **`main` also has `d513acc` on top of the above** ("Backfill scaffold upgrades: security
  middleware, DB connection, error handling") -- item 18's `_backfill_scaffold_upgrades` firing
  for real against this repo, adding helmet/rate-limit/`FEATURE_ROUTES_START`/`_END`/error-handler
  to `app.js` (preserving the already-mounted `authRoutes`) and guarded `mongoose.connect` to
  `server.js`, confirmed via the diff at the time (not test debris).
- **`feature/signup` branch (not yet merged, pending human review)**: two real Coder Agent
  commits (`66cf00d` attempt 1, `864a706` attempt 2 -- attempt 3 made no additional changes and
  wasn't committed since nothing new was dirty) modify `server/src/routes/auth.routes.js` (adds
  a real, validated `/signup` route: required-field check, existing-user check, JWT issuance) and
  `server/src/models/UserCredentials.js` (adds the `fullName` field), plus `bcryptjs` installed
  (declared at the repo root by the model's own `npm install` rather than `server/package.json`
  -- a real, minor planner/coding-loop imprecision worth knowing about, though harmless since
  `UserCredentials.js` still uses the original `bcrypt`, not `bcryptjs`, for its hashing). Code
  plan v1 + a first artifact set (`verification_passed: false`, from the contention-confounded
  run) plus a corrected v2 artifact set (`verification_passed: true`, from the clean re-verify --
  same code, accurate result) both exist under `outputs/e-commerce-platform/feature-signup/
  05_code/`; v2 is the one to review/approve. Signup's UI/UX v2 (LoginForm genuinely reused
  byte-for-byte, SignupForm freshly generated -- see item 17) was approved for real through
  `POST /api/v1/artifacts/{id}/approval` during this session, which is what resumed the graph
  into this real `coder_node` run in the first place.

## Where to look

- Full build spec (read this first, in order, before any new milestone): `instructions .md`
- This file: durable cross-milestone memory, updated at the end of each milestone
- `C:\Users\ASUS\.claude\plans\soft-petting-star.md`: scratch, current-milestone-only plan
