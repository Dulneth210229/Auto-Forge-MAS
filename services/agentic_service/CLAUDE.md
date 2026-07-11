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

## Where to look

- Full build spec (read this first, in order, before any new milestone): `instructions .md`
- This file: durable cross-milestone memory, updated at the end of each milestone
- `C:\Users\ASUS\.claude\plans\soft-petting-star.md`: scratch, current-milestone-only plan
