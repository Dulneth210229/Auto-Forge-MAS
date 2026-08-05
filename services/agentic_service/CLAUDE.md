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
19. **Architecture Agent's out-of-scope validator false-positived on almost every real run --
    fixed, and re-verified with a real, brand-new project + feature end-to-end.** The user
    reported the Architecture Agent "did not work" when run for real. Root cause: both
    `usecase_validator.py`'s and `sequence_validator.py`'s `_validate_out_of_scope` flagged a
    diagram element as an out-of-scope violation whenever it shared just **2 stems** with a
    forbidden SRS `out_of_scope` phrase (`required_overlap = 1 if len(forbidden_stems) == 1 else
    2`), regardless of how many total stems the phrase had or whether the actual *distinguishing*
    word was present at all. Since out-of-scope items are almost always phrased using the same
    domain nouns as the feature itself (e.g. "Account verification via email" for a feature that
    is itself about accounts and email), this meant the check false-positived on nearly any
    legitimate in-scope element -- confirmed directly against three real errors from an earlier
    real run (documented in this file's history for the Signup feature): a duplicate-email check
    was flagged as "Account verification" (matched on `account`+`email`, missing the actual
    distinguishing stem `verif`), a new-user-registration step was flagged as "Password recovery
    functionality" (matched on `password`+`recovery`, missing `functionality`), and the signup
    use case itself was flagged as "User profile customization after signup" (matched on
    `user`+`signup`, missing `profile`/`customiz`). Because the Architecture Agent's fallback
    path (a deterministic, SRS-derived plan, generated only when both the raw and repaired LLM
    outputs fail) has **no further recourse** if it also fails validation, this false-positive
    could -- and, per the prior session's real Signup run, did -- crash the entire request with
    no Architecture Plan produced at all, blocking the UI/UX and Coder Agents from ever running.
    - Fix: `_validate_out_of_scope` in both validators now requires **all** of a forbidden
      phrase's meaningful stems to be present (`required_overlap = len(forbidden_stems)`), not a
      flat 2 -- the element must restate the entire forbidden concept, not merely share incidental
      domain vocabulary. Verified this alone fixes all three real false positives while still
      catching a genuine full-concept violation (e.g. "Verify Account Email... sends an email
      verification link" against "Account verification via email" is still correctly flagged,
      since `verif`/`account`/`email` are all present).
    - This alone was slightly too strict for phrases containing generic requirement-writing
      filler nouns (e.g. "Password recovery **functionality**" -- no realistic diagram element
      would ever literally contain the word "functionality"). Added `functionality`, `capability`,
      `capabilities`, `support` to both validators' `STOPWORDS` sets -- domain-agnostic filler
      words that describe *that* something is a capability, not *which* one, so they add no
      distinguishing signal (same precedent as the pre-existing `feature`/`flow` stopwords).
    - **Safety net added regardless of the above fix** (`agent.py`'s `_generate_architecture_output`):
      the final `_validate_full_output` call on the fallback path is now wrapped in its own
      try/except. If the fallback *still* fails validation (a heuristic validator can always have
      another edge case), the run no longer crashes -- it logs a warning and appends a plain,
      specific caveat to the plan's own `human_approval_note` field, then proceeds so a human can
      review and judge it, mirroring the Coder Agent's existing "proceed anyway with
      `verification_passed=False`" precedent rather than inventing a new failure story.
    - Tests: `tests/test_architecture_usecase_validator.py` (new, 5 tests: all 3 real false
      positives now pass validation, a genuine violation is still caught, an out-of-scope item
      with no meaningful stems is safely ignored) and `tests/test_architecture_sequence_validator.py`
      (new, 3 tests: 2 of the real false positives adapted to sequence-message shape, genuine
      violation still caught) -- no LLM, hand-built minimal `usecase_json`/`sequence_json`
      fixtures. Full suite: **123 passed** (up from 115).
    - **Real end-to-end verification, a genuinely new project and feature** (not a reuse of
      e-commerce-platform): created project **TaskFlow** (`proj_53284a63`, SaaS/MERN) and feature
      **Task Comments** (`feature_5521adbd` -- add/view/delete comments on a task, with SRS
      `out_of_scope` items "Editing existing comments", "Comment notifications or mentions",
      "Comment threading or replies", "Comment attachments or media" -- deliberately chosen to
      share the word "comment" with every in-scope element, the same shape of case that broke
      before). Ran the real pipeline through the actual HTTP API: Requirement Agent (real,
      succeeded first try) → approved → graph `start()` → `resume("approved")` (auto-passed
      `domain`) → paused at `approve_architecture` → **ran the real, now-fixed Architecture
      Agent**: raw LLM output failed JSON parsing (unrelated pre-existing issue, line-431
      malformed delimiter), the repair attempt was missing several required top-level keys, so it
      fell through to the deterministic SRS-derived fallback -- **which completed and passed
      `_validate_full_output` cleanly, with no validation-failure warning logged at all** (the
      fix's target scenario, working correctly on a real run) → approved the Architecture Plan →
      graph resumed into the real `uiux_node`, which generated `CommentInput`/`CommentList`
      components and completed normally → approved the UI metadata → graph resumed into the real
      `coder_node`, whose planner hit the **already-documented, separately-tracked** endpoint/
      entity-coverage limitation (`CodePlanValidationError: code_plan_json does not cover these
      API endpoints: ['/api/task-comments']; ... data entities: [...]`) -- the same pre-existing
      planner unreliability observed repeatedly for Login/Signup in the other project, not a new
      or regressed issue, and out of scope for this fix. The graph correctly stayed parked at
      `next: ['coder_node']` (the same emergent, already-documented checkpoint behavior noted
      elsewhere in this file), ready for a clean retry. **Net result: the Architecture Agent --
      the actual subject of this fix -- now runs to completion and produces an approvable plan
      for a real, previously-guaranteed-to-fail-shaped feature, and the pipeline progressed
      further (through Architecture and UI/UX) than it had ever previously gotten for this class
      of feature.**
    - Known, pre-existing, separate quality gap observed along the way (not part of this fix):
      the deterministic fallback Architecture Plan is noticeably crude -- e.g. it split the
      Comment entity's four fields into four separately-named "entities"
      (`Task CommentsDataEntity1..4`) instead of one unified entity, and produced duplicate
      `/api/task-comments GET` endpoint entries instead of distinct POST/GET/DELETE routes
      matching the SRS's `api_expectations`. This is the fallback template's own generation logic
      (a different code path from the validators fixed here), and its crudeness likely also
      contributed to the Coder Agent planner's subsequent coverage failure (awkward, non-standard
      entity names are harder for the planner to reference correctly). Worth a future look, but
      not conflated with the validator bug fixed in this pass.
20. **Ran the real Coder Agent for TaskFlow/Task Comments (user request: "run the coder agent for
    this new project and feature and check the output") -- found and fixed a real
    `GraphRecursionError` crash, found and corrected a UI/UX component-approval gap, and got a
    clean, genuinely well-integrated result on the corrected re-run.** Since the real planner
    (already known-unreliable, see the gotchas section) failed identically to item 19's earlier
    run, used the same established hand-validated-plan precedent as Login/Signup
    (`scripts/run_taskflow_coder_pipeline_manual.py`, new) -- a real, sensible plan (REST
    POST/GET/DELETE routes, one `Comment` model, modify the two approved UI/UX components instead
    of rewriting them) that still covers every literal string `plan_validator` requires from the
    crude fallback Architecture Plan.
    - **Bug found and fixed**: the first real run of the coding loop against this 8-file plan (2
      of which were "patch an existing component" tasks) hit `GraphRecursionError` -- the 100%
      real, uncaught turn-limit-of-65 exception crashed the entire script/request. `_code_with_retries`
      now catches `GraphRecursionError` explicitly and treats it exactly like an incomplete
      attempt: commits whatever partial progress was made (not lost), and feeds the next attempt
      a message naming the recursion limit and asking the model to work efficiently (don't re-read
      known files, don't call `check_syntax` more than once per file, prioritize finishing over
      polishing) on top of the existing plan-gap report. `CODING_LOOP_RECURSION_LIMIT` also bumped
      65 -> 100 -- the exact right number isn't the point anymore now that hitting it is a
      recoverable failure, not a crash. 4 new tests in `tests/test_coder_agent_retries.py`
      (mock-based: recursion error retried not crashed, efficiency-hint feedback on the next
      attempt's task message, plan-gap still skips the expensive verify() call, a passing verify()
      still short-circuits remaining attempts).
    - **Real gap found in this session's own process, not a Coder Agent bug**: the first
      (pre-fix) full run of the coding loop completed successfully (`verification_passed=True`,
      attempt 1/1) but the model **fabricated brand-new `CommentInput.jsx`/`CommentList.jsx`/
      `CommentItem.jsx` components from scratch** instead of reusing the approved UI/UX ones, even
      though the plan explicitly said to "modify" them. Root cause: only the `ui_metadata` JSON
      artifact had been approved (`artifact_b3950e89`), not the individual `UI_COMPONENT_CODE`
      artifacts for `CommentInput`/`CommentList` themselves -- `read_ui_component`'s lookup
      (`_find_approved_component_artifact`) filters on `approval_status == APPROVED`, so it had
      nothing to find and correctly reported no approved component, leaving the model to build its
      own working (but design-inconsistent) version out of necessity. Confirmed
      `approval_service.py` never cascades a `UI_METADATA` approval to its sibling
      `UI_COMPONENT_CODE` artifacts -- each component needs its own explicit approval, same as
      every other artifact type. **This is a real, easy-to-miss human/process gotcha worth knowing
      for future runs**: approving the metadata is not sufficient to make components reusable by
      the Coder Agent.
    - Approved the two component artifacts for real (`artifact_5e0bba5f`, `artifact_ca5c2871`)
      and re-ran the identical hand-validated plan against a freshly-reset branch. **Result: clean
      integration, exactly as intended.** `CommentInput.jsx` kept 100% of the approved component's
      markup/styling/loading/error-state logic -- the *only* change was replacing the fake
      `// Mock submission - in real app this would be an API call` + `setTimeout` with a real
      `await props.onSubmit(props.taskId, commentText)` call (plus adding the `useState` import
      the preview-only original omitted). `CommentList.jsx` likewise kept 100% of its visual
      structure -- the delete button (previously present with no `onClick` at all) now correctly
      calls `props.onDelete(comment._id)`, and every field reference was correctly updated to match
      the real `Comment` Mongoose model's actual shape (`comment.author.username`/
      `comment.author._id`/`comment.createdAt`/`comment._id`/`comment.text`) instead of the UI/UX
      agent's originally-guessed field names (`comment.authorUserId`/`comment.createdTimestamp`/
      `comment.id`/`comment.commentText`). This is precisely what this session's earlier Coder
      Agent prompt hardening (item 18: "read the component's actual prop usage and wire every prop
      its logic depends on," "never leave a handler wired to hardcoded/fake logic when a real
      service exists") was meant to produce, now confirmed on a real run where the precondition
      (an actually-approved component) was correctly met.
    - `server/src/routes/task-comments.routes.js`: real REST design (POST/GET/DELETE, not the
      fallback plan's single duplicated GET) -- required-field validation on create (400 on
      missing `text`/`author`/`task`), ownership check on delete (403 if the requester isn't the
      comment's author), chronological sort on list, `populate("author", "username")` on both read
      paths so the frontend gets real author names. `verify_result` on the corrected run: **all
      steps passed** -- `npm install` (both sides, first-ever install for this fresh project),
      server boot, client build, endpoint route coverage, and an informational (non-blocking)
      placeholder-stub hit on `TaskDetailPage.jsx`'s intentionally-mocked `currentUser` (reasonable,
      since no auth feature exists yet in this project) and a sample task description string --
      both legitimate, correctly-flagged, non-blocking notes for a human reviewer, not bugs.
    - Full suite re-confirmed passing after the `GraphRecursionError` fix (see test count below).
    - **Real state**: `workspaces/taskflow/repo` now exists with a `feature/task-comments` branch
      (not yet merged -- pending human review of the corrected run's artifacts:
      `artifact_fd4d28ec` and siblings, code plan + merge report + manifest). The pre-fix run's
      artifacts (`artifact_a72df0e1` and siblings, from the fabricated-components version) are
      superseded by this corrected set and should not be approved.
21. **Every generated app only ever showed the static scaffold placeholder when actually run --
    fixed the root cause (unreachable pages), added two new deterministic gates that prove a page
    is both reachable and renders without crashing, and added a real "revise by human prompt"
    capability for the Coder Agent (mirroring Requirement/Architecture Agent's existing
    `.revise()` pattern) so a human can iterate on an already-verified feature instead of hoping
    one shot is enough.** The user reported this directly: Login, Signup, and Task Comments all
    rendered nothing but "Auto-Forge Generated App" / "Feature pages are registered as routes
    below." regardless of what was actually built. Investigated and confirmed a real, structural
    root cause -- **not** a per-feature LLM mistake: `CLIENT_APP_JSX`'s `HomePage` has never had
    any navigation at all, so every `<Route>` a feature adds is real and correctly wired, but
    genuinely unreachable by a human clicking through the app. The user's own first proposal (an
    automatic live-dev-server self-correction loop) was evaluated and deliberately not built --
    no reliable, domain-agnostic way exists to judge "does this look right" without either
    duplicating a much cheaper deterministic check or resorting to a slow, non-deterministic
    LLM-judged screenshot (exactly the cost `preview_renderer.py`'s own docstring already argues
    against for a *much* smaller unit), and it would inherit this project's already-documented
    Docker-contention flakiness. Full plan: `C:\Users\ASUS\.claude\plans\soft-petting-star.md`.
    - **Scaffold fix** (`workspace_service.py`): `CLIENT_APP_JSX`'s `HomePage` now has a stable
      `{/* FEATURE_LINKS_START */}`/`{/* FEATURE_LINKS_END */}` marker pair inside a `<nav><ul>`,
      mirroring the existing `FEATURE_ROUTES_START`/`_END` idiom used for `app.js`'s router
      mounts -- a feature now patches this marker to add a real `<Link>` alongside its `<Route>`,
      instead of there being nothing to patch at all. **Idempotent backfill**: new
      `_LEGACY_CLIENT_APP_JSX_V1` fingerprint + `_upgrade_client_app_jsx`, wired into
      `_backfill_scaffold_upgrades` exactly like the existing `app.js`/`server.js` upgrades --
      untouched file -> wholesale replace; customized file (already has real routes/imports) ->
      anchored insertion that never touches what's already there; already-upgraded -> no-op.
      This is what let the two already-broken, already-real projects
      (`e-commerce-platform`, `taskflow`) self-heal just by calling `ensure_project_repo` again,
      same rollout mechanism as every prior scaffold-upgrade fix.
    - **Prompt changes** (`prompt.py`): `CODE_PLANNER_SYSTEM_PROMPT` rule 9's nav-link clause was
      previously conditional ("if one already exists" -- dead code, since the scaffold never
      created that mechanism) -- now unconditional: adding a page means planning both its
      `<Route>` and a real `<Link>` to it, in one "modify" of `App.jsx`. Added explicit guidance
      for parameterized routes (e.g. `/tasks/:taskId`): never link directly to one -- link to a
      list/index page instead, planning that page as part of the feature if it doesn't exist yet.
      `CODER_AGENT_SYSTEM_PROMPT` gained the symmetric patch instruction for
      `// FEATURE_LINKS_END` and a new completeness rule: a `<Route>` with no reachable `<Link>`
      is exactly the "looks done but isn't" defect the existing completeness rules already target.
    - **New hard gate: page reachability** (`nav_checker.py`, new module, sibling to
      `route_checker.py`, same "explicitly best-effort, regex-based, not full AST" idiom):
      `check_page_reachability` parses `App.jsx` for every `<Route>`/`<Link>` (including
      `to="..."`, template-literal `to={\`...${\`}, and `<a href="...">`) across the entire
      `client/src` tree (not just `App.jsx`), resolves parameterized routes as reachable only if
      their static prefix is itself a registered, reachable route. Wired into `verify.py` as a
      new hard gate, same justification as `check_route_coverage`: cheap, mechanical, no
      meaningful ambiguity.
    - **New hard gate: runtime render check** (`render_checker.py`, new module). Neither
      `client build` (compiles) nor `page reachability` (linked) can catch a page that does
      both but still throws at runtime (e.g. an undefined prop access) -- this closes that gap
      without a live dev server or a retry loop: serves the client's **already-built** `dist/`
      via `vite preview` (correct SPA-routing fallback, unlike a bare static server) from inside
      the sandbox, using a new `sandbox_service.start_background_service`/
      `stop_background_service` (detached container, published port -- `run_command` only ever
      waited for exit with no port publishing before this). From the host, Playwright navigates
      to `/` and every reachable route, checking for zero `pageerror` events and non-empty
      rendered content -- the same minimal bar `preview_renderer.py` already uses for component
      previews. Home page failing is a hard gate (cheap, no data dependency, exactly what was
      silently broken project-wide); feature pages are informational only (their rendering can
      legitimately vary with backend data state, e.g. an empty list before any data exists).
    - **Two real infra bugs found and fixed only by testing against real Docker/real async
      call chains, not synthetic unit tests**:
      1. `sandbox_service.start_background_service` reloaded the container's Docker attrs
         **once**, immediately after `containers.run()` returned, and raised if the port mapping
         wasn't there yet -- confirmed directly that this is a pure timing race (a manual
         reproduction showed the identical container correctly publishing its port moments
         later). Fixed by polling `reload()` up to 10 times (0.3s apart, bailing early if the
         container already exited), and including the container's logs in the error message if
         it genuinely never publishes.
      2. **`render_checker.py`'s Playwright sync API crashes when actually invoked through the
         real pipeline.** `CoderAgent.run()`/`revise()` are `async def`, invoked from a sync graph
         node via `asyncio.run(...)` (deviation #13) -- meaning `verify()` (called synchronously,
         deep inside that async call chain, with no thread of its own) always executes with an
         asyncio event loop already running on that thread. Playwright's sync API refuses to run
         on such a thread at all. This was invisible in every test up to this point because
         `test_render_checker.py`/`test_coder_verify.py` call `verify()`/`check_runtime_render`
         from plain synchronous scripts/tests with **no** event loop running -- only a real,
         genuine end-to-end `revise()` run (see below) surfaced it: every one of 3 coding attempts
         failed with `"home page render": failed -- "It looks like you are using Playwright Sync
         API inside the asyncio loop."` Fixed by running the actual Playwright-touching work
         inside a dedicated `concurrent.futures.ThreadPoolExecutor` worker thread from within
         `check_runtime_render` itself -- a fresh thread has no event loop of its own, regardless
         of the caller's context, with no change to the function's public signature or any
         caller. New regression test drives this through `asyncio.run(...)` specifically (calling
         the function directly inside a running coroutine, not via `asyncio.to_thread`, which
         would already dodge the bug) to actually reproduce the failure mode.
    - **New human-in-the-loop iteration capability: `CoderAgent.revise(feature_id, request)`**,
      mirroring Requirement/Architecture Agent's existing `.revise()` pattern (load latest
      artifact + a human `revision_comment`, regenerate, save as a new version, never overwriting,
      require fresh approval) -- adapted for the fact that the Coder Agent's real output is a live
      git branch, not just a JSON document. This closes a real, previously-unaddressed gap: before
      this, the only way to influence a re-run at all was to manually resume the LangGraph run, and
      `human_comment` never reached the agentic coding loop's own task message, only the planner.
      - New `workspace_service.resume_feature_branch(project_id, feature_id)`: checks out an
        EXISTING branch **without resetting it** (raises `ValueError` if no such branch exists) --
        the key difference from `run()`'s `start_feature_branch`, which always deletes and
        recreates from `main`. A revision builds on top of prior work; it does not discard it.
      - New `CoderAgentReviseRequest` schema (`revision_comment`, `revised_by`) and
        `POST /features/{feature_id}/agents/coder/revise` endpoint, same error-handling shape as
        the existing `/requirement/revise`/`/architecture/revise` endpoints.
      - New `CoderAgent._find_latest_code_plan_artifact`: finds the latest `CODE_PLAN` artifact
        **regardless of approval status** -- a revision should be possible even before a prior
        version has been approved/merged (a human may want several rounds of feedback first).
      - **A real, non-obvious design bug found only by a genuine end-to-end run, not by the
        mock-based unit tests written first**: `revise()`'s re-plan is naturally a *delta* (a
        human asking to "add a loading spinner" produces a plan that only touches
        `CommentList.jsx`, not one that re-lists every endpoint/entity the *prior* plan already
        implements) -- but `_plan_with_retries` validated that delta alone against the **full**
        architecture plan's endpoint/entity/requirement coverage, the same check used for a
        brand-new `run()`. Confirmed directly: a real revision request against the live Task
        Comments feature failed both planning attempts with `"code_plan_json does not cover these
        API endpoints: ['/api/task-comments']..."` even though those endpoints were already
        correctly implemented and untouched by this revision. Fixed by adding an optional
        `coverage_baseline_files` parameter to `_plan_with_retries` -- for revise() only, coverage
        is validated against the **union** of the prior plan's files and the new delta's files,
        while the plan actually returned (and coded) remains just the delta. Mock-based tests
        alone would never have caught this, since they stub out `plan_validator.validate` entirely
        -- a new test exercises the **real, unmocked** validator against a realistic architecture
        plan + prior-plan/delta-plan pair to lock this in.
    - Tests: `tests/test_nav_checker.py` (new, 10, page-reachability logic, no Docker/LLM),
      `tests/test_render_checker.py` (new, 3: real render check passes on the untouched scaffold,
      the sandbox port-mapping mechanism itself, and the event-loop reproduction above),
      `tests/test_workspace_scaffold.py` (+5: `_upgrade_client_app_jsx` backfill + idempotency,
      `resume_feature_branch` checks-out/raises), `tests/test_coder_prompt.py` (+2: unconditional
      link rule, parameterized-route list-page guidance), `tests/test_coder_verify.py` (+4: page
      reachability pass/fail, runtime-render hard-fail-on-home-crash, statuses wired through
      end-to-end), `tests/test_coder_agent_revise.py` (new, 4: raises with no prior run, resumes
      instead of restarting the branch, frames the plan as a revision not a rejection, and the
      real-validator coverage-union fix). Full suite: **155 passed** (up from 153 before adding
      the last two regression tests above).
    - **Real end-to-end verification against both live projects, not just synthetic fixtures**:
      triggered `ensure_project_repo` for real against `proj_a2e3d529` (e-commerce-platform,
      currently on `feature/signup`) and `proj_53284a63` (taskflow, currently on
      `feature/task-comments`) -- both got the `FEATURE_LINKS` marker backfilled wholesale
      (confirmed via `git log`: "Backfill scaffold upgrades: ... home page navigation" on top of
      each project's existing history), proving the backfill mechanism works on real,
      already-diverged repos, not just fixtures. Ran `coder_verifier.verify()` for real against
      both: `page reachability` correctly **fails** on both (neither project has ever had a link
      retroactively added for its pre-existing route -- an accurate, honest result, not a
      regression), while every other step (install, boot, build, endpoint coverage,
      **home page render: passed**) is clean. One transient false-negative on `server boot` was
      observed and confirmed non-reproducing on an immediate isolated re-run -- the same
      already-documented class of Docker-contention flakiness noted below, not a regression.
      Then ran the real `CoderAgent.revise()` end-to-end against the live Task Comments feature
      (`feature_5521adbd`) with a genuine human revision comment ("add a loading spinner while
      comments are being fetched") -- this is what surfaced both real bugs above. After fixing
      them, re-verified the same already-correct generated code (a clean, minimal, well-scoped
      diff: one line added to `CommentList.jsx`'s existing loading state, nothing else touched)
      and saved a corrected, accurate artifact set as **v4** (`artifact_8169b564` and siblings) --
      same "re-verify the same code with a corrected checker, don't re-spend real LLM time for a
      cosmetic re-confirmation" precedent already established for Signup (item 20). Confirms the
      whole revise() flow for real: prior branch commits preserved (`git log` shows the original
      `attempt 1`/`attempt 2` commits still present, untouched), a fresh version saved
      independently of v1-v3, approvable on its own.
    - **A second real bug in the coverage-union fix itself, found only by the user actually
      calling `POST /features/{id}/agents/coder/revise` through Swagger for a genuine SECOND
      revision** (not caught by any test written so far, since none exercised more than one
      revision): the coverage-baseline union above only ever used the *latest* saved CODE_PLAN
      artifact's own file list -- but that latest artifact (v4, saved from the loading-spinner
      revision) itself only lists its own delta (`CommentList.jsx`), by design, not the original
      plan's full file list. So a second revision's baseline silently lost everything the
      *original* plan (v1/v2) implemented, reproducing the identical
      `"code_plan_json does not cover these API endpoints: ['/api/task-comments']..."` rejection
      this whole mechanism exists to prevent -- this time surfaced directly to the user as a 400
      through the real API, not just in a background script. Fixed by adding
      `CoderAgent._collect_cumulative_plan_files(feature_id)`, which unions file entries across
      **every** CODE_PLAN version ever saved for the feature (later versions winning for the same
      path), not just the latest -- `revise()` now passes this as `coverage_baseline_files`
      instead of the single latest plan's own files. **Any future logic that treats "the latest
      saved plan" as "everything this feature has ever implemented" will hit this same class of
      bug** -- after the first revision, that's no longer true by design. New regression test
      (`test_revise_coverage_baseline_spans_every_prior_version_not_just_the_latest`) seeds two
      prior plan versions (a full v1 + a delta-only v2, mirroring the real history) and confirms
      a third revision's real, unmocked `plan_validator` still passes. **Re-verified for real
      against the live feature with a genuine second revision** ("add a delete confirmation
      dialog before deleting a comment") -- planning succeeded with no coverage error at all this
      time, the generated diff is exactly right (wraps the existing `onDelete` call in a
      `window.confirm(...)` guard, nothing else touched), and `verify()` came back clean on every
      step except the same already-known, out-of-scope `page reachability` gap for
      `/tasks/:taskId` (unrelated to this revision, not a regression). Saved as artifact set v5.
22. **`CoderAgent.revise()` only worked when the human named the exact file(s) to change -- a
    vague, file-unspecified request (e.g. "styles are missing, add tailwind css") never correctly
    identified which files were affected. Fixed by giving revision planning real tools to look at
    the actual codebase, instead of a single-shot LLM call with zero visibility into it.** The
    user reported this directly, having had to manually enumerate files like `TaskflowHomePage.jsx`
    and `TaskDetailPage.jsx` one at a time to get anything done. Root cause, confirmed by reading
    the code: `code_plan_json` for a revision was produced by `CodePlanner.generate()` -- a
    single-shot, non-agentic LLM call whose only context is the SRS/Architecture Plan/project
    manifest/UI manifest/human comment, with **zero ability to look at the real, current files** --
    it could only correctly scope a change when told exactly what to do, never when it had to
    figure out *what's affected* on its own.
    - **New agentic revision planner**, reusing tools/patterns already proven elsewhere in this
      codebase rather than inventing new mechanisms:
      - `tools.py`'s new `build_revision_planning_tools(project_id, feature_id)`: a read-only
        subset of the coding loop's own tools (`list_dir`/`read_file`/`search_code`/
        `read_project_manifest`/`read_ui_component` -- explicitly excludes write_file/apply_patch/
        run_shell/check_syntax/list_unimplemented_planned_files, since planning must never touch
        the working tree), plus a new `submit_code_plan(plan_json: str)` tool -- the model's one
        and only way to finish. Deliberately a JSON **string** argument, not a nested `list[dict]`
        tool argument, so parsing reuses the already-proven `CodePlanner._extract_json_object`
        (with its existing repair-prompt fallback) instead of an untested nested tool-call schema.
      - `planner.py`'s new `CodePlanner.generate_via_exploration(...)`: builds the same
        `create_agent(model=get_agentic_chat_model(), tools=..., system_prompt=...)` shape
        `coding_loop.py`'s `build_coder_react_agent` already uses, with a bounded
        `REVISION_PLANNING_RECURSION_LIMIT` (see below for why this needed raising twice).
      - New `CODE_PLANNER_AGENTIC_REVISION_SYSTEM_PROMPT` + `build_agentic_revision_planner_user_prompt`
        (`prompt.py`) -- shares the existing coverage/scaffold-awareness hard rules with the
        single-shot prompt (factored into `_CODE_PLANNER_SHARED_HARD_RULES`/`_CODE_PLAN_JSON_SHAPE`
        to avoid drift), adds explicit instruction to use the tools (especially for a broad,
        file-unspecified request), and seeds the prompt with the cumulative file list from
        `_collect_cumulative_plan_files` (item 21's fix) as a starting point the model can still
        look beyond via its own tools.
      - `agent.py`: `_plan_with_retries` gained an `exploration_context: tuple[project_id,
        feature_id] | None` -- when set (only `revise()` sets it; `run()` is unaffected, since
        planning happens before any feature branch exists there), each attempt calls
        `generate_via_exploration` instead of `generate`. **Required reordering in `revise()`**:
        `workspace_service.resume_feature_branch(...)` now happens BEFORE planning, not after --
        the exploration tools read whatever is currently checked out, so the feature branch's real
        content must already be checked out when planning starts.
    - **Two more real, reachable failure modes found ONLY by running this for real against the
      live Task Comments feature with the user's exact wording -- neither was caught by the
      mock-based unit tests written first, since those don't exercise a real, multi-turn
      tool-calling loop**:
      1. The exploration loop is genuinely open-ended (a vague ask can require many list_dir/
         read_file calls), and the first real run used 16 real tool-calling turns without ever
         calling `submit_code_plan`, hitting the initial 25-turn budget and raising
         `CodePlanGenerationError` uncaught -- crashing the whole `revise()` call. Fixed two ways,
         mirroring the exact lesson already learned for the coding loop's `GraphRecursionError`
         (item 20): bumped `REVISION_PLANNING_RECURSION_LIMIT` 25 -> 50, and made
         `_plan_with_retries` catch `CodePlanGenerationError` from the exploration path and retry
         with an efficiency-focused hint ("don't re-read a file you've already read..."), instead
         of letting it crash the request.
      2. Even with real exploration happening, the model **correctly discovered Tailwind was
         already fully configured project-wide** (tailwind.config.js/postcss.config.js/index.css's
         `@tailwind` directives all already present) but still **converged on the wrong fix**
         (planning to modify `index.css`) instead of finding the one actual unstyled page
         (`TaskflowHomePage.jsx`, using raw inline `style={{...}}` throughout, zero `className`
         usage). Root cause: finding files that do **NOT** match a pattern (no Tailwind classes) is
         a much harder "inverse search" for a model to carry out reliably via manual list_dir/
         read_file/search_code than finding files that DO match one. Fixed with a new deterministic
         tool, mirroring the exact `nav_checker.py`/`route_checker.py` "cheap, best-effort regex
         heuristic" precedent: `style_checker.py`'s `check_component_styling(workspace_root)`
         scans every `.jsx` file under `client/src/pages`/`client/src/components` and reports
         `"styled"` (has `className=`), `"inline_styles"` (only raw `style={{`/`style={`), or
         `"unstyled"` (neither) -- exposed as a new `check_component_styling` tool in
         `build_revision_planning_tools`, with the system prompt explicitly instructing the model
         to call it FIRST for a styling-related comment and trust its answer over manual inference.
    - **Real end-to-end proof, the user's exact reported problem, verified twice (once
      pre-`check_component_styling`, confirming the gap; once after, confirming the fix)**: called
      `coder_agent.revise('feature_5521adbd', ...)` with the literal comment "Styles are missing in
      the generated code so add styles using tailwind css" -- **no file names given at all**.
      Before the styling tool: planned only `client/src/index.css` (wrong -- Tailwind was already
      configured). After adding the tool: planned exactly `client/src/pages/TaskflowHomePage.jsx`
      (modify), with the model's own summary correctly stating "All other components appear to
      already be using Tailwind CSS classes appropriately" -- an accurate, correctly-scoped
      diagnosis with zero file names supplied by the human. The actual generated diff is exactly
      right: every raw inline `style={{...}}` in that file was replaced with the equivalent
      Tailwind utility classes (`p-8 font-sans`, `text-2xl font-bold`, `mt-2`, `text-blue-600
      hover:underline`, etc.), nothing else touched.
    - **Known, separate, pre-existing bug found along the way, NOT part of this fix and not
      introduced by it**: this run's `verify()` still reported `verification_passed: False`, but
      solely because `client build (vite build)` fails with `ReferenceError: module is not defined
      in ES module scope` at `client/postcss.config.js:1` -- that file uses CommonJS
      (`module.exports = ...`) while `client/package.json` declares `"type": "module"`, which
      forces Node to treat every `.js` file as an ES module. Confirmed this predates this fix
      entirely (`postcss.config.js` already existed, already broken, on the commit before this run
      started) -- likely a leftover from earlier, separate manual testing that set up Tailwind in
      this project. The coding loop actually noticed and attempted a fix on its own initiative
      (created a `postcss.config.cjs` with the same, correct content -- `.cjs` is exempt from the
      `"type": "module"` rule), but left the original broken `postcss.config.js` in place alongside
      it, so the build still fails (Vite/PostCSS's config resolution still finds the broken `.js`
      file). **Not fixed here** -- deleting the stale `client/postcss.config.js` (keeping the
      already-correct `.cjs` version) would resolve it, but that's a separate, small, pre-existing
      project bug outside this session's scope (making `revise()` understand vague requests), left
      for a future pass or a human's own `git rm client/postcss.config.js` on the live project.
    - Tests: `tests/test_style_checker.py` (new, 6, pure regex-heuristic tests, no LLM/Docker),
      `tests/test_revision_planner_tools.py` (+1 for `check_component_styling`, tool-set-shape
      assertion updated), `tests/test_coder_planner_exploration.py` (new, 4: parses a submitted
      plan, raises when never submitted, recursion-limit-as-clean-failure, malformed-JSON repair
      path -- all mock-based, no real LLM), `tests/test_coder_agent_revise.py` (+2: resume-before-
      planning call-order assertion, exploration-recursion-limit retry-with-efficiency-hint).
      Full suite: **172 passed** (up from 156 before this item).
23. **Two more real bugs found from the user continuing to hit real, reachable failures through
    the live `/coder/revise` endpoint on the same TaskFlow feature -- one in the exploration
    planner's reliability at real project scale, one an actual, separate frontend bug (a blank
    page mistaken for "no styles").**
    - **Exploration planner reliability at real project scale, confirmed with two full real
      re-runs of the same request** (a vague "this /tasks endpoint doesn't have styles... or
      TaskDetailPage.jsx" comment): the first hit `REVISION_PLANNING_RECURSION_LIMIT` (still 50 at
      the time) after real, substantial exploration; a second real run (~4.5 hours, due to a severe
      apparent Ollama/inference slowdown in this environment -- individual tool-calling turns that
      previously took seconds took minutes each) got through both planning attempts without hitting
      the turn limit at all, but **both times submitted a plan with an empty `files` list**,
      failing `code_plan_json.files must be a non-empty list` -- a different failure mode than
      either previously-seen one (recursion exhaustion, or coverage rejection). Given the multi-hour
      real cost of further live reproduction, root-caused and fixed the improvable parts directly
      rather than continuing to re-run live:
      - `REVISION_PLANNING_RECURSION_LIMIT` bumped 50 -> 80 (`planner.py`) -- exploration is still
        cheap (filesystem-only), so a larger budget costs little and helps as the project (now
        11+ files across many revisions) keeps growing.
      - `CODE_PLANNER_AGENTIC_REVISION_SYSTEM_PROMPT` gained a new rule 1b (`prompt.py`): planning's
        job is only to decide WHICH files need a plan entry, not to draft the actual code change (a
        later, separate coding step does that and reads each file itself) -- so it should prefer a
        summarizing tool (`check_component_styling`/`read_project_manifest`/`search_code`) over
        reading full file contents one at a time, and call `submit_code_plan` as soon as it's
        confident rather than continuing to explore "to be thorough." This directly targets wasted
        turns spent reading files whose content isn't actually needed for a planning-level decision.
      - The exploration-recursion-limit retry feedback (`agent.py`) was rewritten: the old text
        ("don't re-read a file you've already read") was **not actionable** -- a fresh retry
        attempt is a brand-new agent conversation with zero memory of what the previous attempt
        actually explored, so it has no way to know what "already read" even refers to. The new
        feedback asks for a general strategy change instead (prefer summarizing tools, stop
        exploring once confident) rather than an unfollowable specific instruction.
      - **Not yet root-caused**: why the model submitted an *empty* files list specifically (rather
        than, say, a wrong-but-non-empty one, as happened earlier with `index.css`). No visibility
        into the actual tool-call trace was available after the fact (no checkpointer configured on
        the exploration agent, so a completed run's intermediate messages aren't inspectable
        afterward) -- if this recurs, adding a checkpointer (or logging each tool call as it
        happens) would be the way to actually see what the model was doing right before submitting.
    - **A second, real, structural bug in the coverage-union fix (item 21/22)**: even after fixing
      the turn-budget/efficiency issues, a real run's plan was rejected by `plan_validator` for not
      covering the literal endpoint string `/api/task-comments` -- but the actual backend routes
      had been legitimately restructured (in earlier work) to `/api/tasks/:taskId/comments` +
      `/api/comments/:commentId`, a real, valid API design improvement. Since the Architecture
      Plan's `api_endpoints` is a frozen snapshot from before the feature was ever implemented, and
      `_collect_cumulative_plan_files`'s union can only reflect what's in *saved plan* `maps_to`
      values (not the literal Architecture Plan requirement, which never changes), **once a
      feature's real API shape evolves past that snapshot, no future revision can ever satisfy the
      old literal string again** -- permanently blocking every subsequent `revise()` call on that
      feature, regardless of plan quality or turn budget. Fixed: `CodePlanValidator.validate(...)`
      (`plan_validator.py`) gained `enforce_endpoint_coverage: bool = True` -- `_plan_with_retries`
      (`agent.py`) passes `enforce_endpoint_coverage=exploration_context is None`, so **endpoint
      coverage remains a hard gate for a first `run()`** (where it's genuinely important that the
      plan covers everything the Architecture Plan promised) **but is skipped for `revise()`**
      (which builds on an already-implemented, already-approved feature whose real API shape can
      legitimately keep evolving). Entity and requirement-ID coverage remain enforced for revisions
      either way -- those track WHAT the feature does, not the exact shape of its API, and are far
      less likely to legitimately go stale the same way. New tests in
      `tests/test_coder_plan_validator.py` (+2: flag skips endpoint coverage only, entity/
      requirement coverage still enforced; flag defaults to `True`).
    - **The actual, real frontend bug the user was hitting**: not a styling gap at all.
      `TaskDetailPage.jsx` already existed, fully built and already using real Tailwind classes
      throughout (card layout, priority/status badges, styled comment list/input) -- but **no
      `<Route path="/tasks/:taskId">` was ever registered** in `App.jsx`, even though
      `TaskflowHomePage.jsx` already links to specific task URLs (`/tasks/123`, etc.). Navigating to
      any of those links rendered a **completely blank page** (confirmed directly with a real
      Playwright screenshot before the fix) -- indistinguishable, to a human, from "the page has no
      styles," since a page that never renders at all looks exactly like one with zero CSS. Fixed
      directly (added the missing `<Route>` + import) rather than through `revise()` again, given
      the multi-hour real cost already spent reproducing the exploration-planner issues above.
      Verified with a real browser screenshot after the fix: `/tasks/123` renders the fully-styled
      Task Details page (including a styled "Failed to load comments" error state, since no live
      backend was connected for this specific check -- expected, not a bug) with zero JS errors,
      and full `coder_verifier.verify()` passes end-to-end (`page reachability` now correctly
      passes too, since `/tasks/:taskId`'s static prefix `/tasks` is registered and linked).
24. **Architecture Agent upgraded end-to-end: coder-friendly Architecture + Implementation Plan,
    project-aware, tool-using, enhanced-SRS-exclusive** -- a 5-milestone user-requested upgrade
    (full plan: it was in `C:\Users\ASUS\.claude\plans\soft-petting-star.md` before being
    overwritten by the next milestone, per this file's own convention). The Architecture Agent
    previously produced an SDS-flavored plan from a single-shot LLM call over one feature's SRS,
    with zero visibility into the rest of the project -- concrete gaps the user pointed at
    directly (the plan wasn't concrete enough for the Coder Agent to act on unambiguously, and
    the agent planned each feature blind to the rest of the project). Diagrams (use case,
    sequence, class) were explicitly **out of scope for this change** and remain exactly as they
    were -- generated deterministically by dedicated modelers from `(srs, plan)`, never by the LLM.
    - **M1 -- `implementation_plan`, an AI-executable blueprint, added to the schema** (`prompt.py`,
      `agent.py`, `sds_validator.py`, `markdown_builder.py`): `backend.files/endpoints/models`,
      `frontend.pages/components_to_reuse/services/routing`, `implementation_order`,
      `constraints` -- concrete file paths, exact endpoint method/path/request-fields/response/
      error-cases, model field lists, matching the scaffold conventions the Coder Agent's own
      planner prompt already teaches (`server/src/routes/...`, `FEATURE_ROUTES_END`/
      `FEATURE_LINKS_END` markers). **`design_views` (the Coder Agent's two load-bearing fields,
      `interface_view.api_endpoints`/`data_view.data_entities`) is completely unchanged** --
      `implementation_plan` is purely additive.
      - New `ArchitectureAgent._ensure_implementation_plan`/`_build_implementation_plan`: a
        deterministic floor guaranteeing every plan -- LLM-authored, single-shot, agentic,
        SRS-derived fallback, or a converted legacy `sds`-type plan -- carries a structurally-valid
        `implementation_plan`, mechanically derived from `design_views` + the SRS when the LLM
        omitted or malformed it. This matters because the fallback rung is a real, frequently-hit
        path (confirmed again in this milestone's own E2E run, see M5 below), so it can never
        produce a schema the validator then rejects.
      - `sds_validator.py`'s `_validate_implementation_plan`: structural presence checks
        conditioned on what the SRS actually asks for (backend.files non-empty only when the SRS
        has api_expectations, etc.) -- same coverage-checking idiom already used for `design_views`.
    - **M2 -- project-aware context (still single-shot at this point)**: new
      `artifact_service.list_project_artifacts(...)` -- the **first project-scoped artifact
      query** in this codebase (every artifact already carries `project_id`, but every existing
      lookup was feature-scoped only). New `ArchitectureAgent._load_previous_architecture_plans`
      uses it to find every OTHER feature's latest APPROVED plan in the same project (including
      the legacy `sds`-type lookup, same fallback the Coder Agent's own architecture-plan loader
      already has). `build_architecture_user_prompt` gained a previous-plans summary (endpoints +
      entities + implementation file paths only, never the full JSON -- the Ollama context budget
      is real) and a project-manifest section (reused `project_memory_service`, same as the Coder
      Agent).
    - **M3 -- agentic, tool-using generation, as a new FIRST rung on the existing reliability
      ladder** (never a replacement for it): new `app/agents/architecture_agent/tools.py`
      (`build_architecture_planning_tools`) and `_generate_raw_output_via_exploration` in
      `agent.py`, modeled directly on the Coder Agent's proven
      `build_revision_planning_tools`/`generate_via_exploration` pattern (read-only tools +
      `submit_architecture_plan(plan_json: str)` + captured dict, `ARCHITECTURE_PLANNING_RECURSION_LIMIT
      = 80`, `GraphRecursionError`/no-submission both treated as "fall through to single-shot").
      **Deliberately NOT built by filtering `build_coder_tools`**: that builder calls
      `workspace_service.ensure_project_repo` at construction time (a side effect that CREATES the
      workspace) -- wrong here, since the Architecture Agent runs before any code exists and a
      project's first feature legitimately has no workspace yet (every workspace tool degrades to
      a clear "no workspace yet" string instead of raising). The ladder is now: agentic exploration
      -> single-shot (now also with M2's project context) -> JSON-repair -> deterministic
      fallback -> proceed-with-caveat -- every existing rung preserved, the agentic one only ever
      precedes them.
    - **M4 -- input/output integration**: input side -- `srs_for_generation = enhanced_srs_json or
      srs_json` used consistently everywhere (prompt builder, validators, all three diagram
      modelers) so an Enhanced SRS, when the (still-stub) Domain Agent someday produces one,
      supersedes the plain SRS entirely rather than both being sent. Output side --
      `coder_agent/prompt.py`'s shared context-section builder (used by BOTH the single-shot and
      agentic revision planners) renders `architecture_plan_json["implementation_plan"]` as a new
      "follow its file paths, endpoint specs, model fields, and implementation order" section when
      present, and gracefully omits it for a legacy plan that predates this milestone (confirmed
      directly against the real, live e-commerce-platform Login plan -- still stored under the
      legacy `sds` artifact type with old-style `introduction`/`design_context` keys -- prompt
      builds with no crash, `design_views`-derived `required_endpoints`/`required_entities` still
      populate correctly since that shape never changed, and the new section is correctly absent).
    - **M5 -- real, live verification, not just synthetic tests**: full suite **199 passed** (up
      from 174). Real E2E: created a genuinely new feature ("Task Search") on the live TaskFlow
      project (`proj_53284a63`, which already has an approved Task Comments plan + a real
      workspace) via the real Requirement Agent -> real Architecture Agent. The agentic rung hit
      its turn limit on this real run and correctly fell through; the single-shot rung's raw LLM
      output was missing every one of the ~15 top-level required keys entirely (a real, severe
      single-shot miss, unrelated to this milestone's own changes) and repair also failed; the
      **deterministic fallback rung produced a complete, valid plan** -- confirming the
      reliability ladder and M1's fallback-schema guarantee both work for real, not just in
      fixtures. The resulting `implementation_plan` had concrete, real content: 3 backend files,
      1 model, 1 page, 6 ordered implementation steps.
      - **Confirmed the actual point of this milestone**: fed this real plan to the real
        single-shot Coder planner (`code_planner.generate`, bypassing the retry loop for a first
        look) -- its `files` list was an **exact match** to the implementation_plan's own file
        paths (`server/src/models/TaskSearchDataEntity1.js`,
        `server/src/routes/task-search.routes.js`, `server/src/app.js`,
        `client/src/services/taskSearchService.js`, `client/src/pages/TaskSearchPage.jsx`), with
        the model's own summary explicitly citing "the approved architecture blueprint." This is
        a measurably more concrete result than the old abstract SDS ever produced for this class
        of feature (the SDS-era planner's documented failure mode was exactly *under*-planning
        backend files -- see the gotcha below, still real, but no longer starting from nothing).
      - **Also confirmed, honestly, a separate real limitation this milestone does NOT fix**:
        that same real plan's `maps_to` field values were unreliable across two different LLM
        calls (once containing the file's own path instead of the required endpoint/entity/FR-ID
        strings; once missing the field structurally) -- the real `_plan_with_retries` call
        exhausted both attempts and raised `CodePlanValidationError`, exactly matching this
        project's **already-documented, pre-existing** Coder Agent planner gotcha (below) that
        predates this milestone entirely. Not conflated with this milestone's own work, and not
        fixed here -- fixing Coder Agent planner reliability was never this milestone's scope.
      - Verified the legacy path directly against the real, live e-commerce-platform Login plan
        (see M4 above) -- confirmed working, not just asserted.
    - New test files: `tests/test_architecture_plan_schema.py`, `tests/test_architecture_project_context.py`,
      `tests/test_architecture_agent_exploration.py`, `tests/test_architecture_enhanced_srs.py`
      (33 tests total across all four, all passing) plus `scripts/run_taskflow_architecture_e2e.py`
      (the real E2E script, kept as a reusable verification tool matching this repo's existing
      `scripts/run_*_manual.py` convention).
    - **Real state**: `proj_53284a63` (TaskFlow) gained a new feature, `feature_29fa0ed4` ("Task
      Search"), with an approved SRS and an approved Architecture Plan (`artifact_dc772d18`,
      approved during this milestone's own M5c verification) plus rendered use case/sequence/class
      diagrams -- left in place as real, inspectable verification output, not debris. No code was
      generated for it (the Coder Agent step was only planning-level, per the milestone's own
      scope) -- a natural next feature to actually build out in a future session.

25. **Use Case Diagram rewrite: accurate, complete, UML-standard-compliant** -- a user-requested
    6-milestone rewrite (full plan: `C:\Users\ASUS\.claude\plans\soft-petting-star.md`, overwritten
    since per this file's convention). The user identified the generated use case diagrams as not
    accurate/complete enough, with three confirmed real failures directly from saved `.puml`
    artifacts: **garbled names** (`"A Task The Can"`, `"A Enters A Keyword"`, `"Initiate Page"` --
    raw SRS sentence fragments mangled by regex), **CRUD over-fragmentation** (`"Validate Email"`/
    `"Validate Password"`/`"Validate Credentials"` as three separate use cases for one login flow),
    and **undetected near-duplicates** (`"Initiate Forgot Password Process"` vs. `"Initiate Recovery
    Flow"` citing the same requirement). Root cause: the LLM only ever produced a loose categorized
    `usecase_specification_json`; a deterministic modeler then synthesized the actual use case
    names via regex phrase-surgery on raw SRS sentences (`_make_validation_use_case_name`,
    `_make_extension_name`, `_extract_error_topic`, `_extract_recovery_topic`, `_short_topic`) --
    fundamentally NLP-by-regex, reliably broken on ordinary English. **Sequence and class diagrams
    were explicitly out of scope and remain unchanged.**
    - **M1 -- strengthened the LLM-facing schema/prompt** (`prompt.py`): the LLM now produces a
      near-final `use_cases: [{name, type: main|included|extension, description,
      related_requirements, included_in, extends}]` list directly, replacing the old loose
      `primary_use_cases`/`included_behaviours`/`extension_behaviours`/`exception_flows` shape.
      New rules: exactly one `main` entry (never the feature name restated), 2-5 word
      action-oriented names with no leftover fragment words, explicit anti-CRUD-fragmentation and
      dedup-by-meaning instructions, mandatory accurate `related_requirements` (this powers M3's
      new duplicate/fragmentation checks).
    - **M2 -- thinned `usecase_modeler.py`: trust the LLM's list, add real dedup**: new
      `_build_use_cases_from_specification` trusts the LLM's `use_cases[]` directly (no regex
      sentence-mining) whenever it's non-empty; the old `_build_main_use_cases`/
      `_build_included_use_cases`/`_build_extension_use_cases` become fallback-only (invoked only
      when the specification is genuinely empty). Replaced the old exact-name-only
      `_dedupe_and_merge` with a 3-pass `_merge_near_duplicates`: exact normalized name, identical
      non-empty `related_requirements` sets (catches synonym-level duplicates no string metric
      would, e.g. the Forgot-Password/Recovery-Flow case above), and stem/token Jaccard overlap on
      names (small private stemmer, no embeddings library -- nothing in this codebase uses
      `sentence-transformers` directly today).
    - **M3 -- strengthened `usecase_validator.py`**: new `_validate_use_case_name_quality` (rejects
      names containing a standalone article/determiner/possessive-pronoun/Given-When-Then token --
      catches the real garbled examples, while deliberately excluding generic auxiliary verbs like
      `do`/`is`/`are` so the pre-existing `"Do Something"` regression fixture keeps passing); new
      `_validate_use_case_fragmentation` (flags 2+ included/extension use cases under the same main
      use case sharing a leading `INTERNAL_STEP_VERBS` word, or sharing an identical non-empty
      `related_requirements` set -- catches the real `"Validate X"/"Validate Y"/"Validate Z"`
      anti-pattern). **An initially-added fourth check ("main use case name just restates the
      feature name") was removed after a real regression** -- see the gotcha below.
    - **M4 -- new targeted use-case repair-retry loop**: `_complete_usecase_model` became `async`
      and now runs the full `UseCaseQualityValidator` right after building the model (moved
      earlier than before); on a quality failure it calls a new, cheap, targeted
      `_repair_usecase_specification` (one `provider.invoke_agent` call with just the FR list,
      user_stories, out_of_scope, the failed specification, and the exact validator error text --
      mirrors `CoderAgent._plan_with_retries`'s "generate → validate → retry with the specific
      error fed back" idiom, capped at `MAX_USECASE_REPAIR_ATTEMPTS = 2`). **Deliberately gated off
      entirely when the specification is genuinely empty** (the true last-resort fallback rung) --
      making a new LLM call from the rung whose whole purpose is "the LLM already failed twice"
      would defeat its purpose. Never raises for a quality failure; the later
      `_validate_full_output` call remains a final, harmless re-confirmation.
    - **M5 -- honest, simplified fallback naming + dead-code removal**: the fallback path (reached
      only when the specification is truly empty) now names the main use case from `feature_name`
      alone (no business-goal regex-mangling -- a feature name like "Login" or "Task Comments" is
      already a reasonable use case name); new `_build_fallback_supporting_use_case` names
      supporting use cases via best-effort stem-overlap match against `user_stories[].goal`, or one
      gentle `_clean_use_case_name` truncation pass otherwise -- no multi-pass regex verb/topic
      extraction. `_clean_use_case_name` itself was hardened to strip standalone filler words
      (`NAME_FILLER_WORDS`) from anywhere in a name, not just the leading position -- a real test
      failure showed the 5-word truncation alone could still leave a mid-sentence "the"/"my" as a
      leftover fragment (e.g. "Validate The User Credentials Against"). **Deleted, confirmed dead**
      in `agent.py`: `_build_usecase_from_srs` (~240 lines, its result was always immediately
      overwritten by the following `_complete_usecase_model` call), plus
      `_build_security_flow_records` (a bonus find -- zero callers anywhere, confirmed via
      `grep -rn` across `app/`), `_build_usecase_traceability`, `_verb_phrase_from_feature`,
      `_usecase_name_from_text`. In `usecase_modeler.py`: the entire old regex-phrase-surgery
      cluster (`_build_main_use_case_name`, `_make_validation_use_case_name`, `_make_action_name`,
      `_make_extension_name`, `_infer_field_name`, `_extract_error_topic`,
      `_extract_recovery_topic`, `_short_topic`, `_is_generic_use_case_name`) plus their
      now-unused `COMMON_FIELDS`/`GENERIC_USE_CASE_NAMES` class constants.
    - **A real regression found and fixed during M6's own test run, not caught by design review**:
      the M3 "main use case name restates the feature name" check directly contradicted M5's own
      design (fallback names the main use case from `feature_name` verbatim). For any multi-word
      feature name (e.g. "Task Comments"), the honest fallback would deterministically trip that
      check every time, and `test_architecture_agent_exploration.py`'s
      `test_exploration_submission_is_used_without_any_single_shot_call` caught it immediately --
      the check made the deterministic fallback (the one rung that must always succeed) fail its
      own validation, cascading the whole reliability ladder past single-shot into JSON-repair.
      **Removed the check entirely** rather than special-casing it: a literal feature-name match
      is not actually incorrect UML (single- and multi-word feature names like "Login" or "Task
      Comments" are both conventional, legitimate use case names on their own), just not maximally
      descriptive -- not worth breaking the fallback's designed reliability over.
    - **A second real bug found only by the M6 real E2E run** (not by any unit test, since it
      requires two different fallback code paths landing on the same 5-word-truncated name): the
      deterministic fallback produced a genuine cross-category duplicate --
      `"Find Specific Tasks Quickly Using"` appeared as BOTH an included use case and an extension
      use case for the real Task Search feature, because `_merge_near_duplicates` was only ever
      called once per category list (`included_use_cases`/`extension_use_cases` separately), so a
      duplicate spanning the include/extend boundary was invisible to it. Fixed with a new
      `_merge_near_duplicates_across_categories` (runs the same 3-pass dedup over
      included+extension combined, then splits back by each surviving item's own `category` field,
      first-seen-category-wins on a cross-boundary collision). Confirmed fixed against the exact
      real SRS that produced the bug (`outputs/taskflow/feature-task-search/01_requirements/
      task_search_srs_v2.json`): before the fix, `UseCaseQualityValidator.validate()` raised
      `"Duplicate use case name found: Find Specific Tasks Quickly Using"`; after, it passes clean.
    - **Real, live verification, not just synthetic tests**: new
      `tests/test_architecture_usecase_modeler.py` (16 tests -- LLM-specification trust/dedup +
      fallback naming/traceability/relationships), `tests/test_architecture_usecase_validator_quality.py`
      (7 tests -- real garbled names, real 3-way "Validate X" fragmentation, legitimate
      "Validate Credentials" not raising, shared-requirements duplicate detection), and
      `tests/test_architecture_usecase_repair.py` (4 tests -- repair fixes on first attempt, repair
      never succeeds falls through without raising, repair retries up to
      `MAX_USECASE_REPAIR_ATTEMPTS`, repair loop skipped entirely for the true fallback rung). Full
      suite (excluding the three pre-existing Docker-dependent files that fail in this environment
      for unrelated reasons -- `test_coder_tools.py`/`test_coder_verify.py`/`test_render_checker.py`,
      all needing a reachable Docker daemon this machine doesn't have running): **167 passed, 0
      failed**. Real E2E: ran `scripts/run_taskflow_architecture_e2e.py` for real (new feature
      "Task Search" on the live TaskFlow project, `feature_244e26d1`) -- this is the run that
      surfaced the cross-category duplicate bug above. Also exercised the real, unchanged
      `ArchitectureAgent.revise()` for this feature (one real LLM call, not the full multi-turn
      exploration rung) specifically to confirm the new `async _complete_usecase_model` signature
      works there too, and to produce a v2 diagram reflecting the cross-category-dedup fix for
      real -- confirmed clean: `outputs/taskflow/feature-task-search/03_architecture/
      task_search_usecase_v2.puml` has one "Task Search" main use case and one, single, correctly
      `<<include>>`d "Find Specific Tasks Quickly Using" use case, versus the original (git HEAD)
      v1's `"Validate Date"`/`"Initiate Recovery Flow"`/`"A Enters A Keyword"` garbled set.

26. **Sequence + Class Diagram rewrite: dynamic, accurate, UML-standard-compliant** -- a
    user-requested 6-milestone rewrite (full plan:
    `C:\Users\ASUS\.claude\plans\soft-petting-star.md`, overwritten since per this file's
    convention), applying the same LLM-driven pattern item 25 proved for use cases to the
    remaining two diagrams. Confirmed both were 100% deterministic before this: `sequence_modeler.py`
    always emitted the SAME fixed 5-8 message template (submit -> validate -> alt success/fail ->
    optional repo/DB round-trip -> optional external token call) for every feature, only the
    endpoint/participant names varying; `class_modeler.py` always built the same
    Controller/Service/Repository/DTO/Entity skeleton, with attribute content coming from
    `_infer_fields_from_text`/`COMMON_FIELDS` keyword-guessing whenever `design_views`'
    request/response models or data entities arrived as free text. Confirmed real UML-standards
    gaps by reading both builders directly: class relationships had **no multiplicity/cardinality
    notation at all**; the sequence builder supported only `alt`/`opt`/`else` fragments and
    `sync`/`return`/`self` messages -- no `loop` fragment, no async message type. **Hard
    constraints honored throughout, unlike item 25's scope**: the use case pipeline
    (`usecase_modeler.py`/`usecase_validator.py`/`usecase_builder.py`/`usecase_specification_json`/
    `_complete_usecase_model`/`_repair_usecase_specification`) was never touched, and
    `architecture_plan_json`'s `design_views`/`implementation_plan` schema was never touched --
    the new LLM-authored input is two new, additional, sibling top-level fields.
    - **M1 -- new `sequence_specification_json`/`class_specification_json` schema + rules**
      (`prompt.py`): both fully LLM-authored (participants/interactions and classes/relationships,
      not a hybrid of deterministic-skeleton-plus-LLM-content), added as siblings of
      `usecase_specification_json` in the same top-level JSON object -- automatically inherited by
      the agentic prompt via the existing `_SHARED_RULES_AND_SCHEMA` string-split, same zero-drift
      mechanism the use-case schema already relies on. New "Sequence/Class Diagram Specification
      Rules" blocks: sequence requires real actor/boundary/control participants and a real
      main-success-then-alternative flow (not a template), new `loop_start`/`async` vocabulary for
      genuinely repeated/fire-and-forget behavior; class requires real, feature-specific
      DTO/entity attributes (never a placeholder single field) and mandatory
      `source_multiplicity`/`target_multiplicity` on every association/aggregation/composition.
      New `SEQUENCE_REPAIR_SYSTEM_PROMPT`/`build_sequence_repair_prompt` and
      `CLASS_REPAIR_SYSTEM_PROMPT`/`build_class_repair_prompt`, structurally identical to the
      use-case repair prompt but fully independent.
    - **M2 -- thinned both modelers**: new `_build_from_specification` in each trusts the LLM's
      content directly (deterministic id assignment + name-to-id resolution only -- a message/
      relationship referencing an unresolvable participant/class name is skipped, not crashed);
      the entire old template/keyword-derivation body in each was demoted to
      `_build_fallback`/`_build_fallback_classes_and_relationships`, invoked only when the
      specification is genuinely empty, unchanged in behavior.
    - **M3 -- new validator quality checks**: `sequence_validator.py` gained
      `_validate_message_quality` (flags a message repeated verbatim between the same two
      participants outside a loop fragment -- correctly suspended for anything nested inside a
      `loop_start`/`end` block, including nested `alt`/`opt`) and extended fragment-balance to
      accept `loop_start`. `class_validator.py` gained `_validate_multiplicity` (every
      association/aggregation/composition must carry standard UML cardinality notation on both
      ends; dependency/inheritance/generalization exempt) and `_validate_class_quality` (flags an
      anemic dto/entity with zero attributes, or one whose attributes are ALL generic placeholder
      names like a lone `id`/`field`/`value`/`data` -- a genuine mix of real and generic-named
      fields is not flagged).
    - **M4 -- new, fully independent repair-retry loops**: `_complete_sequence_model`/
      `_complete_class_model` became `async`, mirroring `_complete_usecase_model`'s shape exactly
      (`MAX_SEQUENCE_REPAIR_ATTEMPTS`/`MAX_CLASS_REPAIR_ATTEMPTS = 2`, own new
      `_repair_sequence_specification`/`_repair_class_specification`, gated off entirely when the
      specification is genuinely empty -- no LLM call from the rung whose purpose is "the LLM
      already failed twice") -- never sharing prompts, state, or calls with the use-case repair
      loop. All 5 existing call sites for each (3 ladder rungs, the fallback rung, `revise()`)
      updated to `await`.
    - **M5 -- additive builder changes, fully backward compatible**: `sequence_builder.py` gained
      `loop` fragment rendering and an `async` (open-arrowhead `->>`) message type, alongside the
      unchanged `sync`/`return`/`self`. `class_builder.py` gained UML cardinality label rendering
      (`"1" --> "0..*"`-style) on relationships that carry `source_multiplicity`/
      `target_multiplicity`, rendering exactly as before when either is absent (e.g.
      dependency/inheritance). The fallback's one deterministic `association` relationship
      (Repository manages Entity) was given a default `"1"`/`"0..*"` multiplicity so the fallback
      path itself passes the new multiplicity gate, not just the LLM-driven path.
    - **Two real bugs found only by the M6 real E2E run, both in the pre-existing, unmodified
      fallback logic** (not by any unit test, since both require a specific upstream data shape
      the synthetic fixtures didn't have): re-running `ArchitectureAgent.revise()` for real against
      `feature_244e26d1` (the same real TaskFlow "Task Search" feature item 25 created) surfaced
      that its real, previously-approved architecture plan's `design_views.interface_view.
      api_endpoints` contains the exact same endpoint (`GET /api/task-search`) as **two separate
      dict entries** -- a pre-existing, upstream architecture-plan data-quality issue, out of scope
      to fix at the source per this milestone's own "don't touch the architecture plan" constraint.
      This silently produced (a) a genuine duplicate sequence message (now correctly rejected by
      the new `_validate_message_quality` check) and (b) a genuine duplicate class operation on the
      Controller (`getApiTaskSearch` twice, since `_controller_operations` had no dedup pass unlike
      `_service_operations`, which already called `_dedupe_operations` on its own result). Fixed
      both at the point each modeler *consumes* the endpoint list, not by touching the plan itself:
      new `_dedupe_endpoints` in `sequence_modeler.py`'s fallback (normalized method+path key), and
      `_controller_operations` in `class_modeler.py` now calls the already-existing
      `_dedupe_operations` just like `_service_operations` does. Confirmed fixed directly against
      the real data that produced the bug.
    - **A third, more serious real bug found only by the same E2E run**: `revise()` had **no
      safety net around its own `_validate_full_output` call**, unlike the main generation ladder's
      true last-resort rung (`_build_fallback_architecture_output`'s caller wraps it in a
      try/except and proceeds with a caveat on the plan -- an already-established, approved
      pattern in this exact file). Since `revise()` always uses an empty usecase/sequence/class
      specification (only the plan text itself is revised by the LLM; every diagram always comes
      from the deterministic fallback), a heuristic validator failure on ANY diagram would crash
      the entire revision outright with no recourse -- a real, reproducible crash confirmed live
      (a genuinely anemic `dto` class from the SAME real feature's architecture plan, whose
      request/response model fields are literally named `"field"` upstream with the real
      description stuffed into a `"format"`/`"description"` key instead -- another pre-existing,
      out-of-scope-to-fix architecture-plan data-quality issue). Fixed by wrapping
      `_validate_full_output` in `_revise_architecture_plan_output` with the identical
      try/except-and-caveat-note pattern already used by the main ladder's fallback rung, rather
      than inventing new handling. Confirmed fixed live: `revise()` now completes with
      `status: revised` and a `human_approval_note` caveat instead of raising.
    - **A confirmed, honest model-quality observation, not a code bug**: a real single-shot LLM
      call (bypassing the slow, turn-limited agentic exploration rung on purpose, to keep real
      verification cheap) against the real Task Search SRS twice failed to produce ANY
      schema-conformant output at all -- once inventing an entirely different, flattened JSON shape
      with none of the required top-level keys, once returning a near-empty 2-character response.
      This is the SAME class of pre-existing single-shot unreliability item 25's M5 already
      documented (a severe single-shot miss, unrelated to this milestone's own changes) -- but the
      now-larger combined schema (three full specification blocks instead of one) plausibly makes
      it worse for this local model by pressuring its generation budget. Not fixed here (out of
      scope -- this milestone's job was the pipeline, not single-shot model reliability); the
      existing reliability ladder (single-shot -> JSON-repair -> deterministic fallback ->
      proceed-with-caveat) already tolerates this without crashing, confirmed by the real
      `revise()` runs above landing cleanly on the fallback path both times.
    - **Real, live verification, not just synthetic tests**: new
      `tests/test_architecture_sequence_modeler.py` (7 tests), `tests/test_architecture_class_modeler.py`
      (7 tests) -- LLM-specification trust (including unresolvable-name skip, loop/async
      preservation, invalid-enum-value defaulting) + fallback path; `tests/test_architecture_sequence_validator_quality.py`
      (5 tests -- duplicate-message detection in/out of loops, nested-fragment suppression,
      loop fragment balance) and `tests/test_architecture_class_validator_quality.py` (9 tests --
      anemic/placeholder-only dto/entity detection, multiplicity presence/notation/exemption) --
      new files, no pre-existing sequence/class quality test files existed; `tests/test_architecture_sequence_repair.py`/
      `tests/test_architecture_class_repair.py` (4 tests each -- repair fixes on first attempt,
      repair never succeeds falls through without raising, repair retries up to the attempt cap,
      repair loop skipped entirely for the true fallback rung). Full suite (same 3 pre-existing
      Docker-dependent exclusions as item 25): **203 passed, 0 failed** (up from 167). Real E2E:
      re-ran the real, unchanged `ArchitectureAgent.revise()` against `feature_244e26d1` four
      times across the fix cycle above, each run driven by an actual real bug the previous run's
      output exposed -- (1) crashed on the sequence duplicate-message validation error (no safety
      net yet); after adding the `_dedupe_endpoints` fix, (2) still crashed, now on the class
      anemic-DTO validation error, which is what exposed `revise()`'s missing safety net in the
      first place; after adding that safety net, (3) completed successfully with an honest
      caveat, but its own v3 `.puml` output visually revealed the *separate*, validator-uncaught
      duplicate-operation bug in the Controller class; after adding the `_controller_operations`
      dedupe fix, (4) completed fully clean. Final `task_search_sequence_v4.puml`/
      `task_search_class_v4.puml` confirmed directly: no duplicate messages/operations, real
      `CLS_REPOSITORY "1" --> "0..*" CLS_ENTITY_00N : manages` multiplicity notation rendering
      correctly, and an honest, accurate `human_approval_note` caveat surfacing the genuinely
      anemic (upstream-data-caused) DTO fields for human review rather than hiding the problem.
    - **Real state**: `feature_244e26d1` (the same TaskFlow "Task Search" feature from item 25)
      gained `task_search_sequence_v3/v4.puml`/`.png` and `task_search_class_v3/v4.puml`/`.png`
      (v1/v2 from item 25's use-case verification predate this milestone's fixes and are left in
      place, not debris) plus three more Architecture Plan JSON/Markdown versions from the three
      real `revise()` calls above -- all left in place as real, inspectable verification output.

27. **Architect Agent: dynamic, tool-using, reliably-generated diagrams** -- a user-requested
    5-milestone follow-up to item 26, prompted by the user directly observing that every generated
    sequence/class diagram still had the identical structure regardless of feature (full plan:
    `C:\Users\ASUS\.claude\plans\soft-petting-star.md`, overwritten since per this file's
    convention). **Confirmed with hard evidence**: read `login_class_v6.puml`,
    `task_comments_class_v1.puml`, and every `task_search_class_v*.puml` directly -- all had the
    exact same Controller/Service/Repository/DTO/Entity skeleton, with the Repository's operations
    being the **literal, hardcoded strings** `findRequiredData()`/`saveChanges()` in every single
    one regardless of feature. This is the deterministic fallback's own literal output --
    item 26's LLM-authored path was essentially never reached in real usage.
    - **Root cause, confirmed by direct testing**: the single mega-call (agentic exploration or
      single-shot) asked the local LLM to produce `architecture_plan_json` (~15 top-level keys
      including a detailed `implementation_plan`) **plus** `usecase_specification_json` **plus**
      `sequence_specification_json` **plus** `class_specification_json`, all in one JSON response.
      Real testing against this exact model (item 26's own verification) showed it failing to
      produce schema-conformant output at that size -- once inventing an entirely different
      flattened JSON shape, once returning a near-empty 2-character response. The agentic
      exploration rung's tools were all about gathering context for the *plan* -- none helped the
      model construct or validate the diagrams themselves.
    - **Independent design review before implementation** (a Plan agent that read the full real
      implementation and this file's own history of a *different* agentic loop -- the Coder
      Agent's revision planner -- taking up to ~4.5 real hours on this same local model) refined
      the initial one-combined-loop design into **two sequential, independently-gated loops**
      (sequence first, then class informed by the finalized sequence names) for two concrete
      reasons: smaller per-loop turn budget, and -- more importantly -- **nothing structurally
      keeps a class diagram's names consistent with its sequence diagram's names once both are
      freely LLM-authored** (today's deterministic fallback only agrees because it derives both
      from the same feature name mechanically); running class second with a
      `read_finalized_sequence_names` tool makes consistency a property of the design, not a
      hoped-for prompt convention.
    - **M1 -- shrank the main plan prompt back down** (`prompt.py`): removed
      `sequence_specification_json`/`class_specification_json` and their rule blocks from
      `ARCHITECTURE_AGENT_SYSTEM_PROMPT` entirely (also fixed `tools.py`'s
      `submit_architecture_plan` docstring, which independently told the tool-calling LLM to
      produce the same two fields via the tool schema itself, not just the system prompt) -- the
      main call goes back to just `architecture_plan_json` + `usecase_specification_json`, a
      reliability win for that call on its own. New, relocated (not deleted) content split into
      four new prompt pairs: `SEQUENCE_DIAGRAM_AGENTIC_SYSTEM_PROMPT`/
      `build_sequence_diagram_user_prompt` and `CLASS_DIAGRAM_AGENTIC_SYSTEM_PROMPT`/
      `build_class_diagram_user_prompt` for the two new agentic loops; `DIAGRAM_FOCUSED_BOTH_
      SYSTEM_PROMPT`/`build_diagram_focused_both_prompt` and `DIAGRAM_FOCUSED_CLASS_ONLY_
      SYSTEM_PROMPT`/`build_diagram_focused_class_only_prompt` for the new non-agentic fallback
      tier.
    - **M2 -- new `diagram_tools.py`**: `build_sequence_diagram_tools`/`build_class_diagram_tools`,
      each returning read tools (`read_functional_requirements`/`read_acceptance_criteria`/
      `read_interface_and_data_context`), a **validate-in-the-loop tool**
      (`validate_sequence_draft`/`validate_class_draft` -- parses the model's draft, runs it
      through the real modeler+validator, returns `"VALID"` or the exact error text so the model
      can self-correct BEFORE submitting, not just react after a final failure), and a submit
      tool. The class builder's tools additionally include `read_finalized_sequence_names`.
      Deliberately no "read a previous feature's diagram" tool on either builder -- the whole
      point is diagrams grounded in THIS feature's real content, not a structural precedent
      pulling the model back toward sameness. Each validate tool tracks a failed-attempt counter
      and, after 3 failures, appends a soft nudge ("submit your current best draft now") to its
      own return text -- the same "efficiency-hint feedback" idiom already established for the
      Coder Agent's revision planner in this codebase, so an unproductive loop is more likely to
      still submit *something* before the hard recursion-limit backstop discards everything.
    - **M3 -- new agentic diagram-generation steps in `agent.py`**: `SEQUENCE_DIAGRAM_RECURSION_
      LIMIT`/`CLASS_DIAGRAM_RECURSION_LIMIT = 20` (smaller than the main plan's 80 -- each loop
      covers one narrow artifact). New `_generate_sequence_diagram_via_exploration`/
      `_generate_class_diagram_via_exploration`, mirroring `_generate_raw_output_via_exploration`'s
      exact `create_agent`/`ainvoke`/`GraphRecursionError` pattern at a smaller scope. The class
      step is only ever invoked after the sequence step has already succeeded.
    - **M4 -- new `_complete_diagram_models`, replacing 5 call sites**: three tiers, most-dynamic
      first -- (1) the two sequential agentic loops; (2) a focused, non-agentic single-shot call
      for whichever specification(s) are still missing (combined, if sequence itself failed since
      there's nothing yet to keep class consistent with; class-only with the finalized sequence
      embedded, if only class failed -- **a successful sequence result is never discarded just
      because class alone failed**); (3) the existing deterministic fallback inside the modelers,
      unchanged, reached only if both above produce nothing. **A real design subtlety found while
      implementing this**: `parsed` is recreated fresh at every ladder rung within
      `_generate_architecture_output` (confirmed by reading the code), so memoizing "has the
      agentic tier been attempted" *inside* `parsed` -- the review's original suggestion -- would
      not actually survive a rung cascade. Fixed by threading a separate
      `diagram_generation_state` dict explicitly from the caller instead (the same dict passed to
      every `_complete_diagram_models` call within one `_generate_architecture_output` invocation),
      which both bounds the expensive agentic tier to one attempt per outer call AND caches a
      successful result outright for free reuse by a later cascaded rung, an improvement on the
      original "memoize a bool" suggestion. `attempt_agentic=False` (used for the deterministic-
      fallback rung and `revise()`) skips tier 1 entirely -- both still get real, feature-grounded
      diagrams via tier 2 instead of a fixed template, without the potentially-long agentic tail
      on paths that are supposed to be fast/reliable.
    - **Real, live verification, not just synthetic tests**: new `tests/test_architecture_diagram_
      tools.py` (15 tests) and `tests/test_architecture_diagram_exploration.py` (11 tests --
      capture/raise contracts for both exploration methods, and the full `_complete_diagram_
      models` rung matrix: both-agentic-succeed, sequence-succeeds-class-fails, sequence-fails,
      both-fail, `attempt_agentic=False`, and memoization across two simulated cascading calls).
      One pre-existing test (`test_exploration_submission_is_used_without_any_single_shot_call`)
      needed updating -- its old assertion ("exploration succeeding means zero single-shot calls")
      no longer held now that diagram generation is fully decoupled from the plan's own success;
      fixed by extending its mocks to also simulate the two new diagram exploration steps
      succeeding, preserving the test's original intent rather than weakening the assertion. Full
      suite (same 3 pre-existing Docker-dependent exclusions as before): **229 passed, 0 failed**
      (up from 203). Real E2E: called `_complete_diagram_models(attempt_agentic=True)` directly
      against the real, already-established architecture plan for `feature_244e26d1` (Task
      Search) -- isolating the new capability from the separately-slow main plan-generation
      exploration, which was not what this verification targeted. **Result, recorded honestly**:
      the agentic **sequence** loop hit its 20-turn limit without submitting (~4.5 real minutes,
      7 LLM calls) -- but the new **focused single-shot fallback tier** then produced genuinely
      dynamic, feature-specific content in one call: sequence messages like "Enters keyword in
      search bar" -> "Validate keyword length (min 2 chars)" -> queries against two real data
      entities, and a class diagram with real DTO attributes (`TaskSearchResult.taskId/title/
      description/detailUrl`) and real distinct operations (`searchTasks`, `findMatchingTasks`) --
      **not** the old `findRequiredData`/`saveChanges` literals. Both validators passed. Total
      elapsed: 505s. **A real rendering bug found and fixed from this run**: the LLM authored
      operation parameters as rich `{"name", "type"}` objects rather than plain strings; the
      schema never constrained the shape, and `class_modeler.py`'s `_operation_record` was
      rendering them via a raw Python dict `str()`, producing PlantUML like
      `+handleSearchRequest(name request, type TaskSearchRequest)`. Fixed with a new
      `_parameter_text` helper that renders either shape as a clean `"name: type"`. Also exercised
      the real, updated `revise()` (focused single-shot tier only, `attempt_agentic=False`) for a
      second, independent real run -- this one triggered item 26's own reactive class-repair loop
      for real (`ClassDiagramValidationError: Entity class 'TaskSearchController' has no
      attributes`), which self-corrected on its one retry and completed cleanly, confirming both
      milestones' mechanisms compose correctly. **An honest, un-fixed observation from that same
      run**: the repair fixed the *reported* anemic-attribute error, but not a deeper stereotype
      mismatch it didn't directly address -- the final diagram has "TaskSearchController" labeled
      `<<entity>>` and "TaskSearchService" labeled `<<control>>` (swapped from what their names
      imply). This is a real limitation of the repair loop's design (it only addresses the exact
      validator error text, not a full semantic review) inherited from item 26, not introduced
      here -- left as-is and recorded honestly rather than expanding scope to fix it now.
    - **Real state**: `feature_244e26d1` gained `task_search_sequence_v5.puml`/`.png` and
      `task_search_class_v5.puml`/`.png` (from the real `revise()` run above) plus another
      Architecture Plan JSON/Markdown version -- left in place as real, inspectable verification
      output, including the honest stereotype-mismatch quirk noted above.

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
  **Re-confirmed during the Architecture Agent upgrade (item 24)**, in a new variant: the
  `files` list itself was excellent (an exact match to the new `implementation_plan`'s file
  paths -- a real, measurable improvement over the SDS era), but `maps_to` values were
  unreliable across separate real calls (once the file's own path instead of the required
  endpoint/entity/FR-ID strings, once missing structurally) -- `_plan_with_retries` correctly
  exhausted its attempts and raised, rather than passing through a plan that would silently fail
  Coder Agent coverage. A better `implementation_plan` measurably sharpens *what* the planner
  plans; it does not yet fix this separate, still-open `maps_to`-reliability gap.
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
- **RESOLVED (item 29): asking the LLM to retype the entire SRS verbatim was the actual defect,
  not a model-capacity ceiling.** The Domain Agent gotcha directly above (three models, four
  attempts, all structurally failing to reproduce a full two-part `enhanced_srs_json` +
  `domain_improvements_json` JSON blob) was diagnosed at the time as "a genuine local-model-
  capacity limitation." The user reported the Domain Agent still wasn't enriching anything and
  asked for a real fix, not just a documented limitation — redesigning the LLM contract so it
  proposes only a SMALL enrichment PLAN (new items + description enrichments, no IDs to invent,
  no SRS retyping) and letting deterministic Python (`DomainAgent._apply_enrichment_plan`) merge
  that into a full SRS copy **fixed it outright**: `qwen3-coder:latest` succeeded on the very
  first attempt, 3/3 real runs, no fallback triggered, for both the `Login` feature and a brand
  new `Item Management` CRUD feature (`QuickCart` project) — see item 29 below. The lesson: when
  a local model fails a large structured-output task, first ask whether the task itself can be
  shrunk before concluding the model can't handle it. See `app/agents/domain_agent/agent.py`'s
  and `prompt.py`'s module docstrings for the full design rationale.
- **RESOLVED (item 29): the Architecture Agent "taking over an hour" was a GPU/VRAM mismatch, not
  a hang.** `qwen3-coder:latest` is a 30.5B-parameter Q4 model (~18GB) on a machine with only a
  6GB GPU (RTX 4050) — Ollama could only offload ~3.4GB to VRAM, running ~85% of the model on
  CPU. A trivial "say OK" prompt didn't even complete in 15 seconds. Confirmed via `ollama ps`
  (`size_vram` far below the model's real size) and `nvidia-smi` (6141MiB total VRAM). Fix:
  switched `DEFAULT_LLM_MODEL` and `AGENTIC_MODEL_OVERRIDE` (both `.env` and the live Mongo-
  backed `store.llm_settings`) to `llama3:latest` (4.7GB, the only locally-cached model that
  actually fits this GPU) — Architecture Agent then completed in ~4.5 minutes instead of stalling
  past 90. **If this machine ever gets more VRAM, or a smaller code-specialized model is pulled
  (e.g. `qwen2.5-coder:7b`, ~4.7GB), revisit `AGENTIC_MODEL_OVERRIDE` specifically** — llama3 is a
  general instruct model, not code-specialized, and was only chosen because it's what already fit
  and was already cached.
- **UI/UX Agent had no reliability ladder at all for its two riskiest steps -- fixed (item 29).**
  `metadata_modeler.py` already had a JSON-parse repair ladder, but the SEPARATE coverage/
  structure validator call in `agent.py` had zero retries: any schema-valid-but-incomplete output
  (e.g. a page missing one of the required `states`) crashed the whole run immediately. Worse,
  `UIMetadataValidator.validate()`'s `if not errors:` gate meant only ONE category of problems
  was ever revealed per attempt — fixing the "states" gap on repair just exposed a previously-
  hidden `covers_requirements` gap on the next attempt, one layer at a time. Fixed both: the
  validator now only skips coverage checks when the structure is genuinely unsafe to inspect
  (not a list, or a page isn't a dict) — everything else reports all real errors together, so a
  single repair attempt sees the full picture. `_generate_and_validate_metadata` now retries up
  to `MAX_VALIDATION_REPAIR_ATTEMPTS = 4` (real testing against `llama3:latest` showed the
  missing-ID count genuinely shrinking each round -- 6→4→1 in one run -- true convergence, not
  flailing, which is why the bound is higher than Requirement/Domain/Architecture's usual "one
  repair"). Component generation got the same treatment: a real run hit
  `ReferenceError: Item is not defined` (the model factored a per-row `<Item />` sub-component
  instead of inlining it) — added rule 9 to `COMPONENT_GENERATOR_SYSTEM_PROMPT` explicitly
  forbidding this, plus `component_generator.repair_for_render_error` /
  `UIUXAgent._repair_page_components` to feed the real browser console error back for up to
  `MAX_RENDER_REPAIR_ATTEMPTS = 3` attempts (real testing showed a repair can trade one error for
  a different one -- fixing the ReferenceError once produced a JSX syntax error instead -- so one
  attempt was provably not always enough).
- **Playwright's per-call `Locator.screenshot(timeout=...)` kwarg does not reliably override the
  default timeout in this environment -- confirmed by direct testing** (a call with
  `timeout=8000` still took the full ~30s default before failing). `page.set_default_timeout(N)`
  does work correctly (confirmed: set to 5000, failed at exactly 5.0s). `preview_renderer.py` now
  calls `page.set_default_timeout(90000)` right after `browser.new_page(...)` instead of passing
  `timeout=` to the screenshot call itself.
- **A preview-render failure that reproduces only inside the live LangGraph-invoked pipeline, not
  in direct isolation -- still unexplained, worked around rather than root-caused.** A real
  `item-management-page` render (`QuickCart`/`Item Management`, item 29) failed with
  `Locator.screenshot: Timeout ... element is not visible` -- consistently, across many retries,
  even after confirming `page.set_default_timeout(90000)` was genuinely honored (the error
  message itself changed from `~30000ms` to `~90000ms exceeded`, so the fix was real, but the
  element still never stabilized in 90 real seconds). Extensive direct testing could not
  reproduce this: the exact same JSX + mock_props, run via `sync_playwright()` directly, via
  `asyncio.to_thread` from a plain async function, and via `async_playwright()` natively, all
  rendered successfully and quickly every time. The only remaining unverified difference is the
  live LangGraph/MongoDB-checkpointer execution context itself (nested thread/event-loop
  interaction with Playwright's sync API that a standalone script can't reproduce). **Rather than
  keep guessing at a root cause I can't reproduce, made preview rendering non-fatal**: after
  `MAX_RENDER_REPAIR_ATTEMPTS` are exhausted, `_render_pages` now logs an error and skips that
  page's screenshot instead of raising -- a defensible tradeoff since nothing downstream
  (Architecture/Coder Agent) reads `page_screenshots`; it exists purely for human preview. If this
  recurs, the next thing to try is switching `preview_renderer.py` from `sync_api` to
  `async_api` end-to-end (removing the `asyncio.to_thread` wrapper entirely) — not done yet since
  it's a bigger refactor than tonight's fix budget allowed and the non-fatal skip already unblocks
  the pipeline.
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
- **Approving a UI/UX run's `ui_metadata` artifact does NOT approve its individual component
  artifacts.** `approval_service.py`'s UI/UX hook only checks for `ArtifactType.UI_METADATA` to
  trigger `apply_design_system_patch` -- there is no cascade to the sibling `UI_COMPONENT_CODE`
  artifacts from the same run. `CoderAgent`'s `read_ui_component` tool only ever finds components
  with `approval_status == APPROVED` (`_find_approved_component_artifact`), so if only the
  metadata was approved, the Coder Agent will find nothing to reuse and will build its own
  from-scratch version instead -- silently, with no error, since "no approved component found" is
  a valid, expected outcome for a genuinely backend-only feature. Confirmed directly: this exact
  gap caused a real Coder Agent run for Task Comments to fabricate its own `CommentInput`/
  `CommentList` instead of reusing the approved ones (see item 20). **Every `UI_COMPONENT_CODE`
  artifact a feature's coding step is expected to reuse must be approved individually**, not just
  the metadata JSON.
- **`GraphRecursionError` (from `langgraph.errors`) is a real, reachable failure mode for the
  Coder Agent's coding loop on a realistically-sized plan** (confirmed: an 8-file plan with 2
  "modify an existing file" tasks exhausted a 65-step budget). It is now caught in
  `CoderAgent._code_with_retries` and treated as a recoverable failed attempt (see item 20) --
  but if a similar uncaught `GraphRecursionError` ever surfaces elsewhere (e.g. if the UI/UX Agent
  grows an agentic loop of its own someday), the same pattern applies: catch it at the attempt
  boundary, commit partial progress, retry with an efficiency-focused message, don't let it
  crash the whole request.
- **Every generated app's `HomePage` had no navigation at all until item 21's fix** -- any
  `<Route>` a feature plans is real and correctly wired, but was never reachable by a human
  clicking through the running app (confirmed as the root cause of "every feature just shows the
  placeholder text no matter what was built"). Fixed via a `FEATURE_LINKS_START`/`_END` marker in
  `HomePage` + `nav_checker.check_page_reachability` as a new hard `verify()` gate. If a project
  was scaffolded before this fix, `ensure_project_repo` self-heals it on next call (same backfill
  mechanism as every other scaffold upgrade) -- but any **already-existing** route from before the
  fix still needs a human (or a `CoderAgent.revise()` request) to actually add its `<Link>`; the
  backfill only adds the mechanism, it does not retroactively link routes it didn't create.
- **Playwright's sync API cannot run on a thread that already has an asyncio event loop
  running** -- `render_checker.py`'s runtime-render check learned this the hard way: it's only
  ever really invoked through `CoderAgent.run()`/`revise()` (both `async def`, bridged from a sync
  graph node via `asyncio.run(...)`, deviation #13), so an event loop is *always* active on the
  calling thread in production, even though it's invisible in any test that calls `verify()`/
  `check_runtime_render` from a plain synchronous script. Fixed by running the actual
  Playwright-touching work inside its own `concurrent.futures.ThreadPoolExecutor` worker thread,
  internal to `check_runtime_render` -- **any future check that uses Playwright's (or another
  library's) sync API and might be called from inside `CoderAgent`'s or `UIUXAgent`'s async call
  chain needs the same treatment**, regardless of whether it happens to work in an ad hoc sync
  test script.
- **A revision's own plan is naturally a delta, but `plan_validator` checks full architecture-plan
  coverage** -- confirmed directly: a real `CoderAgent.revise()` request ("add a loading spinner")
  produced a plan that only touched the one file that needed to change, and was rejected for
  "missing" endpoints that the *prior*, still-in-place plan already implements. `revise()` now
  passes `_plan_with_retries` an optional `coverage_baseline_files` so coverage is checked against
  the **union** of prior + delta, while only the delta is actually coded -- **any future caller of
  `_plan_with_retries` for an intentionally-partial/incremental plan must do the same**, or it
  will hit this exact false rejection.
- **"The latest saved CODE_PLAN" is NOT "everything this feature has ever implemented," once even
  one revision has happened** -- the coverage-baseline fix above initially built
  `coverage_baseline_files` from only the single latest CODE_PLAN artifact, which broke on a real
  SECOND revision: the first revision's own saved plan was itself just a delta (by design), so
  using only *that* as the baseline for the next revision silently dropped everything the
  *original* plan covered, reproducing the identical false rejection -- this time surfaced
  directly to a real user through the live `/coder/revise` endpoint. Fixed with
  `CoderAgent._collect_cumulative_plan_files`, which unions file entries across **every** CODE_PLAN
  version ever saved for the feature (later versions winning per path), not just the latest one.
  **Any logic anywhere in this codebase that needs "the full picture of what a feature has
  implemented so far" must walk every artifact version, not assume the latest one is
  self-contained** -- that assumption is only ever true before the first revision.
- **A model reliably finds files that match a pattern, but unreliably finds files that DON'T** --
  confirmed directly: the agentic revision planner (item 22) correctly discovered Tailwind was
  already configured project-wide via its own tools, but still converged on the wrong fix, because
  manually cross-referencing "every page/component file" against "which ones showed up in a
  className search" to deduce the files that DIDN'T is a much harder inverse-search reasoning task
  than a direct grep. **Any future case that needs "which files are missing X" (not "which files
  have X") should get a cheap, deterministic tool/check that answers it directly** (like
  `style_checker.py`'s `check_component_styling`), rather than trusting an agentic loop to reliably
  reason its way to the same answer via generic list_dir/read_file/search_code exploration alone.
- **A real, transient Ollama/langchain-ollama streaming error was hit once during this session's
  testing**: `ollama._types.ResponseError: XML syntax error on line 4: unexpected EOF` , raised
  from deep inside `langchain_ollama`'s chat-streaming response aggregation, uncaught, crashing the
  whole `revise()` call. Did not reproduce on an immediate retry of the identical request --
  treated as a one-off transport/server hiccup (this environment's Ollama server has other
  documented flakiness, e.g. Docker-contention false negatives), not a logic bug, and NOT specially
  caught in code for that reason -- if this recurs reliably (not just once), it would be worth
  broadening `_plan_with_retries`'s exploration-path exception handling beyond just
  `CodePlanGenerationError` to catch this too.
- **The agentic exploration planner has no checkpointer, so a completed run's actual tool-call
  trace is not inspectable afterward** -- confirmed as a real diagnostic limitation: a live run
  submitted an empty `files` list after extensive real exploration, and there was no way after the
  fact to see what the model actually looked at or why it concluded there was nothing to plan.
  **If this specific failure mode (a plan that parses but has empty/wrong content, despite
  seemingly-successful exploration) recurs**, the way to actually root-cause it is to add a
  checkpointer to the `create_agent(...)` in `CodePlanner.generate_via_exploration` (or log each
  tool call/result as it happens) so the conversation is inspectable -- guessing from httpx
  timestamps alone (as this session had to) only reveals *when* things happened, not *what* the
  model was actually reasoning about.
- **A feature's real API shape can legitimately evolve past its Architecture Plan's frozen
  snapshot, and once that happens, no revision can ever satisfy the old literal requirement again**
  -- confirmed directly: `/api/task-comments` (the Architecture Plan's original literal endpoint
  string) was legitimately restructured to `/api/tasks/:taskId/comments` + `/api/comments/:commentId`
  during earlier work, permanently blocking every subsequent `revise()` call's coverage check. Fixed
  by skipping endpoint-literal-string coverage specifically for `revise()` (see item 23) -- **if a
  similar "the original requirement no longer matches the evolved reality" problem is ever found for
  entity names or requirement IDs**, the same reasoning (and the same `enforce_...` flag pattern)
  would apply there too, though neither has shown this problem yet.

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
- **A second real project now exists**: `proj_53284a63` ("TaskFlow", SaaS/MERN), feature
  `feature_5521adbd` ("Task Comments") -- created specifically to real-world-verify item 19's
  Architecture Agent fix against a genuinely new project (not e-commerce-platform). Has approved
  SRS v2 (`artifact_7082b7d7`), approved Architecture Plan v1 (`artifact_2190f60f`, the
  deterministic-fallback shape described in item 19), approved UI/UX v1
  (`artifact_b3950e89` + `CommentInput.jsx`/`CommentList.jsx` components). The LangGraph
  checkpoint for `feature_5521adbd` is currently parked at `next: ['coder_node']` after a real
  `CodePlanValidationError` (the pre-existing planner limitation, not a new issue) -- a future
  `resume()` call would retry the real planner cleanly, or a hand-validated plan (matching the
  established Login/Signup precedent in `scripts/run_coder_pipeline_manual.py`) could be used to
  exercise the rest of the Coder Agent pipeline for this feature if desired. **No
  `workspaces/taskflow/` directory exists yet** -- `CoderAgent.run()` calls
  `workspace_service.start_feature_branch(...)` only *after* `_plan_with_retries` succeeds, and
  planning failed before that point, so the project's git repo/scaffold has never been created
  for TaskFlow. **(Superseded by item 20/21 below: `workspaces/taskflow/repo` was subsequently
  created via the hand-validated manual pipeline and now has real commits on `feature/task-comments`.)**
- **Item 21's real, live-project verification, on top of everything item 20 already left in
  place**: `workspaces/e-commerce-platform/repo` (currently on `feature/signup`) and
  `workspaces/taskflow/repo` (currently on `feature/task-comments`) both gained a new real commit
  ("Backfill scaffold upgrades: ... home page navigation") from calling `ensure_project_repo`
  again -- the `FEATURE_LINKS` marker is now present in both repos' `App.jsx`, on top of whatever
  each branch had already added. Neither branch's pre-existing route (`/login`/`/signup` for
  e-commerce, `/tasks/:taskId` for taskflow) got a `<Link>` retroactively added by this (the
  backfill only adds the *mechanism*, not a link for a route it didn't create) -- `verify()`'s new
  `page reachability` gate correctly and honestly still fails for both, which is expected, not a
  regression.
  - `feature/task-comments` also gained two more real commits from a genuine
    `CoderAgent.revise()` run (revision comment: "add a loading spinner while comments are being
    fetched"): `3899554` (attempt 1) and `2b50de7` (attempt 2, the one that stuck -- diff is a
    single line added inside `CommentList.jsx`'s existing loading state). A corrected, accurate
    **v4** artifact set (`artifact_8169b564` and siblings) was saved reflecting the real verify
    result (`page reachability: failed` -- the known, pre-existing, out-of-scope-for-this-revision
    gap; every other step, including the now-fixed `home page render`, passes) -- v1-v3 (from
    earlier sessions/attempts) remain intact and superseded, matching this project's existing
    "never overwrite, always version" artifact convention.
- **Item 22's real verification against `feature/task-comments`**: between this and the prior
  session, the user independently exercised the (then-still-buggy) `/coder/revise` endpoint
  directly through Swagger several times, which is how `client/src/pages/TaskflowHomePage.jsx` and
  `client/src/components/TaskComments.jsx` came to exist on this branch (real, legitimate user
  work, not debris -- left untouched). On top of that real state, this session's `revise()` calls
  (real "add a loading spinner"/"add a delete confirmation dialog"/two "styles are missing, add
  tailwind css" attempts) added further real commits, ending at `a80c559` ("Coder Agent attempt 3:
  feature_5521adbd") -- the final, correct fix: `TaskflowHomePage.jsx`'s raw inline styles replaced
  with Tailwind classes, plus a `client/postcss.config.cjs` the coding loop added on its own
  initiative (attempting, incompletely, to fix the separate pre-existing PostCSS bug documented in
  item 22). The latest artifact set (`artifact_d5833291` and siblings, `verification_passed:
  False` solely due to that separate PostCSS bug) is left in place, pending human review -- not
  merged. **Still not fixed**: `client/postcss.config.js` (the original, broken CommonJS file) is
  still present alongside the new working `.cjs` version; deleting the former would let
  `client build` pass cleanly.
- **Item 23's real, direct fixes on `feature/task-comments`** (applied directly, not through
  `revise()`, given the multi-hour real cost already spent reproducing the exploration-planner
  issues that session): `d48b54e` removed a duplicate `<BrowserRouter>` in `App.jsx` that was
  crashing the entire app to a blank page (React Router throws on nested Routers with no error
  boundary to catch it); `0d7bf78` added the missing `tailwindcss`/`postcss`/`autoprefixer` npm
  packages and deleted the stale `client/postcss.config.js` stub that was shadowing the real
  `postcss.config.cjs` in Vite's config resolution (root cause of "Tailwind never actually
  applies" -- confirmed empirically: built CSS grew from 136 bytes of raw, unprocessed `@tailwind`
  directives to 12.86kB of real utility CSS); `22c03bb` registered the missing
  `<Route path="/tasks/:taskId">` for `TaskDetailPage.jsx` (which already existed, fully built and
  styled, but was never wired into routing -- confirmed via a real Playwright screenshot showing a
  completely blank page before the fix, fully rendered after). Each commit has its own real,
  independently-approvable artifact set (`artifact_dfc0e118`/`artifact_651f0b96`/`artifact_662fd295`
  and siblings respectively), all with `verification_passed: True`.
- **Item 25's real E2E feature**: `proj_53284a63` (TaskFlow) gained another new feature,
  `feature_244e26d1` ("Task Search", a separate feature from item 24's `feature_29fa0ed4` of the
  same name -- both are real, left in place), with an approved SRS and an Architecture Plan
  (`artifact_434cc2dd` v1, `artifact_e406e74b` v2 from the `revise()` exercise) plus real rendered
  use case/sequence/class diagrams for both versions under
  `outputs/taskflow/feature-task-search/03_architecture/`. v1's use case diagram carries the
  cross-category-duplicate bug described above (left in place deliberately, as the real evidence
  for that finding, not cleaned up); v2 is the corrected, validation-clean result. Neither version
  is approved -- v1's human_approval_note honestly flags the duplicate; a future session could
  approve v2 and continue this feature through UI/UX and Coder Agent.
- **Item 26's real E2E verification, on the same `feature_244e26d1`**: four real `revise()`
  calls across the sequence/class dedup-bug fix cycle -- the first two crashed before saving any
  new artifact (sequence duplicate-message bug, then the class anemic-DTO check propagating
  uncaught since `revise()` had no safety net yet); the third (post sequence-fix and
  safety-net-fix, pre operation-dedup-fix) produced Architecture Plan v3 (JSON+Markdown) and
  `task_search_sequence_v3.puml`/`.png` + `task_search_class_v3.puml`/`.png`, completing via the
  new caveat safety net but still visually showing the class duplicate-operation bug; the fourth
  (all fixes in place) produced Architecture Plan v4 and `task_search_sequence_v4.puml`/`.png` +
  `task_search_class_v4.puml`/`.png`, clean of both duplicate bugs -- all left in place as real,
  inspectable verification output. None of these versions are approved; v4's
  `human_approval_note` honestly flags the upstream anemic-DTO data-quality issue described above
  (real, but out of this milestone's scope to fix at the source).
- **Item 27's real E2E verification, on the same `feature_244e26d1`**: a direct
  `_complete_diagram_models(attempt_agentic=True)` call (not saved as artifacts -- used to isolate
  and verify the new agentic loops specifically) confirmed the sequence agentic loop hits its
  20-turn limit on this real feature/model combination but the new focused single-shot fallback
  produces genuinely dynamic content; a second, real `revise()` call (`attempt_agentic=False`)
  produced Architecture Plan v5 and `task_search_sequence_v5.puml`/`.png` +
  `task_search_class_v5.puml`/`.png`, saved as real, inspectable output -- this run also exercised
  item 26's reactive class-repair loop for real (a genuine anemic-attribute validation failure
  that self-corrected on retry). Not approved; left in place with the honest stereotype-mismatch
  quirk noted above still visible for a future session to judge.

- **Item 28: Domain Agent built as a real RAG system** (previously a stub, `raise
  NotImplementedError`), per the plan at the top of this session
  (`C:\Users\ASUS\.claude\plans\soft-petting-star.md` at time of writing). New
  `app/services/rag/` package (`loaders.py`/`chunking.py`/`embedding.py`/`vector_store.py`) +
  `app/services/domain_knowledge_service.py` do real deterministic retrieval (embed query with a
  local `sentence-transformers/all-MiniLM-L6-v2` model, loaded lazily; similarity-search a
  persistent local ChromaDB collection at `vector_db/chroma`) — never an LLM tool-calling loop,
  per this repo's own build-spec constraint that Domain/Requirement/Architecture stay on the
  one-shot `BaseLLMProvider` path. Seed e-commerce knowledge base authored at
  `knowledge_base/ecommerce/` (5 `.txt` files: checkout/cart, payment/PCI, catalog/inventory,
  order lifecycle, account/auth) and really ingested via `scripts/ingest_domain_knowledge.py`
  (5 files, 21 chunks) — `scripts/verify_domain_rag_e2e.py` confirms real retrieval returns the
  correct on-topic source document for 4/4 representative e-commerce queries plus the empty-query
  edge case. `AgentName.DOMAIN`/`ArtifactType.ENHANCED_SRS` were already pre-wired; added
  `ArtifactType.DOMAIN_IMPROVEMENTS` for the new human-readable "what changed and why" summary
  artifact. `domain_validator.py`'s honesty check (no additions/modifications may be claimed when
  retrieval returned zero chunks) is the enforcement mechanism that makes "Domain Agent is a real
  RAG system" a checked fact rather than a claim. `graph_orchestrator_service.py`: `domain` moved
  from `AUTO_APPROVED_STAGES` into `GATED_STAGES` with a real `_domain_node` (mirrors `_uiux_node`)
  — this is exactly the flip the M6-era docstring said to make "the moment Domain Agent produces
  real output." `tests/test_graph_orchestrator.py` updated accordingly: the fast, throwaway-feature
  mechanics tests now anchor entirely at the `requirement` gate (same reasoning that already
  excluded `uiux`/`coder` — `domain` now needs a real approved SRS artifact + a real LLM call, so
  it can no longer be cheaply traversed by a mechanics-only test). New agent files:
  `app/agents/domain_agent/{agent.py,domain_validator.py,markdown_builder.py}` (schemas.py/
  prompt.py extended in place), `app/schemas/domain_schema.py`; real `/domain/run` and new
  `/domain/revise` endpoints replace the old placeholder in `app/api/routes/agents.py`. 29 new
  unit tests (chunking/validator/markdown-builder/fallback/retrieval-query), all pure Python, all
  passing, plus the full existing suite re-run clean (only pre-existing, unrelated Docker-daemon-
  dependent failures in `test_coder_tools.py`/`test_coder_verify.py`/`test_render_checker.py`,
  environmental, not caused by this change). **Real e2e verification against the real, approved
  `Login` feature (`feature_a44033b8`, `E-commerce Platform` project, approved SRS v3)**: real
  retrieval genuinely found 3 relevant e-commerce knowledge sources for this feature
  (`checkout_and_cart_conventions.txt`, `payment_and_pci_basics.txt`,
  `user_account_and_authentication.txt` — a sensible match for a Login feature). All four real
  LLM generation attempts (see the model-quality gotcha above) hit the fallback path, producing
  `login_enhanced_srs_v1.json`/`.md` and `login_domain_improvements_v1.json` through
  `login_enhanced_srs_v4.json`/`.md` and `login_domain_improvements_v4.json` under
  `outputs/e-commerce-platform/feature-login/02_domain/` — each fallback artifact set is real,
  honest, validator-clean output (unchanged SRS content, `fallback_used: true`, a correct,
  specific `fallback_reason`), left in place as genuine evidence the reliability ladder holds up
  under real repeated LLM failure, not synthetic test debris. None of these are approved yet —
  a future session with a more capable model (larger local model or a hosted provider) could
  re-run `domain_agent.run('feature_a44033b8', ...)` to get a genuinely enriched (non-fallback)
  version for human approval.
- **Item 29: Domain Agent redesigned to actually enrich (not just fall back safely), plus a real,
  full pipeline run through Coder Agent on a brand-new project.** The user reported item 28's
  Domain Agent still wasn't enriching anything and asked for a real fix plus a fresh end-to-end
  pipeline test. Root cause: asking the LLM to retype the entire SRS verbatim in one JSON blob
  was itself the defect (see the RESOLVED gotchas above), not a model ceiling as item 28
  concluded. Redesigned the LLM contract to a small enrichment PLAN (additions/modifications
  only, no SRS retyping, no ID invention -- `DomainAgent._apply_enrichment_plan` merges it into a
  full SRS copy deterministically); `domain_validator.py` rewritten to `validate_plan()`,
  checking the small plan pre-merge instead of the merged output post-merge.
  `tests/test_domain_validator.py` and `test_domain_agent_fallback.py` fully rewritten for the
  new shape (34 domain tests total, all passing). **Real result: `qwen3-coder:latest` succeeded
  on the first attempt, 3/3 real runs, zero fallbacks** -- both re-run against the existing
  `Login` feature (`login_enhanced_srs_v5/v6/v7.json`, correctly adding an account-lockout
  requirement and enriching the forgot-password acceptance criterion, both genuinely cited from
  `user_account_and_authentication.txt`) and against a brand-new feature created this session (see
  below). Also fixed in passing: `RequirementAgent.run()` was saving its Markdown/JSON pair at
  MISMATCHED versions (`SRS_v1.md` next to `SRS_v2.json` -- confirmed present since this
  project's very first-ever SRS) because neither `save_text_artifact` nor `save_json_artifact`
  was passed `version_override`, unlike `_save_revised_srs_artifacts` which already did this
  correctly; now computes one shared version up front for both, matching that established
  pattern. **A new real project/feature exists**: `proj_983f2941` ("QuickCart", E-commerce/MERN),
  `feature_89878ec1` ("Item Management" -- add/edit/update/delete catalog items), created and
  driven entirely through the real HTTP API (`fastapi.testclient.TestClient`, not shortcuts) to
  verify the whole pipeline end-to-end for real: approved SRS v1 → real Domain Agent enrichment
  (SKU uniqueness, currency-code, price-history, and prevent-deleting-items-in-active-orders
  additions, all correctly cited from `product_catalog_and_inventory.txt`/
  `checkout_and_cart_conventions.txt`) → approved Enhanced SRS → real Architecture Agent (~4.5 min
  after the model swap below) → approved Architecture Plan → real UI/UX Agent (see the fixes
  below) → approved UI metadata → real Coder Agent, which hit its long-documented planner
  limitation (`CodePlanValidationError` after 2/2 attempts, missing backend files/routes for the
  CRUD endpoints -- the exact same pre-existing gap documented earlier in this file, not a new
  issue) and parked the graph at `next: ['coder_node']`, exactly matching the established M6-era
  precedent. **Along the way, diagnosed that "Architecture Agent takes over an hour" was a
  GPU/VRAM mismatch** (`qwen3-coder:latest` doesn't fit this machine's 6GB RTX 4050), user chose
  to switch both `DEFAULT_LLM_MODEL` and `AGENTIC_MODEL_OVERRIDE` to `llama3:latest` (`.env` and
  the live `store.llm_settings`) -- see the RESOLVED gotcha above for the full diagnosis. **UI/UX
  Agent needed three additional real fixes** to get through a fresh feature with the smaller
  `llama3:latest` model: a validation repair ladder where none existed before, a validator fix so
  a repair attempt sees every real error at once instead of one category at a time, and a
  component render-repair ladder plus a preventive prompt rule for a real
  `ReferenceError: Item is not defined` bug (the model factored out an undefined `<Item />`
  sub-component) -- see the gotchas above for the full detail on each. One page's preview
  screenshot (`item-management-page`) was ultimately skipped (logged as an error, not fatal) after
  a render failure that would not reproduce in any direct isolation test -- see the "still
  unexplained" gotcha above; every other artifact (ui_metadata, 3 components, integration
  manifest, markdown) saved and approved normally. Full test suite re-run clean at the end (301
  passed, only the same pre-existing Docker-daemon-dependent failures, unrelated to any of this).
30. **Built the AutoForge operator-dashboard frontend end-to-end (new top-level `frontend/`,
    React + Vite + Tailwind v4 + React Query + react-router-dom), covering the full
    Requirement → Domain → Architecture → UI/UX → Coder pipeline with Security/QA/Deployment as
    visible placeholders, per user request.** Full spec: the plan this session followed (now
    overwritten per this file's own convention, see `C:\Users\ASUS\.claude\plans\soft-petting-star.md`).
    Two small, additive backend routes were prerequisites: `GET /artifacts/{artifact_id}/content`
    (`app/api/routes/artifacts.py` — unified text/JSON/PNG content-serving, since `GET
    /artifacts/{id}` only ever returned file-path metadata) and `GET
    /features/{feature_id}/graph-status` (`app/api/routes/features.py` — thin wrapper exposing
    `graph_orchestrator_service.get_status()`, previously only ever returned inline from `POST
    /start`). Also fixed two **pre-existing, unrelated** `list_*` 500-crash bugs hit along the way
    (same "one malformed record breaks the whole list" pattern in both): `list_projects()`
    (13 confirmed test-debris Mongo documents, deleted with explicit user consent) and
    `list_feature_artifacts()`/`list_project_features()` (55+ real, historical `qa_agent`
    `"test_cases"` artifacts predating QA Agent's simplification to a stub — genuine data, not
    debris, so fixed with the same defensive per-record try/except-and-log pattern instead of
    deleting).
    - **Milestones M1–M2** (scaffold, Project/Feature CRUD, Requirement Agent run/review,
      artifact viewers) matched the plan's design directly with no real bugs found.
    - **M3 (Domain + Architecture + polling) surfaced one real, confirmed frontend bug**, found
      only by actually driving a fresh feature through the browser rather than reading the code:
      `FeatureDetailPage.jsx`'s `pipelineStarted` was computed as
      `Boolean(graphStatus?.next?.length) || allArtifacts.length > 0` — since Requirement/
      Architecture generate real artifacts via their manual `/run` endpoints *without* the graph
      ever being started (the documented hybrid trigger model), the "Start Pipeline" button
      vanished permanently the moment a human ran Requirement, before the graph had ever actually
      started, leaving no way to make Domain auto-trigger after approval. Fixed by deriving
      `pipelineStarted` from `Object.keys(graphStatus.values || {}).length > 0` instead — a
      graph run that's ever been started leaves its input/output keys in `state.values`
      permanently, even after `next` empties out on completion, confirmed directly against a real
      completed feature (Signup) whose graph-status still carries a populated `values` with an
      empty `next`.
    - **M4 (UI/UX stage) surfaced a more fundamental gap**, found by loading the real, live
      QuickCart "Item Management" feature (approved `ui_metadata` but 3 still-pending
      `ui_component_code` artifacts — the exact scenario the plan's own destructive-warning copy
      was written for): `ArtifactRow.jsx` had no approve/reject action at all (only View/Revise),
      and `ApprovalPanel` only ever targets the stage's single gating artifact — meaning
      individual UI/UX components had **no approval path anywhere**, and once `ui_metadata` itself
      was approved, `currentStage` moved past `uiux` entirely, making the components permanently
      unreachable through the main flow. Fixed two ways: (1) `ArtifactRow.jsx` gained inline
      Approve/Request Revision/Reject buttons (reusing `useApprovalMutation` directly) shown
      whenever a `featureId` prop is passed and the artifact is `pending` — `ArtifactList.jsx`
      only passes `featureId` for non-gating rows, since the gating artifact already has the
      bigger `ApprovalPanel` below it; (2) `FeatureDetailPage.jsx` gained a persistent "UI/UX
      components awaiting review" section, always visible regardless of `currentStage`, showing
      any `ui_component_code` artifact still `pending` — verified live: approving one component
      via the new inline button correctly dropped the count from 3 to 2 and the artifact's
      `approval_status` genuinely flipped in the backend. Diagram PNGs (`use_case_diagram`/etc.)
      have this same class of reachability gap once their stage is approved, but — unlike
      components — were never meant to be individually approved (no gate depends on them), so this
      was left as a known, lower-severity, not-fixed limitation rather than scope-creeping into a
      full "browse every artifact regardless of stage" feature nobody asked for.
    - **M5 (Coder Agent stage) surfaced two more real bugs**, found by loading the real, live
      TaskFlow "Task Comments" feature (18 real Coder Agent versions, genuinely still pending —
      this project's actual, already-most-exercised real Coder Agent history):
      1. `currentStage` was computed as `GATED_STAGES.find(stage => stageStatuses[stage] !==
         APPROVED)` — a purely sequential scan. This feature predates Domain Agent becoming a real
         gated stage (item 28), so it has no `enhanced_srs` artifact and never will, even though
         the graph's real position (`graph-status`: `next: ["coder_node"]`) shows Coder is
         genuinely what's pending. The sequential scan got stuck reporting "Domain: not started"
         forever, making the real, pending `code_diff` permanently unreachable. Fixed by
         prioritizing the graph's own ground truth first: `next` names either `"{stage}_node"`
         (actively auto-running) or `"approve_{stage}"` (paused at a human gate) — either way,
         that's definitively the current stage — falling back to the sequential heuristic only
         when `next` gives no signal at all (never started, or fully finished).
      2. `pickViewer()` routed `artifact_type === "code_diff"` straight to `DiffViewer`
         regardless of format — but `code_diff` exists in BOTH formats: markdown is the real merge
         report `DiffViewer` parses (prose + a fenced diff block), while the JSON one is just a
         `{added, modified, deleted}` file-tree summary with no diff text at all. Viewing the JSON
         variant showed its raw JSON as if it were prose, with a permanent "No diff content found"
         underneath. Fixed by making `pickViewer` only special-case `code_diff` when
         `artifact_format === "markdown"`, letting the JSON variant fall through to the normal
         `JsonViewer` path. Verified both live: the JSON variant now renders as a clean collapsible
         tree; the markdown variant correctly shows the merge report prose (verification steps,
         PASSED status, informational placeholder-stub/feature-page-render findings) followed by
         a real diff2html-rendered diff with truncation notice and file stats.
    - **M6 (LLM Settings page)** built the real GET/PUT/test UI (previously a bare placeholder),
      and in doing so **surfaced and fixed a real, live misconfiguration**: the Mongo-backed
      `store.llm_settings.model` (which one-shot agents actually read, distinct from `.env`'s
      `DEFAULT_LLM_MODEL`) was still `qwen3-coder:latest` — leftover from an earlier, since-paused
      testing thread in this same session — silently making every one-shot agent call (this
      session's own M3 verification included) take 5+ minutes instead of under a minute, since
      that model doesn't fit this machine's 6GB VRAM. Used the newly-built page itself to correct
      it back to `llama3:latest`, verified via a real end-to-end test-prompt call (clean response
      in well under a minute) and via `GET /settings/llm` showing the persisted change.
      `AGENTIC_MODEL_OVERRIDE` (Coder Agent's separate tool-calling model) was untouched, per the
      deliberate, already-documented split.
    - **Real, live verification throughout, not synthetic**: every milestone was driven through
      an actual running backend (`uvicorn`, port 8001) and frontend (`vite dev`, port 5174) via
      Playwright (invoked directly through the backend venv's own Playwright install, since no
      Playwright MCP tool was available this session) — screenshots and `page.inner_text`/
      `pageerror`/console-error capture at each step, never just code review. A throwaway
      "Frontend Verify Test" project/feature created for the M3 hybrid-trigger-model check was
      fully cleaned up afterward (Mongo documents deleted directly via `store.<collection>.
      collection.delete_one(...)`, since no DELETE route exists for projects/features; matching
      output directory removed from disk) — confirmed gone from `GET /projects` afterward.
    - `npm run build` (production Vite build) re-run clean after every fix in this item, zero
      errors — only a pre-existing, unrelated bundle-size advisory (single chunk >500kB,
      no code-splitting configured yet).

31. **AutoForge Frontend v2: redesigned from a linear approve-and-advance wizard into an
    interactive multi-agent dashboard**, per direct user feedback with reference screenshots of a
    comparable system (fixed left pipeline nav, center interaction pane, right "Governance"
    panel). Full plan: `C:\Users\ASUS\.claude\plans\soft-petting-star.md` (overwritten since, per
    this file's convention). Six backend additions, all additive/non-breaking:
    - **Per-agent LLM overrides**: `store.llm_settings` gained a nested `agent_overrides:
      {agent_name: {...}}` map (schema: `AgentLLMOverrideUpdateRequest`/`AgentLLMSettingsResponse`
      in `llm_schema.py`). `llm_provider_service.get_provider(agent_name=...)` and
      `agentic_model_factory.get_agentic_chat_model(agent_name=...)` both check this before
      falling back to the global default (the latter falls back to `.env`'s
      `AGENTIC_MODEL_OVERRIDE` **only** for `agent_name == "coder_agent"` specifically -- a real
      bug caught and fixed during this work: that env var was leaking into Architecture Agent's
      own agentic exploration calls whenever Architecture had no override configured, silently
      forcing it onto Coder Agent's model instead of the global default). New routes: `GET/PUT/
      DELETE /settings/llm/agents/{agent_name}`, `POST /settings/llm/agents/{agent_name}/test`.
      Every one-shot agent's `get_provider()` call site updated to pass its own `agent_name`.
    - **A real, serious performance bug found and fixed in the process**: `MongoLLMSettingsProxy`
      re-fetches the **entire** settings document from MongoDB on every single `["field"]` access
      (no per-instance caching at all) -- pre-existing before this session, but the new per-agent
      code multiplied it across 5 agents x ~6 fields, observed taking **5+ seconds** for what
      should be one cheap read (confirmed directly: a real save via the new LLM Settings UI got
      stuck on "Saving..." for 5+ seconds; curl timing confirmed `PUT .../agents/{name}` alone
      took 5.37s). Fixed by adding `MongoLLMSettingsProxy.get_document()` -- one `find_one` call,
      reused as a plain dict everywhere in `llm_provider_service.py`'s new methods and in
      `agentic_model_factory.py` (which had the identical anti-pattern) -- verified down to
      ~0.15-0.22s per call after the fix (curl-timed, ~25-40x faster). **Any future code touching
      `store.llm_settings` for more than one field should use `get_document()` once, never
      `store.llm_settings["x"]` repeatedly in the same call** -- the existing single-field proxy
      interface is fine for genuinely single-field reads/writes (e.g. the pre-existing
      `update_settings()` still writes field-by-field and works fine for its actual usage), but
      silently re-fetching per field is a real trap for anything reading several fields at once.
    - **Conversation-history data**: new `stage_events` Mongo collection (`stage_event_schema.py`,
      `stage_event_service.py`) records every human-initiated `run()`/`revise()` request's
      `human_comment`/`revision_comment` at the API route layer (`agents.py`, right after
      `_validate_feature`, before the try block -- so it's captured even if the agent call itself
      later fails). `ApprovalResponse` gained an optional `feature_id`, and
      `approval_service.list_feature_approvals(feature_id)` joins via **each approval's own
      artifact's feature_id** (not the approval's own new field) specifically so it works for
      approvals made before this field existed too -- confirmed necessary live: every
      historical approval's own `feature_id` was `null`, and the join-based lookup was what made
      them show up at all. New routes: `GET /features/{feature_id}/approvals`, `GET
      /features/{feature_id}/events`.
    - **Downloads**: `GET /artifacts/{id}/download` (raw bytes + `Content-Disposition: attachment`,
      sibling of the existing JSON-wrapped `/content`). `workspace_service.export_zip(project_id,
      ref)` reads a git ref's **committed tree directly** (`repo.commit(ref).tree.traverse()`),
      never checking the ref out first -- safe to call regardless of what's currently checked out
      on disk. `GET /features/{id}/code/download` zips the feature's own branch if it still
      exists (pre-merge, so a reviewer can try the code locally before deciding), else falls back
      to `main`; `GET /projects/{id}/code/download` always zips `main`. Verified for real:
      downloaded zips for both the merged Login feature (22 real files, confirmed no `.git`
      internals) and the still-unmerged Task Comments branch (32 real files) via actual button
      clicks in a real browser, not just curl.
    - **Artifact `size_bytes`** (cosmetic, shown in the new Governance panel): computed from the
      file on disk at every read (`artifact_service._hydrate_artifact_response`), never stored --
      `None` on a missing file rather than raising.
    - Frontend: `FeatureDetailPage.jsx` rebuilt as a three-panel layout (`PipelineNav.jsx` --
      every stage independently clickable regardless of approval status, the direct general fix
      for the prior design's "artifacts become unreachable once a stage is approved" gap;
      `GovernancePanel.jsx` -- Stage Actions/Trace Links/Stage Artifacts; center Interaction/
      Output/Artifacts tabs). `StageInteractionPanel.jsx` merges stage_events + approvals +
      artifact-versions into one real chronological chat-style timeline (not a live
      back-and-forth -- a real activity log presented conversationally), with static per-stage
      suggestion chips (`lib/suggestionChips.js`). New `components/documents/` (`DocumentValue.jsx`
      -- a generic JSON-to-readable-sections/tables renderer; `SrsDocumentViewer.jsx`/
      `ArchitecturePlanDocumentViewer.jsx` -- real formatted-document views for SRS/Enhanced
      SRS/Architecture Plan JSON, wired into `pickViewer`) replace raw JSON dumps for those three
      artifact types specifically, verified against real generated QuickCart data (proper headers,
      tables for functional/non-functional requirements/user stories/traceability, nested
      design_views/implementation_plan sections). `ArtifactContentView.jsx` factored out of
      `ArtifactViewerModal.jsx` so the same viewer-dispatch logic renders both inside the popup
      and inline in the Output tab. Retired `StageActionPanel.jsx`/`PipelineStageTracker.jsx`
      (superseded, deleted as dead code) and the previous session's special-cased "pending UI/UX
      components" banner (superseded by the general per-stage Artifacts tab reachability fix).
    - **Real, live verification throughout** (same methodology as the prior frontend session --
      actual running backend + frontend, Playwright via the backend venv, no synthetic fixtures):
      every milestone screenshotted against real data (Task Comments' 18 real Coder Agent
      versions, QuickCart's real SRS/Architecture Plan, Login's real merge history). Full backend
      suite re-run clean after every milestone (263 passed throughout, same pre-existing
      Docker-dependent exclusions as always). Final 9-page smoke test (project list, 3 project
      detail pages, 5 features at different real pipeline stages, LLM Settings) -- zero page
      errors, zero console errors.

32. **Requirement Agent turned conversational: gap-filling BA instead of a single-shot form-filler.**
    Previously `RequirementAgent.run()` required a fully-formed `RequirementBAInput` in one
    request, silently defaulted anything missing (`_complete_ba_input`), and the human never saw
    the SRS take shape or got asked a clarifying question. Full plan:
    `C:\Users\ASUS\.claude\plans\soft-petting-star.md` (overwritten since, per this file's
    convention). Design considered representing each conversational turn as a versioned
    `SRS_DRAFT` artifact (reusing `artifact_service`'s versioning) -- rejected via an independent
    Plan-agent design review: `get_next_version()` has no locking (a real two-tab race once
    called every turn), it repurposes "version" to mean "turn number" for files no one reviews
    individually, and it would need the frontend's generic artifact list to explicitly hide a new
    pseudo-type. Chosen instead: one new Mongo collection, `requirement_conversations`, one
    document per `feature_id`, upserted in place each turn (same idiom as the pre-existing
    single-document `store.llm_settings`) -- the only shared-service touch this milestone makes.
    - New `app/agents/requirement_agent/conversation_engine.py`: `project_ba_input_to_srs_shape`
      (the core "turn known_answers into full SRS shape" logic, extracted from the existing
      `_build_fallback_srs_json` -- which becomes a thin wrapper appending its own
      failure-reason line, unchanged behavior; the extraction also fixed a real, previously-silent
      gap: `output_requirements`/`validation_rules` being defaulted with **zero** assumption flag,
      and a hardcoded single-FR traceability row that was only ever correct by coincidence when
      exactly one FR existed -- now one row per FR); `run_gap_analysis` (one small LLM call per
      turn -- extract answers, ask at most 3 prioritized questions, same JSON-parse/repair ladder
      as the rest of this agent, falling back to a deterministic rule-based checklist on total
      failure, never a second LLM call). New `app/agents/requirement_agent/conversation_quality_gate.py`
      (mirrors `domain_validator.py`'s idiom): deterministic, no-LLM checks -- functional
      requirements non-empty/concrete, `api_expectations` entries regex-plausible as
      `METHOD /path`, `data_requirements` entries not vague sentences, and (the hard blocker) any
      Tier-1 field auto-assumed rather than answered. Tier system baked into the prompt and code
      (`TIER_1_FIELDS`/`TIER_2`/`TIER_3`): Tier 1 (`functional_requirements`, `api_expectations`,
      `data_requirements`) always asked about if missing, because these are exactly the fields a
      real, confirmed prior failure (item 29's QuickCart Architecture Plan -- duplicate GET-only
      endpoints and single-field pseudo-entities instead of real CRUD/one entity) traced back to.
    - New `RequirementAgent` methods (`run`/`revise` and every existing helper untouched):
      `start_conversation`/`reply_to_conversation`/`get_conversation`/`reset_conversation`/
      `confirm_conversation`. `confirm_conversation` re-validates `known_answers` through
      `RequirementBAInput` and calls the **unmodified** `_complete_ba_input`/
      `_generate_requirement_output`, saving via a new `_save_generated_srs_artifacts` helper
      factored out of `run()`'s existing inline save block (now shared by both) -- this is what
      makes the result compose with the existing `approval_service`/`graph_orchestrator_service`
      gate with zero changes to either: they only ever see a normal `ArtifactType.SRS` artifact.
      The quality gate is re-checked **server-side** inside `confirm_conversation` itself (400 if
      not ready and `override_quality_gate` isn't explicitly set) -- a direct API call cannot
      bypass it just by skipping what the frontend shows; an override's reason is stamped into the
      real SRS's own `assumptions` array so it stays visible to Domain/Architecture Agent and any
      future human reviewer, not just the frontend session that made the call.
    - New routes (fully additive; `/requirement/run` and `/requirement/revise` untouched --
      confirmed via grep these are the only two callers of `requirement_agent.run()`/`.revise()`
      anywhere): `POST/GET .../requirement/conversation/{start,reply,confirm,reset}` +
      `GET .../requirement/conversation`.
    - Frontend: new `RequirementConversationPanel.jsx` replaces `RequirementRunForm` as the
      default view for the `requirement` stage's `ACTION_REQUIRED` state (the old form stays
      reachable via a "Prefer to fill a form manually instead?" link, unchanged). Chat bubbles
      reuse `StageInteractionPanel.jsx`'s existing `TimelineItem` Tailwind classes for visual
      consistency; the live SRS preview reuses `SrsDocumentViewer` directly (no artifact fetch
      needed -- the conversation response already carries the full preview) behind a
      collapsed-by-default "View current SRS draft" toggle. Fixed `TimelineItem`'s ask-bubble
      label ternary (`eventType === "run" ? "Started" : "Revision requested"`, which silently
      mislabeled any third event type) into a label map covering the new
      `clarify_start`/`clarify`/`confirm` event types.
    - **A real, non-obvious layout bug found only by driving this through the actual browser, not
      by reading the code**: the panel was first built with a side-by-side chat+SRS-preview
      two-column layout, copying the pattern that worked for UI/UX's Page Previews earlier this
      session -- but that pattern lived in the wide center Output panel, while this component
      renders inside the narrow (`w-96`) per-stage **Interaction sidebar**. A real screenshot
      showed the quality-gate reasons list collapsed to one character per line -- the inner
      `w-96` SRS-preview column was by itself as wide as the entire available sidebar, squeezing
      the chat column to near-zero width. Fixed by switching to a single-column layout (chat
      stacked above the reply box and quality-gate banner) with the SRS preview behind a
      collapsed-by-default toggle instead of an always-open side pane. Confirmed fixed with a
      fresh screenshot after the rebuild -- clean, fully-readable layout.
    - **A real, separate bug found only by driving a genuine multi-turn conversation against a
      real local LLM, not by unit tests**: the gap-analysis prompt shows the model an empty-string/
      empty-list JSON shape as an example of the `known_answers` structure (e.g.
      `"architectural_style": ""`) -- the same "model anchors on the shown JSON shape" gotcha this
      project has hit before with other agents. A real run had the model echo
      `"architectural_style": ""` back verbatim despite having no real answer for it, which then
      failed `RequirementBAInput`'s validator at confirm time (an empty string is not `None`, so
      it skips the field's normal `MODULAR` default and hits the allowed-values check instead,
      raising). Worse, on a later turn the same clobbering silently overwrote an already-correct
      `target_stack: "MERN"` down to `""`. Fixed by filtering the model's `known_answers` update to
      only non-falsy values before merging (`{k: v for k, v in new_known_answers.items() if v}`) --
      any accidentally-echoed empty placeholder can no longer overwrite or introduce a bad value.
    - Tests: `tests/test_requirement_conversation.py` (new, 12 -- honest default-flagging with no
      false failure-reason text, `_build_fallback_srs_json`'s existing behavior preserved after
      the extraction, per-FR traceability, every individual quality-gate check, and
      `run_gap_analysis`'s question-truncation/known-answer-merge behavior plus its deterministic
      fallback on total parse failure, mocked LLM matching this suite's established
      `patch(".../conversation_engine.llm_provider_service")` idiom). Full suite: **275 passed**
      (up from 263), zero regressions.
    - **Real end-to-end verification, a genuinely new feature, driven through the real HTTP API
      and then the real browser**: created `feature_df7639a2` ("Inventory Reports") on the live
      QuickCart project with a deliberately rough description ("let admins manage inventory
      somehow") -- the real gap-analysis call correctly asked exactly the Tier-1 questions
      (concrete actions, API endpoints, data fields) with zero prompting toward them; after two
      real replies providing concrete CRUD/endpoint/field detail, the quality gate correctly
      turned ready (`auto_assumed_tier1_count: 0`); confirming produced a real SRS v1 (pending
      approval) -- the underlying single-shot SRS-generation LLM call itself failed schema
      validation on this run (a **pre-existing**, already-documented model-quality gotcha,
      unrelated to this milestone) and correctly fell through to the now-shared
      `project_ba_input_to_srs_shape`-based fallback, proving the extraction preserved the
      existing reliability ladder end-to-end under a real failure, not just in fixtures. Also
      created `feature_f9af7982` ("Order Export") specifically to drive the chat UI itself through
      a real browser (not just the API) -- this is the run that surfaced both real bugs above.
      Both features are left in place as real, inspectable verification output, matching this
      project's established convention (not cleaned up as test debris).

33. **Requirement Agent conversation UX pass: chat as the main window, per-question answering
    with placeholders, and live-streamed SRS generation.** Direct follow-up user feedback on
    item 32: the chat needed to be the primary/main window (not squeezed into the narrow
    Interaction sidebar) until an SRS exists, answering 3 questions at once in one combined box
    was frustrating, questions needed example placeholders, and the final SRS generation should
    be visibly live (streaming) rather than a blocking wait then a sudden reveal, with clear
    loaders throughout.
    - **Main window**: `StageOutputPanel.jsx` now renders `RequirementConversationPanel` directly
      as the main Output content for `stage === "requirement"` whenever no SRS artifact exists yet
      (`versions.length === 0`) -- the instant a real SRS is generated, this stage reverts to the
      normal document-view behavior every other stage already has, automatically (no special-case
      code needed for the transition -- it falls out of the existing `versions.length` check).
      Removed from `StageInteractionPanel.jsx`'s narrow sidebar entirely (replaced with a one-line
      pointer to the main panel).
    - **Per-question answering with placeholders**: `GAP_ANALYSIS_SYSTEM_PROMPT` now asks for
      `questions: [{"question", "placeholder_example"}]` instead of plain strings -- the model
      writes a concrete, feature-specific example answer for each question (confirmed real:
      "POST /api/return_requests, GET /api/return_requests" for an API-endpoints question on a
      genuinely new "Return Requests" feature), shown as that question's input placeholder.
      `conversation_engine.py`'s deterministic fallback checklist got matching canned examples.
      `requirement_conversation_schema.py` gained `QuestionWithPlaceholder` +
      `_coerce_questions` (a `field_validator(mode="before")` that wraps a legacy plain string in
      `{"question": s, "placeholder_example": ""}`) so conversation documents saved before this
      change keep working with no migration. Frontend: `QuestionAnswerForm` renders one labeled
      input per open question (not one shared textarea); submitting combines the
      individually-answered questions into a clearly-attributed `Q: ...\nA: ...` block per
      question -- both easier for a human to answer and a cleaner signal for the next
      gap-analysis turn than one run-on paragraph.
    - **Live-streamed SRS generation**: new `RequirementAgent.confirm_conversation_stream`
      (async generator, mirrors `confirm_conversation`'s validation/quality-gate/save logic
      exactly) calls `provider.stream(...)` (already existed on every `BaseLLMProvider`, just
      never wired to an endpoint before) instead of `invoke_agent`, yielding
      `{"type": "token", "text": ...}` events as raw output arrives; only the JSON-repair retry
      and deterministic fallback (rare reliability-ladder paths) stay non-streamed, since there's
      no meaningful "live" content to show while repairing already-malformed output. New route
      `POST .../requirement/conversation/confirm/stream` returns a `StreamingResponse` of
      newline-delimited JSON (deliberately not SSE/EventSource, which can't POST a body) --
      `frontend/src/api/agents.js`'s `confirmRequirementConversationStream` reads it via a plain
      `fetch()` `ReadableStream` reader, calling `onEvent` per parsed line. `LiveGenerationView`
      shows a pulsing "Connecting to Requirement Agent..." spinner before the first token, then
      the raw JSON growing live in a monospace box with a blinking cursor -- confirmed for real
      with a genuine local LLM: the exact SRS JSON text visibly typing in, not a fixed wait
      followed by a sudden reveal. The existing "Start Conversation"/"Send Answers" loaders were
      also made more prominent (an explicit `LoadingSpinner`, not just disabled-button text).
    - **A real, non-obvious race found only by driving this through a genuine local LLM at real
      latency, not by unit tests**: clicking "Confirm anyway" while a reply's own gap-analysis
      call was still in flight read `known_answers` from the database *before* that reply had
      finished saving, silently confirming against stale/empty answers (the generated SRS's
      FR-001 came back as the raw feature description, `_complete_ba_input`'s own fallback,
      because `functional_requirements` genuinely wasn't in `known_answers` yet at the moment
      confirm read it) -- a real, user-reachable defect, not just a test-timing artifact (a real,
      fast-clicking human could trigger the identical race, since the override "Confirm anyway"
      path was never disabled by a pending reply). Fixed by disabling both the ready-path and
      override-path confirm buttons whenever `respond.isPending`, with an explicit
      "Waiting for your last answer to finish processing..." message -- confirmed fixed with a
      clean re-run showing the real per-question answer ("Customer can create a return request
      for a delivered item") correctly reflected in the generated SRS's FR-001.
    - Tests: `tests/test_requirement_conversation.py` gained 2 new tests (`confirm_conversation_
      stream` yields tokens-then-done and saves a real artifact via a real project/feature/
      requirement_conversations fixture with proper Mongo+disk teardown, matching the established
      `feature_with_prior_run`-style pattern in `test_coder_agent_revise.py`; blocks cleanly with
      a single error event when the quality gate isn't ready, never calling `provider.stream` at
      all) plus updated assertions for the existing gap-analysis tests' now-structured question
      shape. Full suite: **277 passed** (up from 275), zero regressions.
    - **Real state**: four more QuickCart features created purely to verify this pass end-to-end
      through a real browser against a real local LLM (`feature_8f5f184f`/`feature_dc1172af`/
      `feature_d6715d99`/`feature_d7c8c638`, all "Return Requests" variants) -- left in place per
      this project's established convention, each showing a different real stage of the flow
      (fresh per-question start, mid-generation live stream, and a fully confirmed SRS with the
      race-condition fix correctly reflected in its FR-001).

34. **Frontend UX pass: edit-and-resubmit for every agent's past comments, a genuinely auto-growing
    chat composer, and the ability to delete an unapproved artifact version.** Direct user request
    (three sub-asks in one message): "User must be able to edit and resubmit the message to each
    agent like chat gpt and claude," the composer "must be dyanmic when user enters a huge message,"
    and "if the user wants to remove some un approved verion of SRS user must be able to do this."
    - **Edit-and-resubmit**: deliberately implemented as "reload the original comment text back
      into the composer, let the human resend it as a new message" rather than a true in-place
      history rewrite, for every agent EXCEPT Requirement's pre-SRS conversation (which already has
      real rewindable state via `known_answers_before` snapshots and keeps its own dedicated
      inline-edit-with-rewind system, untouched). Every other run/revise call is stateless with
      respect to prior comments -- an already-produced artifact really was generated from the
      original text and can't be honestly "un-produced," so rewriting its history would be
      dishonest. `RequirementConversationParts.jsx`'s `PencilIcon` exported; `ChatBubble.jsx` gained
      a hover-reveal Edit button on "ask" bubbles (`group`/`group-hover:opacity-100`) calling a new
      `onEdit(comment)` prop; wired through `ChatPanel.jsx` and `RequirementRevisionChat.jsx` as
      `onEdit={setComment}`.
    - **Auto-growing composer**: the previous heuristic (`rows={Math.min(6, value.split("\n").length)}`)
      only grew on explicit Shift+Enter presses, not on a long soft-wrapped single line.
      `ChatComposerBox.jsx` now measures real `scrollHeight` via a `textareaRef` + `useEffect`
      (`style.height = "auto"` then `scrollHeight`, capped at `MAX_TEXTAREA_HEIGHT_PX = 240` with
      `overflow-y-auto` beyond that) -- confirmed live: a long unbroken sentence grew the box from
      20px to 100px tall with zero manual line breaks.
    - **Delete an unapproved artifact version**: `artifact_service.delete_artifact(artifact_id)` +
      `DELETE /artifacts/{artifact_id}` (204; 400 if approved) + frontend `deleteArtifact`/
      `useDeleteArtifact`/`ArtifactRow.jsx`'s inline Delete -> "Confirm?"/"Cancel" two-step button.
      **A real bug found only by live verification, not by code review**: this codebase's own
      documented convention is that every gating artifact_type saves a JSON+Markdown pair sharing
      ONE version, and the frontend's version list (`dedupeArtifactVersions`) collapses that pair
      into a single displayed row, showing only the stage's preferred format (e.g. `json` for
      `srs`). The first implementation deleted only the ONE artifact_id behind that row -- so
      deleting "SRS v1" only ever deleted the JSON half; the Markdown half silently remained in the
      database and (worse) then became the row's new representative on the next list refresh,
      making the version appear to un-delete itself. Fixed by making `delete_artifact` operate on
      the whole VERSION: it now finds every sibling sharing `(feature_id, artifact_type, version)`
      and deletes all of them together -- confirmed live, deleting one row now removes both
      artifact_ids from the database in one action. **A second, related bug found in the same live
      pass**: the initial fix's approval guard only checked the ONE artifact_id being deleted, not
      its siblings -- calling delete directly on the still-pending Markdown half of an
      already-JSON-approved pair succeeded, orphaning the approved JSON without its Markdown
      sibling (unreachable through the actual UI, since `dedupeArtifactVersions` always shows the
      approved JSON as that row's representative and `ArtifactRow`'s `canDelete` correctly hides
      Delete for it -- but directly reachable via the raw API). Fixed by checking every artifact in
      the whole version group for `APPROVED` status before allowing any of them to be deleted, not
      just the one requested. **Any future logic operating on "one artifact" for a gating
      artifact_type must remember it's really a two-row version-pair** -- this is the second time
      this exact JSON+Markdown pairing convention has caused a real bug from code that only
      considered one half (see item 30's `pickViewer`/`code_diff` gotcha for the first).
    - Also caught, mid-verification, an operational gotcha worth remembering: after editing
      `artifact_service.py`, the already-running `uvicorn` process (started without `--reload`)
      kept serving the OLD code -- the first live delete test "worked" but silently used
      pre-fix behavior, because the backend was never restarted after the edit. **Any backend
      code change made while a test instance is already running needs an explicit restart before
      the next live verification pass**, or the verification is testing stale code.
    - Full backend suite: **277 passed** both before and after the fix (no new unit tests were
      added specifically for `delete_artifact`'s cascade/guard logic -- this was verified live,
      end-to-end, via a real isolated backend/frontend instance and a real browser, not synthetic
      fixtures; a future session adding `tests/test_artifact_delete.py` would be a reasonable
      follow-up to lock this in). `npm run build` clean (only the pre-existing chunk-size
      advisory). Real, live verification: created a throwaway project (`proj_6e968a81`, "RF Verify
      Test") and feature (`feature_00f51c11`, "Verify Feature") on fresh isolated ports (8060/5185),
      drove a real conversation through a real local LLM to a confirmed SRS, requested a real
      revision (confirming both the edit-and-resubmit UI AND the auto-grow textarea in the same
      pass), then exercised delete on both an unapproved version (succeeded, cascaded correctly)
      and an approved one (correctly refused, 400) -- fully cleaned up afterward (project deleted
      via the existing `DELETE /projects/{id}` endpoint, both test processes killed).

35. **Delete confirmation upgraded from inline text to a real popup, and Requirement Agent
    revisions redesigned so a requested edit actually happens.** Two direct user reports: (1) the
    delete-artifact confirm from item 34 should be "through a popup message," not inline
    Confirm/Cancel text; (2) asked the Requirement Agent to remove one specific NFR
    ("Listing page must load within 2 seconds for up to 10,000 items") from an already-generated
    SRS, and the item was still present in the newly generated SRS after revision -- "the agent
    must dynamically address those user needs and performed those requirements/instruction."
    - **Popup**: new `frontend/src/components/common/ConfirmDialog.jsx` (wraps the existing
      `Modal`) -- `ArtifactRow.jsx`'s inline "Delete" -> "Confirm?"/"Cancel" text toggle replaced
      with a real modal (`ConfirmDialog`) naming the exact artifact type + version being deleted.
    - **Root cause of the ignored-removal bug, confirmed by reading the code (same defect class as
      item 29's Domain Agent fix)**: `revise()`/`revise_stream()` asked the LLM to retype the
      ENTIRE SRS JSON verbatim on every revision, changing only what the comment asked for. On
      this local model, that's unreliable -- and critically, the reliability ladder's fallback for
      a totally failed/unparseable LLM call (`_fallback_revise_srs_json`) just **cloned the
      existing SRS unchanged**, silently discarding the human's requested edit with no visible
      error anywhere. Given this project's own extensively-documented local-model JSON reliability
      issues, this fallback path is the prime suspect for what the user hit.
    - **Fix, mirroring item 29's Domain Agent redesign exactly**: the LLM is no longer asked to
      retype the SRS. `REQUIREMENT_REVISION_SYSTEM_PROMPT` (`prompt.py`) now asks for a small
      `{"revision_summary", "operations": [{"action": "remove"|"add"|"modify"|"set", "field",
      "target", "value", ...}]}` plan -- one operation per distinct change, "target" must quote an
      existing id/exact text so it can be matched precisely, and an irrelevant/unmatchable request
      must return an EMPTY operations list plus an honest revision_summary explaining why, never a
      guessed change. New `app/agents/requirement_agent/revision_patcher.py`
      (`apply_revision_operations`) deterministically applies that small plan to the real SRS:
      handles plain-string-list fields (scope, constraints, etc.), `{id, description}`-object-list
      fields (functional_requirements/non_functional_requirements/acceptance_criteria/
      validation_rules, matching by exact text, id, OR substring containment so the LLM can quote
      just the distinctive part of a long requirement), `user_stories`'s own shape, and top-level
      scalar fields -- rebuilding `traceability` afterward if functional_requirements changed.
      Every operation the patcher couldn't confidently match, and the zero-operations case, are
      appended directly to the revised SRS's own `assumptions` array (plus a new
      `revision_metadata.applied_changes`/`unmatched_operations` pair) -- so "the agent silently
      didn't do what I asked" is no longer possible; it either happens or is explicitly said not
      to have happened, visible in the document itself. `agent.py`'s `_revise_srs_json` (used by
      `revise()`) gained the same LLM-call -> JSON-repair-retry -> deterministic-fallback ladder
      shape `revise_stream()` already had (it previously had no repair step at all). The streamed
      raw output during a revision is now the small plan, not the whole document -- updated the
      Result panel's live-view label ("Reviewing your requested change..." instead of
      "Regenerating SRS...") and the revision chat's banner copy to match what's actually
      happening; `revision_summary` stays the first JSON key so the existing chat-bubble streaming
      extraction is unaffected.
    - **Real, live verification, not just synthetic tests**: created a fresh test feature with an
      SRS containing the user's exact NFR text, requested the user's exact revision comment through
      the real streaming endpoint against a real local LLM -- the model produced a correct,
      one-operation plan on the FIRST attempt (no repair, no fallback), and the resulting SRS v2
      genuinely no longer contains that NFR, with `revision_metadata.applied_changes` recording
      exactly what happened. A second real test with a deliberately nonsensical removal request
      ("remove the requirement about time travel and quantum encryption") correctly returned zero
      operations, with both `revision_summary` and a new `assumptions` entry honestly stating
      nothing was changed. Also verified the delete popup live: clicking Delete now opens a real
      modal naming the exact version, Cancel closes it with no request sent, and confirming deletes
      the version (cascading both JSON+Markdown, per item 34's fix) and closes the dialog.
    - New `tests/test_requirement_revision_patcher.py` (10 tests, no LLM -- exact/id/substring
      removal matching, unmatched-removal-is-reported not silently dropped, add/modify for both
      list shapes, user_stories add, traceability rebuild after FR removal, malformed operations
      skipped not raised). Full suite: **287 passed** (up from 277). `npm run build` clean.

36. **Pin which approved SRS version feeds the Domain Agent, instead of always the latest.**
    Direct user request, prompted by seeing two approved SRS versions (v2/v3) in "All Artifacts"
    with no way to control which one the next agent actually uses: "the lastly approved version
    will continue to next agent and mentioned the name of using SRS for the next phase on the
    right side of the result section, top right corner after the preview tab. And add a radio
    button in the approved SRS for the user to select which [version is] going to be use[d]."
    - **Backend**: `FeatureResponse` gained `active_artifact_selection: dict[str, str]` (maps
      `artifact_type -> artifact_id`, e.g. `{"srs": "artifact_..."}`), stored on the feature
      document, defaulting to `{}` for every pre-existing feature (an absent entry means "use the
      default," never an error). New `artifact_service.get_selected_or_latest_approved_artifact
      (feature_id, artifact_type, artifact_format=None)`: returns the pinned artifact if one is
      set AND still valid (belongs to this feature, still that type/format, still APPROVED) --
      otherwise the latest approved version by version number, i.e. **exactly** the same default
      every stage's own private `_find_latest_approved_*` duplicate (Architecture/Domain/UI-UX/
      Coder Agent each have one, confirmed by reading them) already used. A stale/deleted
      selection silently falls through to that default rather than raising -- pinning is a soft
      override, never a way to brick the pipeline if the pinned version later disappears. New
      `artifact_service.set_active_artifact_selection(feature_id, artifact_type, artifact_id)`
      (raises ValueError -> 400 for: unknown feature/artifact, wrong feature, wrong type, or not
      APPROVED -- only an approved version is ever a meaningful choice). New route `PUT
      /features/{feature_id}/artifacts/active-selection`. **Only `DomainAgent.
      _find_latest_approved_srs_artifact` was wired to this** (delegates to the new shared method
      instead of its own private duplicate) -- per the user's explicit scope ("specially to the
      next agent" = Domain Agent reading the SRS). The other three agents' private
      "latest-approved" duplicates are untouched; wiring any of them the same way later is a
      trivial one-line change to `get_selected_or_latest_approved_artifact`, not a new mechanism.
    - **Frontend**: new `frontend/src/lib/activeArtifactSelection.js`'s
      `getEffectiveActiveArtifact(artifacts, activeSelection, artifactType, artifactFormat="json")`
      mirrors the backend's exact default/override logic client-side (no extra round trip) --
      used by both the indicator and the radio button so they can never disagree.
      `OutputPanel.jsx`'s tab bar (previously just the Result/Files/Preview buttons) gained a
      `justify-between` layout and a right-aligned pill per entry in a new
      `NEXT_AGENT_BY_ARTIFACT_TYPE` map (`{srs: "Domain Agent"}` today) reading
      `"Using SRS vN for Domain Agent"` -- exactly the "top right corner after the preview tab"
      placement asked for. `ArtifactRow.jsx` gained a real `<input type="radio">` (grouped by
      `name={"active-" + artifact_type}`) shown only on rows where `showActiveSelector` is true
      AND `approval_status === "approved"` (mirrors the backend's own 400 guard -- the radio
      simply never appears somewhere it would be rejected), plus an "In use" pill on whichever row
      is currently effective. `ResultTab.jsx` computes `effectiveActiveArtifact` via the shared
      helper and passes `activeArtifactType`/`activeArtifactId`/`onSetActive`/`settingActive`
      through `ArtifactList.jsx` to each row; a new `useSetActiveArtifactSelection(featureId)`
      mutation (`useFeatures.js`) writes straight into the `["feature", featureId]` query-cache
      entry on success (same "direct cache write, no refetch" idiom already used elsewhere in
      this codebase for a small, single-document response) so the indicator and every row's
      radio state update immediately, in the same render, with no extra fetch.
    - New `tests/test_artifact_active_selection.py` (5 tests, no LLM/HTTP -- defaults to latest
      when unset, explicit selection overrides the latest-version default, selecting a
      non-approved artifact is refused, selecting an artifact belonging to a different feature is
      refused, a stale/deleted selection falls back to the latest-approved default rather than
      erroring). Full suite: **292 passed** (up from 287).
    - **Real, live verification**: created a fresh test feature, generated and approved SRS v1,
      requested a revision and approved the resulting v2 too (so two real approved versions
      coexisted, reproducing the screenshot that prompted this request) -- confirmed the indicator
      defaulted to "Using SRS v2 for Domain Agent" (the latest, matching prior behavior with zero
      selection made) and v2's row showed the radio checked with an "In use" pill; clicked v1's
      radio button and confirmed, in the same screenshot pass, the indicator updated live to
      "Using SRS v1 for Domain Agent", the checked radio moved to v1's row, and
      `GET /features/{id}` genuinely returned `active_artifact_selection: {"srs":
      "<v1's real artifact_id>"}` -- the persisted backend state matches exactly what the UI
      showed, not just a client-side-only toggle. `npm run build` clean throughout.

37. **SRS approval exclusivity, an approve-confirmation popup that auto-starts Domain Agent and
    auto-switches the chat, and a real (not testing-artifact) fix making edited chat messages
    stream live instead of sitting behind a static spinner.** Two direct user reports in one
    message: (1) "user can only approved only one SRS user can not select multiple SRS verions" --
    reacting to the real state from item 36's verification where v1 AND v2 were BOTH left
    "Approved" simultaneously; (2) "Once the user clicks on the approved button A popup message
    appear confirming to user and starting the domain agent... user clicks okay the domain agent
    chat will start automatically"; and, separately, "When User edit the user message it will not
    appear on the chat box section."
    - **SRS exclusivity** (`approval_service.py`'s `submit_approval`): approving an SRS artifact
      now finds every OTHER `srs`-type artifact for the same feature currently `APPROVED` and
      reverts it to `PENDING`. Scoped narrowly to `ArtifactType.SRS` specifically, not every
      gating type -- UI/UX's `ui_component_code` artifacts are legitimately, independently
      approved several at a time (distinct components, not versions of one document); SRS is a
      singleton document with versions, which is what this rule is actually about.
    - **Approve confirmation + auto-run Domain Agent + auto-switch chat**: new
      `ConfirmDialog.jsx` gained a `tone` prop (`"danger"` red / `"primary"` accent) and a
      `confirmingLabel` prop (previously hardcoded "Deleting...") so the same component now
      serves both delete confirmations and this positive-action one.
      `GovernancePanel.jsx` (not `ApprovalPanel.jsx` -- see the real bug below) owns a
      `confirmingApprove`/`phase` state machine and its own `useApprovalMutation`/`useRunDomain`
      instances: confirming -> approve (supersedes any other approved SRS per the fix above) ->
      `runDomain.mutateAsync({})` (the existing manual-trigger path already wired for the
      composer, per item 30 -- no LangGraph run needs to have been started) -> `selectAgent
      ("domain")`. `OutputPanel.jsx`'s "Using SRS vN for Domain Agent" indicator (item 36) and
      this popup now compose correctly since both read the same exclusivity-respecting state.
    - **A real bug found and fixed mid-verification, not by static reading**: the confirm+run+
      switch sequence was originally written as an async function living INSIDE `ApprovalPanel`
      -- which is unmounted by its own parent the instant the artifact's `approval_status` stops
      being `"pending"` (exactly what happens right after the approval call succeeds, mid-
      sequence). Confirmed directly: a live run's debug logging showed `"approval.mutateAsync
      resolved"` and then NOTHING -- no `runDomain` log, no thrown/caught error, no `selectAgent`
      call -- the async function was silently abandoned the moment its owning component
      unmounted. Fixed by moving the entire confirm-dialog + orchestration up to
      `GovernancePanel.jsx`, which never unmounts across that transition (it only swaps which
      child it renders); `ApprovalPanel.jsx` was simplified back to a dumb component taking an
      optional `onApproveClick(comment)` callback instead of owning any multi-step flow itself.
      **Any future multi-step async sequence triggered from a button inside a conditionally-
      rendered child must live in the nearest ancestor that stays mounted across every state
      transition the sequence itself causes** -- this is the second time this exact class of bug
      has been found in this codebase (see item 34's cascade-delete note for the first, different
      shape of "one artifact_id isn't the whole logical unit" mistake) but a new failure mode
      (component lifetime, not data modeling).
    - **A second real, related bug found in the same verification pass**: `ResultTab.jsx`'s
      `selectedVersion` state didn't reset when `stage` itself changed -- after the auto-switch to
      Domain Agent, if a version NUMBER happened to coincidentally exist for both `srs` and
      `enhanced_srs` (e.g. both have a "v4"), the panel kept showing the OLD stage's document
      under the NEW stage's header, since the existing "does this version still exist" check
      found a coincidental match and never re-picked the new stage's actual latest version. Fixed
      with a new, separate `useEffect` keyed only on `[stage]` that unconditionally resets to
      `versions[0]?.version` on every stage change, leaving the existing "new version arrived for
      the same stage" effect untouched.
    - **A third bug, pre-existing and unrelated to this session's new code, found and fixed along
      the way**: `ResultTab.jsx` always passed `gatingArtifactType={null}` to `ArtifactList`,
      which (per `ArtifactRow.jsx`'s OWN docstring -- "the gating artifact itself already gets the
      bigger ApprovalPanel below it, so callers should omit featureId there") was supposed to hide
      the redundant inline Approve/Reject on the ONE row that already has the bigger
      Governance-panel controls. Since it was always `null`, EVERY row (including the gating one)
      showed BOTH controls -- meaning the SRS's Approve button had two live copies, only one of
      which (Governance's) went through the new confirmation flow; the other (the inline one)
      still approved immediately with no popup, no exclusivity awareness at the UI level (the
      backend-level exclusivity fix still applied either way, but the human-facing confirmation
      could be silently bypassed). Fixed by passing the stage's real gating type
      (`STAGE_GATING_ARTIFACT[stage]?.type`) instead of a hardcoded `null`.
    - **The "edit message doesn't appear" report: extensively investigated, and NOT a bug in the
      edit-and-resubmit or edit-and-regenerate mechanisms themselves** -- both were verified live,
      multiple times, to work correctly: `RequirementRevisionChat`'s hover-edit-reload-into-
      composer-resubmit flow (item 34's pattern) and `RequirementConversationChat`'s true inline
      edit-with-rewind flow (`HumanBubble`, pre-existing, kept unchanged per item 34's own
      design note) both correctly save the edit and refresh the display -- confirmed via direct
      backend inspection after each. **The real, confirmed gap**: unlike every other reply-shaped
      action in this conversation (normal replies, revisions, confirms), editing a turn used a
      plain, non-streaming call -- the edited message sat behind only a spinner for however long
      the real LLM call took (which, on this local model, is routinely 30s-several minutes,
      already extensively documented elsewhere in this file). A human watching a static spinner
      for that long, with zero visible progress, would very reasonably conclude "this isn't
      working" -- exactly the perceived-breakage this session has repeatedly fixed for OTHER
      flows by making them stream (see items 32/33). Fixed by adding the same treatment here:
      new `RequirementAgent.edit_turn_reply_stream` (mirrors `reply_to_conversation_stream`
      exactly -- same token/error/done event shape, same repair-then-deterministic-checklist
      ladder, same rewind-via-`known_answers_before`/`existing_turns_override` logic as the
      existing non-streaming `edit_turn_reply`), new route `POST .../conversation/turns/
      {turn_index}/edit/stream`. Frontend: `RequirementConversationChat.jsx` gained an
      `editingContext` state (`{turnIndex, pendingReply}`) so the turn being edited shows its new
      text immediately plus a live `LiveReactionBubble` (reusing the exact component normal
      replies already use), while every turn AFTER it is hidden outright during the stream
      (they're about to be discarded by the rewind anyway, so showing them only to yank them away
      once the stream lands would be its own small "did that just disappear?" moment). The
      now-fully-superseded non-streaming frontend path (`useEditRequirementConversationTurn`,
      `editRequirementConversationTurn` API function) was removed outright, matching this
      session's established precedent for a mutation once nothing calls it anymore -- the backend's
      plain route is untouched for direct API callers.
    - **A real, separate infra gotcha re-confirmed hard during this verification (already
      documented for a different endpoint earlier in this file, but worth restating since it cost
      real time here too)**: the isolated test backend process was started BEFORE the new
      `/edit/stream` route was added to the source, and since it runs without `--reload`, every
      request to that route 404'd -- confirmed directly via a raw `curl` bypassing the frontend
      entirely, which is what made this diagnosable in under a minute once tried. **Any backend
      route added mid-session to an already-running test instance needs an explicit process
      restart before it can be exercised** -- this has now caused real, multi-minute confusion at
      least twice in this file's history.
    - **A second real testing-methodology lesson, specific to Playwright + streaming fetch
      responses**: `browser.close()` immediately after taking a screenshot silently aborts any
      still-in-flight `fetch()` request the page had open -- including this exact streaming edit
      call, which on `qwen3-coder:latest` can genuinely take minutes. Several verification
      attempts appeared to "fail" (backend never saved the edit) purely because the test script
      closed the browser before the real, slow LLM call had actually finished -- not a product
      bug. The only way to get a trustworthy verdict was `page.expect_response(...)` wrapped
      around the triggering click, with a long timeout, keeping the browser open until the real
      HTTP response object itself resolved -- confirmed a genuine 200 with the full NDJSON body,
      and confirmed the backend's saved turn matched the edited text afterward. **Any future
      verification of a slow, real-LLM-backed streaming call must wait on the actual response
      object (or an equivalent hard signal), never a fixed timeout or a DOM-text heuristic that
      can match an optimistic bubble before the real work finishes.**
    - New backend tests: `tests/test_approval_srs_exclusivity.py` (3 -- approving a new version
      supersedes the old one, reject/revision-request never touches siblings, exclusivity never
      bleeds into unrelated artifact_types like `ui_component_code`);
      `tests/test_requirement_conversation.py` gained 2 (`edit_turn_reply_stream` yields
      tokens-then-done with the new reply correctly saved and the old turn's stale data replaced;
      errors cleanly on an unknown turn index). Full suite: **297 passed** (up from 292).
      `npm run build` clean throughout.
    - **Real, live verification for every piece**: created a fresh feature, generated and
      approved SRS v1 through the real popup, then revised+approved v2 through v6 in sequence,
      confirming at each step that only the just-approved version stayed "Approved" and every
      other version reverted to "Pending" (real, persisted `GET /features/{id}/artifacts` checks,
      not just UI screenshots) -- and that the "Using SRS vN for Domain Agent" indicator, the
      per-row radio, and the actual `enhanced_srs` content Domain Agent produced (verified by
      reading its `revision_metadata.revision_comment` directly) all agreed on which version was
      current, every time. Separately verified the streaming edit fix with a genuine multi-minute
      real LLM call, confirmed complete via the real HTTP response object, with the backend's
      saved turn matching exactly what was typed. All test projects/processes cleaned up
      afterward.

38. **Added a delete-feature capability (previously didn't exist at all -- only whole-project
    delete did) and used it to remove a real feature per direct user request**: "Remove Item
    listing page feature in the Retail store project." Confirmed via the real, running main
    backend (port 8000, `--reload`) that no delete-feature route/service/UI existed anywhere --
    `delete_project` (`app/api/routes/projects.py`) was the only precedent. New
    `DELETE /features/{feature_id}` (`app/api/routes/features.py`, same file/route-body style as
    `delete_project`, not a separate service layer) cascades this ONE feature's artifacts,
    approvals (joined by both `feature_id` and `artifact_id` since older approval records predate
    the `feature_id` field, matching `list_feature_approvals`'s own established join logic),
    stage_events, and requirement_conversations record -- deliberately narrower than
    `delete_project`: never touches the project's knowledge documents or the whole workspace repo,
    since sibling features in the same project may still need those. Best-effort discards this
    feature's own git branch via the pre-existing `workspace_service.discard_feature_branch`, but
    ONLY when `(repo_path / ".git").exists()` first -- `discard_feature_branch` internally calls
    `ensure_project_repo`, which CREATES a workspace as a side effect if none exists yet; without
    this guard, deleting a feature that never advanced past Requirement (never had a workspace to
    begin with) would spuriously create one just to find nothing to discard in it.
    - Frontend: `deleteFeature`/`useDeleteFeature(projectId)` (mirrors `useDeleteProject`'s exact
      shape). `FeatureListItem.jsx`'s outer element changed from a single `<button>` to a `<div>`
      wrapping the existing select-button plus a new hover-reveal `&times;` delete button
      (can't nest a `<button>` inside another `<button>` -- invalid HTML, hence the wrapper div).
      `FeatureListPanel.jsx` owns a `deletingFeature` state + a `ConfirmDialog` (item 37's
      component); confirming deletes, then navigates to the bare `/projects/{projectId}` route
      (clearing the URL's `featureId`) if the deleted feature was the currently-selected one, so
      `ProjectWorkspacePage` recomputes `effectiveFeatureId` from whatever features remain instead
      of pointing at a feature that no longer exists.
    - New `tests/test_feature_deletion.py` (3 -- deleting one feature removes everything scoped to
      it; a sibling feature and ITS artifacts are completely untouched; deleting an unknown
      feature_id 404s). Full suite: **300 passed** (up from 297). `npm run build` clean.
    - **Real state change, not test debris**: confirmed the target via the real, live main backend
      (`GET /projects` -> `proj_61b14680` "Retails store" -> its one feature,
      `feature_06e647d2` "Item listing page", `in_progress`, 6 SRS artifacts across v2-v4 with two
      simultaneously "approved" -- itself a live example of item 36's since-fixed exclusivity gap,
      predating that fix reaching this long-running `--reload` process's already-loaded state).
      Confirmed the new route was live on this exact process without a manual restart (uvicorn's
      `--reload` picked up the new route from the file edit automatically) before calling
      `DELETE /features/feature_06e647d2` for real. Verified fully gone afterward: the project's
      feature list is now empty, and both `GET /features/feature_06e647d2` and its `/artifacts`
      sub-resource return 404. The "Retails store" project itself, and every other real project in
      this same database, were not touched.

39. **Fixed a real, reported gating-artifact-resolution bug: rejecting the newest SRS version made
    the whole feature show "Rejected" even though an OLDER version was still genuinely pending,
    and there was NO way through the UI to approve that older version at all.** Direct user
    report with a screenshot: rejected SRS v2 while v1 sat at `approval_status: "pending"`; the
    feature list showed "Item listing page ... Requirement [Rejected]", and nothing in the UI let
    them approve v1. Explicit ask: rejecting/deleting one version must never make the whole
    feature show rejected/deleted as long as another version is still pending a decision, and the
    human must be able to select and approve WHICHEVER version they want, not just be stuck with
    "the latest."
    - **Root cause** (`frontend/src/lib/deriveStageStatus.js`): `latestArtifactOfType` picked the
      gating artifact strictly by highest `version` number, with zero regard for
      `approval_status`. Both `deriveStageStatus` (feeds the sidebar's status badge) and
      `getLatestGatingArtifact` (fed `GovernancePanel`'s single `ApprovalPanel`, i.e. the ONLY
      place with Approve/Reject/Request-Revision buttons for the gating type) used this same
      strictly-latest pick -- for `[v1: pending, v2: rejected]`, both always resolved to v2,
      regardless of v1's genuinely-actionable state.
    - **Fix**: replaced `latestArtifactOfType` with `resolveGatingArtifact(artifacts, type,
      format)` -- APPROVED wins if any version is (highest-versioned one, defensively, since the
      exclusivity rule from item 37 means there should only ever be one) -- else the
      highest-versioned still-PENDING/REVISION_REQUESTED version (a real decision still waiting,
      regardless of whether some OTHER, newer version was rejected) -- else the highest-versioned
      version overall (every version decided on and rejected -- correctly reported as rejected)
      -- else `null`. `deriveStageStatus` and the renamed `getOperativeGatingArtifact` (renamed
      from `getLatestGatingArtifact` since it deliberately no longer always returns the latest)
      both use this. Deleting a version needs no special-casing at all -- it just disappears from
      the `artifacts` array the resolver already operates over, so the precedence naturally
      re-resolves to whatever's left (exactly satisfying the "deleted" half of the report with
      zero extra code).
    - **The second half of the fix -- letting the human pick ANY pending version, not just the
      resolved "operative" one**: `ArtifactRow.jsx`'s existing per-row inline Approve/Reject/
      Request-Revision (already built for non-gating artifacts like individual UI/UX components)
      was being suppressed on EVERY row of a gating type, because `ArtifactList.jsx`'s `isGating`
      check compared by `artifact_type` alone -- with the type-only comparison, ALL versions of
      `srs` counted as "the gating one," hiding inline controls everywhere and leaving anything
      other than whatever `GovernancePanel` happened to show with literally no approval path.
      Fixed by adding a new `gatingArtifactId` prop (the exact operative artifact_id, not just
      the type) -- inline controls are now suppressed ONLY on that one specific row (avoiding a
      redundant duplicate with `GovernancePanel`'s bigger panel), while every OTHER pending
      version of the same type gets its own fully-functional inline Approve/Reject/Request-
      Revision, confirmed live with a genuine two-simultaneously-pending-versions scenario.
    - **Kept the item-37 SRS confirm-and-auto-run-Domain-Agent UX consistent across both entry
      points**: the confirm-dialog + approve + `runDomain` + `selectAgent("domain")` orchestration
      (previously living in `GovernancePanel.jsx`, per item 37's own unmount-safety fix) was
      lifted one level further up, to `ResultTab.jsx` -- the actual shared ancestor of BOTH
      `GovernancePanel` (the operative row's approval) AND `ArtifactList`/`ArtifactRow` (every
      other pending row's inline approval). Both now call the same
      `requestSrsApproveConfirmation(artifactId)` callback via a new `onApproveClick` prop
      threaded through `GovernancePanel`->`ApprovalPanel` and `ArtifactList`->`ArtifactRow`
      respectively, so clicking Approve on ANY pending SRS row -- the operative one or not --
      shows the identical confirmation dialog (correctly naming whichever version was actually
      clicked) and triggers the identical approve-exclusivity + auto-Domain-Agent-run + auto-
      chat-switch sequence. `GovernancePanel.jsx` and `ArtifactRow.jsx` themselves no longer own
      any multi-step async state -- both are back to being plain components that either call
      their own immediate mutation or defer to a parent-supplied callback.
    - No backend changes were needed at all -- confirmed by re-reading `submit_approval` that
      rejection already has zero effect on sibling versions (only approval's exclusivity rule,
      from item 37, touches siblings), so this was purely a frontend derivation bug.
    - **Real, live verification, reproducing the exact reported screenshot scenario**: created a
      fresh feature, generated SRS v1, revised to v2, and rejected v2's JSON artifact directly
      (matching the user's exact repro) -- confirmed the sidebar now shows "Awaiting review" (not
      "Rejected"), `GovernancePanel` now shows "Awaiting your review (v1)" (not v2), and clicking
      Approve there shows a dialog correctly reading "Approving v1..." Completed the full flow for
      real (real approval, real Domain Agent run, real auto-switch) and confirmed the top-right
      indicator read "Using SRS v1 for Domain Agent" afterward -- the whole pipeline genuinely used
      the human-approved v1, not the rejected v2. Separately verified the "multiple simultaneously
      pending versions" case on a second feature (v1 pending, v2 pending, neither rejected): v2 (the
      resolved "operative" one) correctly has no inline controls (GovernancePanel already covers
      it), while v1 correctly has its own live Approve/Reject/Request-Revision, and clicking its
      Approve button opens a dialog correctly reading "Approving v1..." -- confirming a human can
      genuinely choose either version, not just whichever one the resolver happens to prefer.
      `npm run build` clean throughout; no frontend test framework exists in this repo (no
      vitest/jest configured), so this was verified live rather than with unit tests, matching
      this session's established practice for pure frontend-logic changes. Test project and
      processes cleaned up afterward.

40. **Follow-up to item 39 (same session, same reported flow): item 39's fix only made the
    STATUS badge version-aware -- it did NOT make every pending version individually approvable.
    A second screenshot ([v1: pending, v2: rejected, v3: pending]) showed v1 alone had inline
    Approve/Reject/Request-Revision, v3 had none at all** -- direct quote: "currently system
    allow user to choose only one user can not selecte one among multiple versions... if user
    approved other versions should be automatically disabled." Root cause: item 39's own fix
    still suppressed inline controls on whichever ONE row `getOperativeGatingArtifact` resolved
    to (to avoid a literal duplicate with `GovernancePanel`'s panel) -- so exactly one pending
    version (not necessarily the one the human wants) kept its buttons, and every OTHER pending
    version of the same type still had none. Two-part fix:
    - **Removed the per-row suppression entirely** (`ArtifactList.jsx`): every pending/rejected
      version of every artifact_type now gets its own inline Approve/Reject/Request-Revision,
      full stop -- no row is ever hidden in favor of a "operative" one anymore. Accepted a small,
      deliberate redundancy as the trade-off: the one row `GovernancePanel`'s dedicated
      `ApprovalPanel` also shows now displays approval controls in two places (inline in "All
      Artifacts" AND in the "Governance" section below) -- harmless duplication, not a
      functional bug, and simpler/safer than the alternative of removing `GovernancePanel`'s
      panel entirely (which would also need to relocate its `APPROVAL_WARNINGS` -- the uiux/coder
      merge-risk warnings -- somewhere else, out of scope for this fix).
    - **New `approveLocked` behavior**, directly per the user's explicit "automatically disabled"
      wording: `ArtifactList.jsx` computes, per row, whether a SIBLING of the same artifact_type
      is already `approved`; if so, that row's Approve button (only Approve -- Reject/Request
      Revision stay active, e.g. to formally clear out an old unused version) is disabled with a
      title explaining why. Switching which version is approved still works -- it just requires
      explicitly rejecting the current approval first (a deliberate, safer two-step flow instead
      of letting a stray click on a different row silently re-trigger the whole approve + auto-
      run-Domain-Agent + auto-switch-chat sequence from item 37/39).
    - `ResultTab.jsx`/`ArtifactRow.jsx` updated accordingly (dropped the now-unused
      `gatingArtifactId` prop and its suppression logic entirely; `ArtifactRow` gained the
      `approveLocked` prop). No backend changes.
    - **Real, live verification, reproducing the EXACT second screenshot**: recreated
      `[v1: pending, v2: rejected, v3: pending]` on a fresh feature -- confirmed both v1 AND v3
      now show independent, fully-functional Approve/Reject/Request-Revision (v2, rejected,
      correctly shows none). Approved v1 specifically (not v3, the "operative" one) through the
      confirm dialog -- confirmed it read "Approving v1..." and, after completion, the top-right
      indicator correctly read "Using SRS v1 for Domain Agent" and the chat auto-switched to
      Domain Agent, proving genuinely free selection. Reloaded fresh and confirmed v3's Approve
      button is now `disabled` with the exact expected tooltip ("Another version is already
      approved -- reject it first to approve a different one"), while v1 shows "Approved"/"In
      use" with its own radio button. `npm run build` clean; verified live only (no frontend
      test framework in this repo, matching item 39's own note). Test project/processes cleaned
      up afterward.

41. **Domain Agent ran blind immediately on SRS approval, before the human ever got a chance to
    guide it** -- direct user report: "Once the user approved SRS... domain will carry a new chat
    that is specific only for domain agent... Once user directed/went to the domain agent chat
    domain agent must ask from user to improve the SRS by existing domain knowledge or user have
    somthing explicitly added to the SRS like Data base schema... If user have something user can
    prompt to the domain agent and get the result." Root cause: `ResultTab.jsx`'s SRS-approve
    orchestration (from item 37/39) called `useRunDomain(featureId).mutateAsync({})` -- an empty
    `human_comment` -- immediately after approval, before switching the chat to Domain Agent, so
    by the time the human arrived at Domain's chat the run had already happened; their only
    remaining option was to *revise* already-generated output instead of guiding the *original*
    generation. Confirmed via investigation that `human_comment` (advisory prompt context) and
    `referenced_document_ids` (guaranteed-inclusion pinned knowledge-document chunks) are both
    genuinely wired into Domain Agent's real behavior already (`agent.py`'s
    `_retrieve_domain_knowledge`/`_retrieve_domain_knowledge_for_revision`, capped at
    `MAX_CHUNKS_PER_PINNED_DOCUMENT`/`MAX_TOTAL_PINNED_CHUNKS`/`MAX_TOTAL_RETRIEVED_CHUNKS`) --
    this was a pure frontend sequencing bug, not a missing backend capability. Fix, frontend-only:
    - **`ResultTab.jsx`**: removed the automatic `runDomain.mutateAsync({})` call and its
      `approvalPhase` state machine entirely. `handleConfirmedSrsApprove` now only approves the
      SRS and calls `selectAgent("domain")` -- it no longer runs Domain Agent itself.
    - **`ChatPanel.jsx`**: replaced the old static "Domain Agent runs automatically..." helper
      text (shown when `!hasOutput && selectedAgent === "domain"`) with an actual proactive
      prompt: asks the human whether Domain Agent should enrich the SRS using existing domain
      knowledge alone or whether they have something specific to add (schema, compliance rule,
      business constraint), plus a "Just use domain knowledge" button that calls
      `runDomain.mutate({})` directly (the same empty-comment call that used to run
      automatically, now only on explicit request) for humans with nothing to add. The composer's
      placeholder for domain (when no output yet) now reads "e.g. Here's our database schema:
      ... (or leave blank and use the button above)" instead of a generic prompt. Pre-existing
      `SUGGESTION_CHIPS["domain"]` and the pre-existing `/`-mention document picker (see the
      Domain Knowledge upload feature, if landed) render alongside unchanged -- both were already
      gated on `canCompose`, which is unaffected by this fix.
    - No backend changes -- `/domain/run`'s `human_comment`/`referenced_document_ids` handling
      was already correct; this only fixed *when* and *with what* the frontend calls it.
    - **Real, live verification** across three fresh features (isolated backend/frontend
      instances, real LLM calls, no mocks): approved an SRS on each and confirmed Domain Agent did
      **not** auto-run (sidebar showed "Domain -- Not started", Result panel showed "No output yet
      for this stage") and the new proactive prompt rendered with the exact expected copy. Path 1
      (typed comment): submitted "Here is our database schema: items table has fields id, name,
      price, stock, quantity" as the human's first message to Domain Agent (confirmed, via a
      fully-instrumented Playwright session kept open across the approve -> type -> submit
      sequence, that the composer placeholder and the eventual request both correctly targeted
      `/domain/run`, not a misrouted `/requirement/revise/stream`) -- the run completed with a
      real domain-cited requirement in the resulting Enhanced SRS (`FR-DOM-001`, citing
      `product_catalog_and_inventory.txt`), confirming the human's turn-taking genuinely happens
      before generation, not after. Path 2 ("Just use domain knowledge" button): clicked the
      button on a separate fresh feature (via the composer's `PillDropdown`-based agent pill, not
      a native `<select>` -- see `AgentSelect.jsx`/`PillDropdown.jsx`), confirmed it fired
      `POST /agents/domain/run` with an empty comment and, polling until completion, produced real
      Enhanced SRS / Domain Improvements artifacts identical in shape to the pre-fix auto-run
      behavior -- so humans with nothing to add lose zero functionality, they just now have to
      make one click instead of it happening for them. `npm run build` clean; backend pytest
      suite 338 passed (11 failed + 3 errored, all pre-existing Docker-sandbox-dependent
      `test_coder_tools.py`/`test_coder_verify.py`/`test_render_checker.py` tests failing because
      no Docker daemon is reachable in this environment -- confirmed via the exact failure message
      "Sandbox unavailable: could not reach Docker daemon," unrelated to this fix, which touched
      no coder/sandbox code). No frontend test framework exists in this repo, matching every prior
      item's own note. Test project (`proj_217ffa15`, three features) and isolated
      backend/frontend processes cleaned up afterward.

42. **Every agent's chat showed every OTHER agent's activity too, not just its own -- and
    Domain Improvements was asked to be approved as its own artifact even though it was never a
    real decision point.** Direct user report, two parts in one message: "Each agent must keep
    it's own chat as an example when moving from requirement agent to domain agent, requirement
    agent chat can not be carried to the domain agent... this mechanism should be applied for
    every agent. And do not ask from user to approve Domain improvements artifact. user can only
    see this document attached with enhanced SRS version."
    - **Part 1 root cause**: `buildAgentTimeline.js`'s own docstring said the quiet part out loud
      -- it deliberately built "ONE continuous chronological feed across every agent for the
      whole feature" and `ChatPanel.jsx` rendered that entire feed unfiltered
      (`timeline.map(...)`) regardless of `selectedAgent`. So switching the chat to Domain Agent
      didn't just switch which messages were highlighted -- it kept showing Requirement's (and
      every other stage's) asks/responses/decisions mixed into the same feed. `RequirementRevisionChat`
      (Requirement's post-SRS chat) received the identical unfiltered `timeline` prop and had the
      same bug in the other direction.
    - **Fix**: `buildAgentTimeline(stage, allArtifacts, allApprovals, allEvents)` now takes the
      stage as its first argument and filters all three sources (events, artifact-version groups,
      approvals) down to that one stage from the start, not after the fact -- matching what its
      name always implied. `ChatPanel.jsx`'s one call site now passes `selectedAgent`. Since
      `RequirementRevisionChat` only ever renders when `selectedAgent === "requirement"`, and it
      receives the same now-scoped `timeline` variable, it's fixed for free. Generic across every
      stage (requirement/domain/architecture/uiux/coder) by construction -- one function, one call
      site, parameterized by stage, not a Domain-specific patch -- satisfying "this mechanism
      should be applied for every agent" without needing separate code paths per agent.
    - **Part 2 root cause**: `domain_improvements` is Domain Agent's own "what changed and why"
      side-record, saved at the same version as its Enhanced SRS
      (`domain_agent.py`'s `_save_domain_artifacts`) but never the type any stage actually gates
      on (`STAGE_GATING_ARTIFACT` only ever points at `enhanced_srs` for the domain stage;
      confirmed via grep that no backend service reads `domain_improvements`' approval_status at
      all). It still got saved with `approval_status: "pending"` like every artifact
      (`artifact_service`'s generic default) and, after item 40's fix removed per-row approval
      suppression for every artifact_type, started showing up as its OWN row in "All Artifacts"
      with its own real Approve/Reject/Request-Revision controls -- asking the human to approve a
      document that was never a real decision point, on top of the Enhanced SRS itself.
    - **Fix, `ResultTab.jsx`**: new `UNLISTED_ARTIFACT_TYPES = ["domain_improvements"]` excludes it
      from `stageArtifacts` entirely (no row, no approval controls, ever). Its content is instead
      rendered as a read-only attachment directly under the Enhanced SRS document view for the
      SAME version (found via `allArtifacts.find(a => a.artifact_type === "domain_improvements"
      && a.version === artifact.version)`, reusing the existing `ArtifactContentView` +
      `DomainImprovementsViewer` pair unchanged) -- exactly "attached with enhanced SRS version,"
      per the user's own wording. No backend changes -- this was purely a frontend listing/gating
      bug, the backend never treated it as a gate to begin with.
    - **Real, live verification** on a fresh feature (isolated backend/frontend instances, real
      requirement run -> approve -> domain run with a distinctive marker comment
      "DOMAIN_ONLY_MARKER: ..."): confirmed Requirement Agent's chat shows only its own
      Started/Produced SRS/Approved bubbles with zero trace of the marker; confirmed Domain
      Agent's chat shows only its own Started (with the marker)/Produced Enhanced SRS bubbles with
      zero trace of "Produced SRS" (Requirement's own response bubble). Confirmed "All Artifacts"
      for the domain stage lists exactly one row ("Enhanced SRS v1 -- Pending" with its own
      Approve/Request Revision/Reject) and no "Domain Improvements" row at all. Confirmed, by
      scrolling the Enhanced SRS document view, that a "Domain Improvements" section (heading,
      summary, additions/modifications) renders directly beneath the Enhanced SRS content with no
      approval controls anywhere near it, while the single "Awaiting your review" governance panel
      below still correctly gates only the Enhanced SRS. `npm run build` clean; no backend changes
      so the pytest suite is unaffected by this item. No frontend test framework exists in this
      repo, matching every prior item's own note. Test project/feature and isolated
      backend/frontend processes cleaned up afterward.

43. **Editing a chat message loaded it into the composer instead of editing it in place, and no
    message (user or agent) had a copy-to-clipboard affordance.** Direct user report: "When user
    editing the message, once the user clicks on the message edit button the message appear on
    the chat input field, It should not happen. When user wants do edit the message user must be
    able to edit the message/prompt on the massage and not on the input field, same as chat gpt
    or claude message edit system. And user must be able to copy the user message and the agent
    message as well. add copy icon to user prompt/messssage and evry agent prompt/messages."
    - **Edit root cause**: `ChatBubble.jsx` (used by `ChatPanel.jsx`'s generic per-agent chat for
      every stage except Requirement pre-SRS, and by `RequirementRevisionChat.jsx` for
      Requirement's post-SRS revise chat) implemented its "Edit" affordance as `onEdit={setComment}`
      -- clicking it copied the old message's text into the BOTTOM composer box, requiring the
      human to leave the message, notice the composer now had text in it, and hit Send again. This
      is not what "edit the message" means in ChatGPT/Claude -- confirmed by contrast with
      `RequirementConversationParts.jsx`'s `HumanBubble` (Requirement's pre-SRS chat only), which
      already did TRUE inline editing correctly (hover reveals a pencil, clicking it swaps the
      bubble in place for a textarea with Cancel/Save controls) -- that component was already
      correct and needed no changes.
    - **Fix**: `ChatBubble.jsx` rewritten to use the exact same in-place-swap pattern as
      `HumanBubble` for its "ask" bubbles -- clicking Edit swaps that one bubble for an inline
      textarea (seeded with the original text) with Cancel / "Save & Send" buttons directly
      beneath it; the composer at the bottom is never touched. New prop `onEditSubmit(text)`
      replaces `onEdit` -- since this app has no backend "rewind and regenerate" for run/revise
      artifacts (they're immutable once produced, unlike Requirement's pre-SRS conversation, which
      really does discard-and-regenerate via `edit_turn_reply`), Save still resubmits the edited
      text as the next message (same mutation the composer's Send already uses) -- just triggered
      from the message itself instead of a round-trip through the composer. `ChatPanel.jsx` and
      `RequirementRevisionChat.jsx` both factored their submit logic into a shared
      `submitAgentMessage`/`submitRevision` function used by both the composer's Send and the new
      `onEditSubmit`.
    - **Copy root cause**: no chat message anywhere had a copy-to-clipboard control at all.
    - **Fix**: new shared `frontend/src/components/common/CopyButton.jsx` (hover-reveal, matching
      the existing Edit affordance's convention, `navigator.clipboard.writeText` with a checkmark
      + "Copied" swap for ~1.5s on success). Wired onto every user AND agent message bubble across
      every chat: `ChatBubble.jsx`'s "ask" (user) and "response" (agent, copies the "Produced X
      (vN)" text) bubbles; `RequirementConversationParts.jsx`'s `HumanBubble` (user) and
      `AgentTurnBubble` (agent, copies the reaction text + any questions asked). Decision bubbles
      (the small centered "Approved"/"Rejected" pills) deliberately excluded -- they're status
      indicators, not prompts/messages, per the user's own two named categories. `AgentTurnBubble`
      and `ChatBubble`'s response bubble needed a `group` class added to their wrapper (previously
      absent -- only ask/HumanBubble had one, for the pre-existing Edit affordance) so the
      hover-reveal mechanism has something to key off of.
    - **Real, live verification** (isolated backend/frontend, real LLM calls, clipboard
      permissions explicitly granted in the Playwright context to actually confirm the copied
      bytes, not just that a button exists): on the pre-SRS conversation, clicked Edit on a real
      `HumanBubble` and confirmed the bottom composer's value was unchanged (empty) throughout;
      clicked Copy on both a `HumanBubble` and an `AgentTurnBubble` and read the clipboard back via
      `navigator.clipboard.readText()`, confirming it exactly matched the visible message text in
      both cases. On Domain Agent's chat (a real `ChatBubble` ask/response pair, produced via a
      real requirement-run -> approve -> domain-run with a distinctive comment), clicked Edit on
      the ask bubble and confirmed: an inline textarea appeared seeded with the exact original
      comment, the bottom composer's value stayed empty the whole time, and Cancel discarded the
      edit without sending anything. Clicked Copy on both the ask and response bubbles and
      confirmed the clipboard held the exact comment text and the exact "Produced Enhanced SRS,
      Domain Improvements (v1)" text respectively. `npm run build` clean; no backend changes so
      the pytest suite is unaffected. No frontend test framework exists in this repo, matching
      every prior item's own note. Test project/feature and isolated backend/frontend processes
      cleaned up afterward.

44. **Refreshing the browser reset the visible chat back to Requirement Agent -- read as "the
    other agent's chat history disappeared" -- and no agent's chat could be stopped mid-generation.**
    Direct user report: "Currently the chat histroy od each agent will dissepear when the user
    refreseh the browser it can not happen like that. The chat history of each agent must remain
    same. And each agent chat can be paused by the user like chat gpt or claude."
    - **Refresh root cause**: every agent's chat data was always durably persisted server-side
      (`stage_events`/`artifacts`/`approvals` for Domain/Architecture/UIUX/Coder and Requirement's
      post-SRS revise; the `requirement_conversations` record for Requirement's pre-SRS
      conversation) -- nothing was ever actually lost. `WorkspaceSelectionContext.jsx`'s
      `selectedAgent` was a plain `useState("requirement")` with zero persistence, though -- a full
      page reload always remounts this provider fresh, so it always snapped back to Requirement
      regardless of which agent's chat was on screen a moment ago. Purely a "what's currently
      displayed" bug, not a data-loss bug, but indistinguishable from one to the user.
    - **Fix**: `selectedAgent` is now seeded from (and kept in sync with) an `agent` URL query
      param via `useSearchParams`, the same mechanism `ProjectWorkspacePage` already uses for
      `featureId`. `selectAgent(stage)` writes `?agent=stage` (`replace: true`, no extra history
      entries); `selectFeature(id)` clears it back to Requirement's default, matching the existing
      "switching features resets to Requirement" behavior. A fresh load of the exact same URL now
      reopens the exact same agent's chat instead of silently jumping back.
    - **Pause root cause**: no chat had any way to stop an in-flight generation. Requirement
      Agent's pre-SRS reply/edit/confirm and post-SRS revise are real token-by-token streams
      (`fetch` + `ReadableStream`, `streamNdjsonPost` in `api/agents.js`); Domain/Architecture/
      UIUX/Coder run/revise are plain awaited axios POSTs with no streaming at all -- neither path
      had any cancellation wired in anywhere.
    - **Fix**: `streamNdjsonPost` and `postCancelable` (new shared helper for the plain axios
      calls) both accept an optional `signal`; aborting either mid-flight resolves with
      `{aborted: true}` instead of rejecting, so a deliberate stop never surfaces as a "Request
      failed" error banner. Every streaming mutation in `useRequirementConversationFlow.js`
      (`respondStream`, `editTurnStream`, `confirmStream`, `reviseStream`) and every mutation in
      `useAgentMutations.js` now creates a fresh `AbortController` per call and exposes a
      `stop()`/`stopXStream()` function that calls `.abort()`. `SendButton.jsx` renders a black
      square "Stop generating" button (ChatGPT/Claude's exact affordance) in place of the old
      disabled spinner whenever `pending` is true, wired through `ChatComposerBox`'s new `onStop`
      prop to whichever mutation/stream is currently active in `ChatPanel.jsx`,
      `RequirementConversationChat.jsx`, and `RequirementRevisionChat.jsx`; the confirm-generating
      and edit-generating indicators (which don't use the bottom composer) got their own inline
      "Stop" links.
    - **Two real, honestly-documented asymmetries between the two kinds of agents**, confirmed by
      reading the actual backend routes rather than assumed:
      1. For Requirement's 4 streaming endpoints, the whole turn (human_reply + agent's
         reaction/questions) is only ever persisted atomically by the stream's final "done" event
         -- stopping mid-stream means NOTHING was saved server-side (unlike ChatGPT/Claude, where
         the human's own message is durable the instant it's sent). Fixed the "silently lose what
         you typed" side-effect this would otherwise cause: `RequirementConversationChat.jsx`'s
         reply handler now checks the resolved `{aborted}` result and puts the exact typed text
         back in the composer if the stream was stopped before finishing, instead of discarding
         it. A parallel `isGenerating` bug this abort-resolves-not-rejects design would have
         caused (`confirmStream.isSuccess` alone stays true forever after ANY resolution,
         aborted or not, which would have wedged the UI in "Generating..." forever after a
         stopped confirm) is fixed by also checking `!confirmStream.data?.aborted`.
      2. For Domain/Architecture/UIUX/Coder's run/revise routes, by contrast, confirmed by reading
         `agents.py`: `stage_event_service.record(...)` runs SYNCHRONOUSLY before the agent call
         even starts, so the human's comment is durably saved as a real stage_event almost
         immediately regardless of whether the request later gets aborted -- these four agents
         needed no "restore the composer" recovery logic, and `useAgentMutations.js` always
         invalidates the `events` query on resolution (aborted or not) specifically so that
         already-saved "ask" bubble reliably shows up either way.
      Also honestly documented in code comments (not glossed over): stopping a real
      **streaming** generation genuinely halts the backend too (FastAPI/Starlette cancels a
      `StreamingResponse`'s underlying async generator when the client disconnects), but stopping
      one of the four **non-streaming** agents is honestly "stop waiting on it" from the human's
      side -- whether the backend's one plain `await agent.run(...)` call itself gets interrupted
      depends on how that particular call is structured, which this fix doesn't change.
    - **Real, live verification** (isolated backend/frontend, real LLM calls): switched to Domain
      Agent's chat, confirmed the URL became `...?agent=domain`, did a genuine full `page.reload()`
      (not a SPA navigation), and confirmed the agent pill still read "Domain" and the same
      proactive-prompt chat state was still showing afterward. Sent a real Domain Agent message
      with a distinctive marker comment, clicked Stop ~0.5s in, and confirmed: the button correctly
      reverted to a normal Send arrow, no error banner appeared, `GET .../events` showed the
      stage_event WAS recorded with the exact marker text despite the stop, and -- most tellingly
      -- the feature's Domain stage genuinely stayed "Not started" with zero Enhanced SRS artifacts
      produced, confirming the abort really did stop the backend agent, not just the frontend's
      view of it. Separately, on Requirement Agent's real pre-SRS streaming reply: clicked Stop
      ~2s into a visibly in-progress token stream, confirmed the black square Stop button rendered
      correctly mid-stream, the composer's text was restored to the exact original typed message
      after stopping, the conversation's `turn_history` length was provably unchanged (nothing
      persisted, as documented above), and the Send button correctly reverted afterward. `npm run
      build` clean; no backend changes so the pytest suite is unaffected. No frontend test
      framework exists in this repo, matching every prior item's own note. Test
      projects/features and isolated backend/frontend processes cleaned up afterward.

45. **Domain Agent silently discarded explicit human-provided content (e.g. "add this database
    schema"), the composer stayed frozen with the typed text in it until the whole enrichment
    finished, there was no live output, and no way to stop it -- Domain Agent was the one agent
    chat left behind after every one of these was already fixed for Requirement Agent.** Direct
    user report, five parts: (1) "When I tell domain agent to add database schema for the
    enhaced SRS the agent did not add what I asked" (2) the typed prompt stayed in the input
    field until generation finished, instead of moving to the chat immediately (3) "Domain agent
    output also apear live" (4) Domain Agent should "dynamically addopt with user prompt" (5)
    "Token streaming... must be availble for the domain agent as well, just like the requirement
    agent" plus a loader "just like the requirement agent."
    - **Root cause, part 1 (the actual correctness bug, found by reading domain_validator.py/
      agent.py/prompt.py, not guessed)**: Domain Agent was built as a strict RAG system -- its
      system prompt told the LLM "every addition must cite one of the [KB-N] knowledge chunks,"
      and `domain_validator.py`'s `_validate_citation_integrity`/`_validate_honesty_with_empty_
      retrieval` mechanically enforced it: any addition/modification whose `domain_citation`
      didn't match a real RETRIEVED chunk's source_document was rejected, and if retrieval
      returned nothing at all, ANY proposed addition/modification failed the whole plan. A
      human explicitly typing "here's our database schema: ..." is not a RAG retrieval result --
      it has no [KB-N] chunk to cite -- so the validator rejected it every time, no matter what
      the LLM tried, silently falling back to "No domain enrichment was applied to this SRS."
      This is the exact opposite of what the chat's own proactive prompt (item 41) promises
      ("do you have something specific to add -- like a database schema?").
    - **Fix, part 1**: added a second legitimate citation source, `domain_citation.source_document
      == "human_provided"`, accepted only when the call actually had a non-empty human comment
      (`human_comment_provided` threaded through `validate_plan`/the new `filter_valid_plan` --
      the LLM cannot fabricate this source when there was no real comment to ground it in). Added
      `data_requirements` as a new addition-only target_section (it already existed as a plain
      `list[str]` field on the SRS -- see `markdown_builder.py`'s own rendering of it -- with no
      per-item id, so it's the natural home for schema-shaped content that never fit any of the
      five existing FR/NFR/AC/VR/US item shapes). Both system prompts and the human-comment/
      revision-comment injection text were rewritten to explicitly instruct the LLM to incorporate
      concrete human-provided content faithfully (not paraphrase or drop it), and to write ONE
      complete addition for a single cohesive structure (a whole table's fields) rather than
      fragmenting it -- the first version of this fix got the citation/section right but the LLM
      still only added one field from a five-field schema until this instruction was added.
    - **Root cause, part 1b (found live, AFTER the citation fix, via real end-to-end testing)**:
      `domain_validator.validate_plan`'s existing all-or-nothing design meant ONE hallucinated,
      unrelated item (e.g. a modification referencing a made-up acceptance-criteria id) discarded
      the ENTIRE plan via a single raised exception -- including a separate, genuinely correct,
      human-requested schema addition sitting right next to it in the same LLM response. Observed
      directly: a real test run produced `{"additions": [database schema, ...], "modifications":
      [bad AC-003 reference]}` and the bad modification alone caused the whole thing to be thrown
      away, reproducing the user's exact complaint even after the citation logic was already
      fixed.
    - **Fix, part 1b**: new `DomainEnhancementValidator.filter_valid_plan` -- a lenient
      counterpart to the existing `validate_plan` (kept unchanged, still covered by its own
      dedicated unit tests) that checks each addition/modification INDEPENDENTLY, keeping every
      one that passes and dropping (with a logged, human-readable reason) only the ones that
      don't, instead of raising for the whole plan. `agent.py`'s `_parse_and_validate_plan`/
      `_resolve_enrichment_plan` now use this instead -- the JSON-repair retry step is now only
      reached for genuine structural failures (unparseable JSON, missing top-level keys), not
      "one item out of five had a bad reference," since that case is now handled by keeping the
      other four.
    - **Root cause, parts 2-5 (the chat UX)**: Domain Agent's chat went through `ChatPanel.jsx`'s
      GENERIC composer path -- a plain, non-streaming axios `mutateAsync` awaited to completion
      before the composer cleared (`setComment("")` ran only AFTER `await submitAgentMessage(...)`
      resolved), no live token output at all (Domain's `/domain/run`/`/domain/revise` were
      one-shot JSON endpoints, unlike Requirement Agent's real `provider.stream(...)`-backed
      endpoints), and no stop affordance wired to it.
    - **Fix, parts 2-5**: gave Domain Agent the exact same real infrastructure Requirement Agent
      already has, not a look-alike:
      - Backend: new `DomainAgent.run_stream`/`revise_stream` async generators (mirroring
        `RequirementAgent.revise_stream` exactly) using `provider.stream(...)` for the first LLM
        call, yielding `{"type": "token", "text": ...}` events for the small enrichment plan as it
        generates, then running the SAME deterministic filter/merge/save tail as `run()`/
        `revise()` (factored into the shared `_resolve_enrichment_plan` helper both streaming and
        non-streaming paths now call). New routes `POST /domain/run/stream` and
        `POST /domain/revise/stream`, identical NDJSON shape to Requirement's streaming routes.
        The old non-streaming `/domain/run`/`/domain/revise` routes are untouched for any direct
        API caller, same as Requirement's own precedent.
      - Frontend: new `useDomainAgentFlow.js` hook (mirrors `useRequirementConversationFlow.js`
        exactly -- per-call `AbortController`, `stop*Stream()` functions) shared via new
        `DomainAgentFlowContext.jsx` (mirrors `RequirementConversationFlowContext.jsx`) so
        the chat feed and the Result panel's live document view observe the same in-flight
        stream. New `DomainAgentChat.jsx` (mirrors `RequirementRevisionChat.jsx`) is now
        Domain's own dedicated chat component, replacing the generic `ChatPanel.jsx` path for
        `selectedAgent === "domain"` -- carries over the proactive prompt, "/" document mention,
        and suggestion chips that used to live inline in `ChatPanel.jsx`. The human's message
        now appears in the chat feed and the composer clears IMMEDIATELY on submit (optimistic
        `pendingHumanReply` bubble, same pattern `RequirementRevisionChat` already uses), not
        after the agent finishes. `ResultTab.jsx` gained an `isDomainGenerating` branch reusing
        the exact same `LiveGenerationView` (built-in "Connecting..." spinner, then live
        decluttered-JSON "typing" -- the loader the user asked for "just like the requirement
        agent" comes free from reusing this exact component) Requirement's own revise flow uses.
        The composer's Send button already becomes a Stop button while any stream is pending
        (item 44's mechanism), now wired to Domain's new streams too.
      - `useRunDomain`/`useReviseDomain` (the old non-streaming mutation hooks) are no longer
        imported by `ChatPanel.jsx` but were left in `useAgentMutations.js` unused rather than
        deleted, matching this repo's own established precedent (Requirement Agent's own
        non-streaming `/requirement/revise` route and hook are kept the same way).
    - **Real, live verification** (isolated backend/frontend, real LLM calls, llama3:latest):
      typed "Here's our database schema: items table has fields id, name, price, stock, quantity"
      into Domain Agent's chat and confirmed, within ~150ms of clicking Send, the composer was
      already empty and the human's message was already visible in the chat feed -- both well
      before the agent finished. Confirmed a real Stop button appeared mid-stream and, separately,
      confirmed stopping actually halts the backend (zero artifacts produced when stopped early,
      same evidence style as item 44). Let a run complete fully and inspected the resulting
      Enhanced SRS JSON directly: `data_requirements` contained the exact complete string "items
      table with fields id, name, price, stock, quantity" -- the full schema, faithfully
      incorporated, not dropped and not fragmented -- with `domain_improvements` correctly
      showing `knowledge_sources_used: [{"source_document": "human_provided", "chunks_used": 1}]`.
      Separately verified the "Just use domain knowledge" quick-action button (for a human with
      nothing specific to add) still completes a full run end-to-end and produces real artifacts.
      Backend pytest suite: 300 passed (all pre-existing `test_domain_validator.py` tests for the
      unchanged strict `validate_plan` still pass unmodified). `npm run build` clean. No frontend
      test framework exists in this repo, matching every prior item's own note. Test
      projects/features and isolated backend/frontend processes cleaned up afterward.

46. **Asking Domain Agent to remove or edit something already in the Enhanced SRS did nothing --
    a new version was generated with the requested change silently missing.** Direct user report:
    "When I prompt to remove or edit something on the enhanced SRS in the domain agent the domain
    agent did nothing and generated a new enhaced SRS verion without the edit I told to do. When
    user need to endit, remove or update on something on the enhanced SRS the user must be able
    to do it by the domain agent, just like the architect agent."
    - **Root cause**: Domain Agent's entire revision vocabulary was an "enrichment plan" --
      `additions` (new items) and `modifications` (ENRICH an existing item's description with a
      missing domain detail, per its own system prompt wording). There was no way to express
      "remove this" or "replace this outright" at all -- a fundamentally different, and
      fundamentally missing, capability. By contrast, Requirement Agent's own revise flow
      (`revision_patcher.py`, confirmed by reading it) already has exactly this: a small
      `add`/`remove`/`modify`/`set` operations list, applied deterministically by field name
      against the document. Domain Agent never had an equivalent.
    - **Fix**: reused `apply_revision_operations` directly (imported from
      `app.agents.requirement_agent.revision_patcher` -- a deliberate, documented exception to
      this file's own "other agents stay untouched" claim, since the function is generic and
      feature-independent, matches by field name against any SRS-shaped document, and has no
      Requirement-Agent-specific dependencies; reusing it avoided re-implementing ~300 lines of
      already-working, already-tested matching logic). New `DomainAgent._apply_operations_and_merge`
      applies any `operations` (remove/modify) to the current Enhanced SRS FIRST, then merges the
      enrichment plan's `additions` on top of the operation-patched result -- called from both
      `revise()` and `revise_stream()` only (not `run()`/`run_stream()`, which have no existing
      document yet to edit). Applied/unmatched edits are recorded in `domain_improvements_json`
      (`applied_edits`/`unmatched_edits`) and unmatched ones are also appended to the Enhanced
      SRS's own `assumptions` array, mirroring Requirement Agent's own "report, don't guess"
      convention exactly -- a human reviewer sees explicitly when a requested edit did NOT happen,
      instead of it silently not happening with no trace.
    - **Prompt iteration, done for real via live testing, not guessed**: the first version (three
      mechanisms -- additions/modifications/operations -- coexisting) let the model correctly
      express a `remove` on the first try, but consistently mis-routed `modify` requests through
      the OLD `modifications` shape instead of `operations`, omitting the required `value` field
      three times in a row with three different malformed shapes. Diagnosis: three overlapping
      mechanisms was too much decision surface for this size of local model
      (`llama3:latest`, temperature 0.3). Fix: collapsed the revision schema to exactly TWO
      mechanisms -- `additions` (brand-new content only) and `operations` (anything touching
      something that already exists, including "enrich this item's description," which is now
      just `action: "modify"` with the complete new text) -- with `modifications` kept in the
      returned JSON shape only as an always-empty placeholder so older parsing code never breaks.
      This single simplification fixed `modify` reliably across every retest afterward. Separately
      hardened `domain_validator.py`'s lenient per-item path (`_check_one_citation`/
      `_check_one_modification`) to auto-attribute a missing `domain_citation` to
      `"human_provided"` when a real human comment exists (rather than reject the item), and to
      accept the `operations` vocabulary's key names (`field`/`target`/`value`) as aliases for
      `modifications`' own (`target_section`/`id`/`enhanced_description`) if the model still
      confuses them -- defensive robustness, not required for the fix to work, but cheap and
      strictly safety-net.
    - **Real, live verification** (isolated backend/frontend, real LLM calls, `llama3:latest`,
      inspecting actual resulting artifacts each time, not just HTTP status codes): "Remove the
      requirement about merging guest carts (FR-DOM-001)" -> confirmed FR-DOM-001 genuinely gone
      from the next version's `functional_requirements`, with `domain_improvements.applied_edits`
      correctly recording it. "Change FR-002 to say: ..." -> confirmed FR-002's description was
      replaced with the exact new text, twice in a row. "Update NFR-001 to say response time must
      be under 1 second" -> confirmed the exact replacement, and a same-session "Remove NFR-002"
      right after that also correctly removed it. Re-verified additions (the prior item's own
      schema-incorporation fix) still work correctly after this schema simplification -- one
      retry needed out of two attempts on a fresh feature (the other failed attempt was an honest,
      correctly-reported "nothing changed" rather than a silent no-op, confirming the reliability
      ladder's own honesty guarantee held even when the underlying small local model itself
      stumbled). Finally drove a real removal request through the ACTUAL browser chat UI (not just
      curl): composer cleared immediately, the message appeared in the chat feed, a new Enhanced
      SRS version was produced, and the targeted functional requirement was genuinely gone from
      it. Backend pytest suite: 300 passed, including every pre-existing `test_domain_validator.py`
      test for the untouched strict `validate_plan` (only the new lenient per-item path changed).
      `npm run build` clean; no frontend code changes were needed for this item (the existing
      DomainAgentChat/streaming infrastructure from item 45 required zero changes -- this was a
      pure backend capability gap). No frontend test framework exists in this repo, matching every
      prior item's own note. Test projects/features and isolated backend/frontend processes
      cleaned up afterward.

47. **Follow-up to items 45/46 (same overall request, restated): "the domain agent must
    dynamically interact with the user... satisfy all user prompts/needs... just like the
    requirement agent... e.g. add a database schema."** Investigation found items 45 and 46
    together already fully deliver this -- real token-by-token streaming, immediate composer
    clear, a live loader, and working add/remove/modify via `DomainAgentChat.jsx` +
    `useDomainAgentFlow.js` + the operations-based revise backend -- so this item is a fresh,
    skeptical, full end-to-end re-verification of that combined state (not a re-implementation),
    plus one real bug it caught:
    - **Bug found**: `LiveReactionBubble` (in `RequirementConversationParts.jsx`) hardcoded the
      label `"Requirement Agent"` on its "thinking..."/streaming bubble. `DomainAgentChat.jsx`
      (item 45) reuses this exact component for its own streaming summary, so Domain Agent's
      live "thinking" bubble incorrectly read "Requirement Agent" the whole time -- confirmed via
      screenshot before the fix. Fixed by adding an `agentLabel` prop (default
      `"Requirement Agent"`, so both existing Requirement Agent call sites -- `RequirementRevisionChat.jsx`
      and `RequirementConversationChat.jsx` -- need no changes) and passing
      `agentLabel="Domain Agent"` from `DomainAgentChat.jsx`'s own call site.
    - **Real, live re-verification of the combined items 45+46+47 state**, fresh isolated
      backend/frontend, real LLM calls (`llama3:latest`), through the ACTUAL browser chat UI, one
      continuous session per flow (avoiding the documented `browser.close()`-races-an-in-flight-
      stream gotcha): typed a database schema into a fresh feature's Domain Agent chat (its first
      message, so this exercises `run_stream`) -- confirmed the composer cleared and the message
      appeared in the chat feed within ~150ms, confirmed the "thinking" bubble correctly read
      "Domain Agent" (not "Requirement Agent"), waited for real completion (polling the backend
      artifacts endpoint, not a fixed sleep), and confirmed the resulting Enhanced SRS's
      `data_requirements` contained the exact schema string
      `"cart_items table: id, cart_id, product_id, quantity, price."` -- faithfully incorporated.
      Then, on the SAME feature (now exercising `revise_stream`), typed "Remove the functional
      requirement about removing items from cart" and confirmed a new Enhanced SRS version was
      produced with that exact functional requirement genuinely gone from
      `functional_requirements`, composer again clearing immediately and the label again reading
      "Domain Agent" throughout. `npm run build` clean; backend pytest suite 300 passed. No
      frontend test framework exists in this repo, matching every prior item's own note. Test
      project/feature and isolated backend/frontend processes cleaned up afterward.

48. **Per-Project Domain Knowledge Upload + "/" Document Mention for Domain Agent -- found already
    fully implemented (backend RAG pipeline, upload service, routes, and every frontend piece)
    from earlier in this same session; this pass was real, live, skeptical end-to-end
    verification of that state, not a reimplementation, and it caught one real cosmetic bug.**
    Full design: the plan approved in plan mode this session (now superseded per this file's own
    "plan file is scratch" convention). Confirmed present and correct by reading every file the
    plan named: `rag/vector_store.py` (`get_chunks_by_document`/`delete_by_document`/`query(...,
    where=...)`), `rag/chunking.py` (`document_id`-namespaced chunk IDs), `domain_knowledge_
    service.py` (`retrieve(..., project_id=...)`'s Python-side cross-project-leak guard,
    `ingest_upload`/`get_document_chunks`/`rank_chunks_by_relevance`/`delete_document`), the new
    `knowledge_document_service.py` (upload/list/get/delete, mirroring `project_memory_service`'s
    storage convention), `knowledge_schema.py`, the `knowledge_documents` Mongo collection, `POST/
    GET/DELETE /projects/{id}/knowledge/documents` + download route, `domain_schema.py`'s
    `referenced_document_ids`, and `DomainAgent._collect_pinned_chunks`/`_retrieve_domain_
    knowledge(...)` wiring pinned chunks ahead of similarity-search chunks. Frontend: `api/
    knowledge.js`, `useKnowledgeDocuments.js`, `DomainKnowledgePanel.jsx` (wired into
    `FeatureListPanel.jsx` behind a "Domain Knowledge" modal), `DocumentMentionPicker.jsx` +
    `DomainAgentChat.jsx`'s `/`-trigger regex/mention-chip state (from item 45's dedicated Domain
    chat component -- the picker/chips slot directly into its existing composer, no separate
    integration needed).
    - **Real, live verification, no mocks**: a standalone script (no HTTP, no LLM, real Chroma +
      real `sentence-transformers` embedding) exercised `knowledge_document_service`/
      `domain_knowledge_service` directly against two real projects -- upload succeeds with a real
      non-zero `chunk_count`, `list_documents` is correctly project-scoped, **the cross-project
      leak guard holds** (a query from project B for project A's unique marker text returns zero
      of A's chunks), project A's own retrieval correctly finds its own document, `DomainAgent.
      _collect_pinned_chunks` correctly returns the pinned document's real chunk text, raw-byte
      download round-trips exactly, and delete removes the chunks (0 remain via `get_document_
      chunks` afterward). Then, in a real isolated browser session (fresh backend :8070/frontend
      :5199, real project/feature), opened the Domain Knowledge modal, uploaded a real `.txt` file
      through the actual file input, watched it reach `status: ready` via the panel's own 3s
      polling, navigated to Domain Agent's chat, typed `/returns` and confirmed the mention picker
      appeared showing the uploaded filename, clicked it, and confirmed a removable
      `returns_schema.txt ×` chip appeared above the composer with the `/returns` token correctly
      stripped from the message text -- exactly the Claude/ChatGPT-style file-mention UX the plan
      called for.
    - **Real bug found and fixed**: `DomainKnowledgePanel.jsx` mapped a knowledge document's own
      `status` (`processing`/`ready`/`failed`) onto `StatusBadge`'s `approved`/`rejected`
      vocabulary purely to reuse its green/red color styling -- but `StatusBadge`'s label text was
      hardcoded per status key, so a successfully-processed document's badge literally read
      "Approved" (and a failed one "Rejected"), falsely implying a human approval decision had
      happened to a document that was never gated at all. Fixed by giving `StatusBadge` an
      optional `label` override prop (falls back to its existing hardcoded label map when
      omitted, so every other call site in the app is unaffected) and passing "Ready"/"Failed"/
      "Processing..." from `DomainKnowledgePanel` -- confirmed via a fresh screenshot after the
      fix. **Any future reuse of `StatusBadge` for a status vocabulary that isn't actually
      pending/approved/rejected should pass its own `label`**, not rely on the approval-flavored
      default text.
    - No backend changes were needed -- the backend half of this feature was already correct as
      found. Full backend suite: 300 passed (no regressions, confirmed before starting this
      verification pass). `npm run build` clean after the `StatusBadge`/`DomainKnowledgePanel`
      fix. No frontend test framework exists in this repo, matching every prior item's own note.
    - **Loose end, not investigated further**: the throwaway verification project
      (`proj_37f06cfd`, "KB Mention Verify") could not be found via `DELETE`/`GET` immediately
      after the browser verification session ended, despite having been fully functional (upload,
      list, chat, mention picker) moments earlier through the same backend process -- no on-disk
      `outputs/kb-mention-verify/` directory existed either, so there was nothing left to clean up
      by hand. Not reproduced or root-caused (this session's isolated test backends/projects are
      always short-lived and thrown away regardless, so a project vanishing on its own before
      cleanup has zero practical impact) -- flagged here only in case a similar "a just-created
      project silently disappeared" report ever surfaces as a real, non-throwaway complaint.

49. **Domain Agent treated a human-referenced document as merely optional background, identical
    to an ordinary similarity-search hit -- so "enrichment" often looked static/generic even
    though the RAG plumbing (items 45/48) was already real. Fixed by giving referenced
    documents mandatory-incorporation treatment in the prompt, distinct from ordinary retrieval.
    Also fixed a second, real, reproduced bug: the agent's chat reply visibly disappeared for a
    beat right when a stream finished, before the persisted bubble replaced it.** Direct user
    report, three parts: (1) "the domain agent only enhanced the SRS static way... must enhance
    dynamically according to the user prompt and user select files," (2) "user must be able to
    add extra sections to the SRS explicitly... if user needs to add database schema... domain
    agent must do it," (3) "once the domain agent replies... the message disappears instantly."
    - **Root cause, parts 1-2**: confirmed by reading `_format_retrieved_chunks` (`prompt.py`) --
      every retrieved chunk, whether it came from ordinary similarity search OR from a document
      the human explicitly selected via "/" (item 48's pinned-chunk mechanism), was rendered
      identically as a generic `[KB-N]` block with no signal that one class of chunk was
      hand-picked by the human and the other wasn't. The system prompt's own "TWO legitimate
      sources" framing (retrieved chunks vs. the human's *typed* comment) never distinguished a
      referenced *file* from a generic retrieval hit -- so the model was free to judge a
      referenced document's relevance the same way it judges any KB search result, and could (and
      did, on the first repro attempt) engage with it only partially instead of treating the
      human's explicit selection as an instruction. This is the same defect class already fixed
      for *typed* human comments in item 45 (`HUMAN_PROVIDED_SOURCE`), just never extended to
      *referenced files* -- the chat's own proactive prompt invites "type / to reference an
      uploaded document," implying selection alone should carry weight, which it didn't.
    - **Fix**: `DomainAgent._collect_pinned_chunks` now tags every pinned chunk
      `referenced_by_human: True`. `prompt.py`'s `_format_retrieved_chunks` renders tagged chunks
      as a separate `[REFERENCED-N]` block (own section, "mandatory to use") ahead of ordinary
      `[KB-N]` blocks ("optional background"). Both `DOMAIN_AGENT_SYSTEM_PROMPT` and
      `DOMAIN_REVISION_SYSTEM_PROMPT` gained explicit "you MUST incorporate every [REFERENCED-N]
      chunk's relevant content, not just consider it optional" rules, plus the SAME "if it
      describes one cohesive structure, write ONE complete addition covering the whole thing"
      instruction item 45 already gave typed comments -- now applying to referenced files too.
      `build_domain_user_prompt`/`build_domain_revision_prompt` each gained a small dynamic
      reminder line (counting how many `[REFERENCED-N]` chunks are present) reinforcing the same
      point right before generation, matching this project's own established "local models respond
      better to repeated instructions" precedent. Citation format is unchanged and needed no
      validator changes -- a `[REFERENCED-N]` chunk cites with its own real
      `source_document`/`chunk_id`, exactly like a `[KB-N]` chunk already does; only `human_provided`
      remains reserved for the human's own *typed* text.
    - **Root cause, part 2's "extra sections"**: turned out to already be the exact mechanism item
      45 built -- `data_requirements` renders as its own titled `## 14. Data Requirements` Markdown
      section (confirmed by reading `markdown_builder.py`), which is precisely "an extra section
      for a database schema." The gap was never a missing schema mechanism, only that a
      *referenced file's* schema wasn't being reliably pulled in -- fixed by the same change as
      part 1.
    - **Root cause, part 3, confirmed by reading the actual mutation code**:
      `useDomainAgentFlow.js`'s `invalidateAfterCompletion` fired four `queryClient.
      invalidateQueries(...)` calls without awaiting any of them, and was a plain (non-async)
      function passed as the mutation's `onSuccess`. React Query's `mutateAsync()` only resolves
      once `onSuccess` itself resolves -- since this `onSuccess` returned `undefined` synchronously
      instead of a pending promise, `mutateAsync()` (and therefore `activeStream.isPending`
      flipping false, and `submitDomainMessage`'s `.finally(() => setPendingHumanReply(null))`)
      all fired essentially immediately, well before the invalidated queries had actually
      refetched fresh data from the backend. Net effect: the live streaming/reaction bubble and
      the optimistic "You" bubble both vanished the instant the stream's `"done"` event landed,
      but the real persisted bubbles (which only exist once the refetched `events`/`artifacts`
      queries land in the cache) hadn't appeared yet -- a real, reproducible empty-frame gap,
      exactly the reported "message disappears instantly."
    - **Fix**: made `invalidateAfterCompletion` `async` and awaited every `invalidateQueries(...)`
      call via `Promise.all([...])` -- `mutateAsync()` (and thus the live bubbles' teardown) now
      genuinely waits until the fresh timeline data has landed in the query cache before
      resolving, making the live-bubble-to-persisted-bubble handoff seamless. **The identical
      unawaited pattern was found in two more places sharing the same root cause** (not reported
      for these, but the same bug class, fixed for consistency and cheap to fix safely):
      `useRequirementConversationFlow.js`'s `confirmStream`/`reviseStream` `onSuccess` handlers
      (Requirement Agent's post-SRS revise chat -- `RequirementRevisionChat.jsx` mirrors
      `DomainAgentChat.jsx`'s exact bubble-teardown pattern, so it had the exact same race), and
      `useAgentMutations.js`'s shared `useAgentMutation` factory (used by Architecture/UI-UX/Coder
      Agent's plain, non-streaming chats -- same "pending flips false right as onSuccess starts"
      mechanism, same fix).
    - **Real, live verification, no mocks, through the actual browser chat UI** (isolated
      backend/frontend, real Ollama calls -- temporarily switched Domain Agent's live per-agent
      LLM override from `qwen3-coder:latest`, discovered mid-verification to be genuinely slow on
      this machine's GPU per the already-documented gotcha, to `llama3:latest` for the duration of
      this pass only, then restored it back to `qwen3-coder:latest` exactly afterward -- this is
      real, persisted, shared configuration in the live Atlas cluster, not test-local state, so it
      was put back rather than left changed):
      - Message-disappear fix: submitted a real Domain Agent message, watched a genuine Stop
        button appear then disappear as the real stream completed, and screenshotted the exact
        next frame after completion -- the real "Domain Agent: Produced Enhanced SRS, Domain
        Improvements (v1)" bubble was already visible with zero empty gap, confirmed both visually
        and via `page.inner_text` (no "No activity yet" flash, "Produced" present immediately).
      - Dynamic/referenced-file enrichment fix: uploaded a real knowledge document (a
        `return_reasons` lookup table schema: `id`, `code`, `display_label`,
        `requires_photo_evidence`, `refund_eligible`) to a fresh project, referenced it via "/" in
        Domain Agent's chat with only a generic, non-copy-pasted instruction ("Please enrich the
        SRS using [the referenced file]") -- the resulting Enhanced SRS's `domain_improvements`
        correctly cited `return_reasons_schema.txt` by its real `chunk_id` (not a generic KB hit,
        not "human_provided") and added a genuinely content-derived enrichment (a `reason_id`
        foreign-key requirement + a status-enum acceptance-criteria modification), both explicitly
        reasoned from "[REFERENCED-1]" in the model's own rationale text -- concrete evidence the
        model now treats a referenced file differently from background retrieval, not the
        pre-fix generic/static behavior. A follow-up revision request ("add the full
        return_reasons lookup table... including every field in that document," again without
        retyping the schema, just re-referencing the same file) produced a `data_requirements`
        entry that was an EXACT, complete match to the uploaded file's full 5-field schema --
        confirming both the mandatory-incorporation fix and the pre-existing "one complete
        addition per cohesive structure" instruction now correctly extend to referenced files, not
        just typed comments.
    - Full backend suite: **300 passed** (`tests/test_domain_validator.py`/
      `test_domain_agent_fallback.py` specifically re-run first, all still passing unmodified --
      this change only touched prompt text and chunk tagging/formatting, no validator logic).
      `npm run build` clean. No new backend unit tests were added for the prompt-wording change
      itself (there is no automated way to assert an LLM "treats X as mandatory" -- this was
      verified live, against a real model, matching this project's established practice for
      prompt-quality changes). No frontend test framework exists in this repo, matching every
      prior item's own note.
    - **A real, reachable bug found ALONG THE WAY during this verification's own test setup, NOT
      part of this fix and NOT fixed here (recorded honestly rather than silently left for a
      future session to rediscover)**: `approval_service.py`'s SRS-exclusivity rule (item 37) reverts
      every OTHER `srs`-type artifact currently `APPROVED` back to `pending` when a new one is
      approved -- scoped by `artifact_type` alone, with **no format awareness**. Since every SRS
      version is saved as a JSON+Markdown *pair* sharing one version (this project's own
      long-established convention -- see item 34's cascade-delete fix for the first time this
      exact pairing caused a bug), approving the JSON half of a version, after its Markdown
      sibling was already separately approved, silently reverts that Markdown sibling back to
      "pending" -- confirmed directly and reproducibly in this session (approved `srs` markdown
      v1, then `srs` json v1; the markdown flipped back to pending the instant the json was
      approved). **This is reachable through the normal UI, not just direct API calls**: item 40's
      own fix made every pending/rejected version of every artifact_type independently
      approvable, including a gating type's Markdown row, which previously had no path to
      independent approval at all. Likely low real-world impact today, since the frontend's own
      approve flow (`ResultTab.jsx`'s `requestSrsApproveConfirmation`) always targets the row the
      UI shows (typically the JSON representative, per `dedupeArtifactVersions`' format
      preference) rather than a human manually approving the Markdown row on its own -- but a
      human who *does* explicitly approve a Markdown row first, then approves its JSON sibling
      (or vice versa), will see the first one silently un-approve. Worth a future fix (the
      cleanest one: scope the exclusivity revert to same-`artifact_format`-siblings the same way
      item 34's `delete_artifact` already treats a JSON+Markdown pair as one logical version) --
      not fixed here, since it's unrelated to what this item's user report asked for.

50. **Domain Agent could structurally only enrich 6 of the SRS's ~18 sections (in practice
    converging on non_functional_requirements/acceptance_criteria almost every run) -- fixed by
    genuinely widening what it's allowed to touch, not just prompting it to try harder. Also
    added inline, color-coded highlighting for domain-added content across every section, not
    just the original 4.** Direct user report: "the domain agent only improves the Nonfunctional
    requirement section and the acceptance criteria section... must enrich the entire SRS
    dynamically instead of static... must display the domain improvements separately... highlight
    and use separate colour codes for domain agent improvements."
    - **Root cause, confirmed by reading the actual schema, not assumed**:
      `domain_validator.py`'s `ADDITION_TARGET_SECTIONS` was hard-capped at the 5 ID-tagged
      sections (FR/NFR/AC/VR/US) plus `data_requirements` -- `scope`, `out_of_scope`,
      `constraints`, `risks`, `dependencies`, `assumptions`, `user_roles`, `api_expectations`,
      `ui_expectations`, `input_requirements`, `output_requirements` were **structurally
      impossible** targets for an "addition," rejected by the validator regardless of what the
      retrieved knowledge supported. The system prompt's own "Never touch project/feature-level
      fields (business_goal, scope, constraints, etc.)" line made this a deliberate original
      design choice, not an oversight -- but it meant the model's only real creative freedom
      narrowed down to NFR/AC in practice (the two sections that read most naturally as "domain
      knowledge" without a schema/citation to hang off of), exactly matching the reported
      complaint. This was a real schema restriction, not a model preference the prompt could
      talk its way around.
    - **Fix, backend**: `domain_validator.py` gained `PLAIN_LIST_SECTIONS` (the 11 sections
      above -- deliberately matching `DOMAIN_REVISION_SYSTEM_PROMPT`'s pre-existing "operations"
      field list, which could already reach every one of these via remove/modify; only
      "additions," shared by both initial generation and revision, was missing them) and
      `ADDITION_ONLY_SECTIONS = [data_requirements] + PLAIN_LIST_SECTIONS` --
      `ADDITION_TARGET_SECTIONS` now includes all of them, addition-only (like data_requirements,
      none have a per-item id to modify; `_validate_modifications`/`_check_one_modification`
      reject a modification targeting any of them with the same "propose an addition instead"
      message data_requirements already had). `agent.py`'s `_apply_enrichment_plan` generalized
      its data_requirements-only special case to `if target_section in ADDITION_ONLY_SECTIONS`,
      appending the description to whichever plain list[str] field the LLM targeted -- one code
      path for all 12 addition-only sections instead of one hardcoded to `data_requirements`.
    - **Fix, prompt**: `DOMAIN_AGENT_SYSTEM_PROMPT` and `DOMAIN_REVISION_SYSTEM_PROMPT` both gained
      an explicit "do NOT default to only non_functional_requirements/acceptance_criteria --
      actively check EVERY section against the retrieved knowledge, only propose what the content
      genuinely supports, never pad a section just to appear thorough" rule, plus per-section
      guidance on what kind of domain fact fits each new target (a compliance rule -> constraints,
      a known failure mode -> risks, a third-party service -> dependencies, an exact
      endpoint/auth expectation -> api_expectations, etc.). The old blanket "never touch
      project/feature-level fields" line was replaced with a short, explicit exclusion list
      (business_goal, feature_name, project_type, target_stack, architectural_style,
      traceability, domain_enrichment_metadata -- identity/system-managed fields only); everything
      else is now a legitimate target.
    - **Fix, "display domain improvements separately"**: already existed from item 42 (the
      `domain_improvements` artifact is excluded from the approvable artifact list and rendered
      as a read-only attachment directly under the Enhanced SRS) -- confirmed still correct,
      unchanged by this item.
    - **Fix, "highlight with separate color codes"**: `EnrichedItemList`/`SrsDocumentViewer`
      already did this for FR/NFR/AC/VR (green="Added by Domain Agent", blue="Enhanced by Domain
      Agent") -- but two real gaps were found reading the actual component: `user_stories` was
      missing from `ENRICHABLE_SECTIONS` entirely (Domain Agent could already add to it per
      `SECTION_PREFIX_MAP`, just never got the highlight treatment), and every plain-list section
      (including the pre-existing `data_requirements`) had **no highlighting mechanism at all**,
      since a plain string can't carry its own `origin`/`modified_by_domain_agent` flag the way an
      FR/NFR/AC/VR/US dict item can. Fixed: `user_stories` added to `ENRICHABLE_SECTIONS`. New
      `EnrichedPlainList.jsx` (same green "Added by Domain Agent" card + citation convention as
      `EnrichedItemList`, addition-only -- a plain-list section has no "modified" concept since
      there's no original text left to diff against once a string is edited in place) renders any
      of the 12 addition-only plain-list sections; a domain-added entry is identified by **exact
      text match** against the sibling Domain Improvements artifact's own recorded
      `additions[].description` for that `target_section` (new `buildHighlightedTextsBySection`
      helper in `SrsDocumentViewer.jsx`) -- no SRS schema change needed, since
      `domain_improvements_json` already records exactly this. `ArtifactContentView.jsx` gained an
      optional `domainImprovementsArtifact` prop (fetches its content via the same
      `useArtifactContent` hook, React-Query-cached so no extra network cost since `ResultTab.jsx`
      already fetches this same artifact for its own separate "Domain Improvements" attachment
      below) and passes it into `SrsDocumentViewer` as `domainImprovements`; `ResultTab.jsx`'s one
      call site updated. Also mirrored the same tagging into the Markdown output for symmetry
      (`markdown_builder.py`'s `_simple_list` gained an optional `highlighted_texts` set param,
      prefixing a matched plain-list entry with `**[DOMAIN ADDED]**`, computed once per `build()`
      call from `domain_improvements_json`'s own additions) -- the downloaded/rendered Markdown
      report now shows the same distinction the JSON-driven React view does, not just one of the
      two.
    - **Known, honest scope limit**: the artifact-viewer **popup** (`ArtifactViewerModal.jsx`,
      reached via a "View" link anywhere outside the main Result panel) does not currently look up
      sibling artifacts, so it renders an Enhanced SRS without the inline highlighting -- falls
      back to the exact same plain rendering as before this item (no regression, just missing the
      enhancement there). The **primary** reading surface (`ResultTab.jsx`'s inline document view,
      the same place a human actually reviews and approves the Enhanced SRS) has it. Threading
      sibling-lookup into the popup path would need `allArtifacts` plumbed into
      `WorkspaceSelectionContext`, out of this item's scope.
    - **Real, live verification, no mocks, through the actual API and browser** (isolated
      backend/frontend, temporarily switched Domain Agent's live per-agent LLM override to
      `llama3:latest` for the duration of this pass only -- same real, persisted, shared Atlas
      configuration as item 49, restored to `qwen3-coder:latest` exactly afterward): created a
      fresh "Payment Processing" feature specifically to exercise the payment/PCI seed knowledge
      base. A broad enrichment request ("cover requirements, constraints, risks, and dependencies,
      not just non-functional requirements") produced additions in `functional_requirements` AND
      `data_requirements` -- **zero** in NFR/AC this run, a complete reversal of the reported
      bias, direct evidence the schema is no longer the bottleneck (the model's per-run section
      choice is a separate, harder "which sections does retrieved content actually support"
      question this fix doesn't and can't fully control, honestly noted rather than overclaimed).
      A second, targeted revision request ("add a constraints entry: must comply with PCI DSS and
      never store raw card numbers") -- after one real, unrelated JSON-parse fallback on the first
      attempt (the pre-existing reliability ladder correctly caught it and preserved the document
      unchanged, confirmed via `fallback_used: true` in the resulting metadata; not a regression,
      the same ladder every Domain Agent call already has) -- succeeded on retry: the new
      `constraints` entry was confirmed present, verbatim, in the real Enhanced SRS JSON. A real
      browser screenshot of the Result panel's Constraints section shows the exact PCI DSS text in
      a green card with an "ADDED BY DOMAIN AGENT" badge and "Source: human_provided" citation,
      while the adjacent, untouched Risks/Dependencies entries (original Requirement Agent
      content) correctly render as plain, unhighlighted bullets right below it in the same
      screenshot -- direct visual proof of both the enrichment breadth fix and the highlighting
      fix working together, with no false-positive highlighting.
    - Full backend suite: **300 passed** (`tests/test_domain_validator.py`/
      `test_domain_agent_fallback.py`/`test_domain_markdown_builder.py` specifically re-run first,
      all still passing unmodified by this schema-expansion change). `npm run build` clean. No new
      backend unit tests added for the prompt-wording change itself (same reasoning as item 49 --
      "does the model actually diversify" is a live-verification question, not a unit-testable
      one); the deterministic schema/merge/markdown changes (`ADDITION_ONLY_SECTIONS`,
      `_apply_enrichment_plan`'s generalized branch, `_simple_list`'s highlighting) are exactly
      the kind of logic this project's existing tests already cover structurally and continued to
      pass unmodified. No frontend test framework exists in this repo, matching every prior item's
      own note.

## Where to look

- Full build spec (read this first, in order, before any new milestone): `instructions .md`
- This file: durable cross-milestone memory, updated at the end of each milestone
- `C:\Users\ASUS\.claude\plans\soft-petting-star.md`: scratch, current-milestone-only plan
