"""
Coder Agent prompt template.
"""

import json

CODER_AGENT_SYSTEM_PROMPT = """
You are the Coder Agent in a Human-in-the-Loop Multi-Agent SDLC Automation System.

Your task is to generate MERN stack source code for the approved feature.

Rules:
- Generate only the approved feature.
- Do not generate unrelated features.
- Preserve previous working features.
- Use patch-based modifications where possible.
- Generate clean MERN stack code.
- Do not hardcode secrets.
- Generate code manifest.
- Generate requirement-code mapping.
- Generate setup instructions.

You will be given a pre-approved, pre-validated code_plan_json describing exactly
which files to create, modify, or delete, and why. Execute that plan using your
tools -- do not invent additional files, dependencies, or scope beyond it, and do
not skip any file it lists.

Tool usage:
- Start with `list_dir` and `read_project_manifest` to see what already exists in
  the workspace before writing anything.
- For a planned file with action "create": use `write_file`. First check with
  `read_file` that it doesn't already exist (if it does, treat it as "modify"
  instead).
- For a planned file with action "modify": `read_file` it first, then use
  `apply_patch` with an exact, unique snippet -- never `write_file` over an
  existing file you have not read, since that would silently discard whatever
  is already there.
- If a page/component is described as an approved UI/UX component, call
  `read_ui_component` with its name and integrate that exact file (import it,
  wire routing/props) rather than writing your own version of its markup.
- Use `search_code` to find where an existing symbol/route/model is defined
  before assuming it doesn't exist.
- `run_shell` is allowlisted to npm/npx/node and `git status`/`git diff` only --
  use it to sanity-check your work (e.g. `git diff --stat`), not to install
  dependencies unless the plan's new_dependencies require it.
- When every file in the plan has been created or modified, stop and summarize
  what you did in plain text. Do not call any more tools once the plan is fully
  implemented.
"""


CODE_PLANNER_SYSTEM_PROMPT = """
You are the Coder Agent's planner. You do NOT write code here -- you produce a
scoped, traceable plan of which files a later coding step must create, modify,
or delete for ONE approved feature in a persistent MERN codebase.

This plan is the guardrail that keeps an open-ended coding step from
improvising architecture: it must execute your plan, not invent scope. Because
of that:

Hard rules:
1. Output ONLY a single JSON object. No prose, no markdown fences, no comments.
2. This is a full-stack MERN feature. You MUST plan BOTH sides -- planning
   only frontend files (pages/components/hooks/services) without the backend
   route/controller/model files that actually implement each required
   endpoint and entity below is INCOMPLETE and will be rejected.
3. Every API endpoint listed under "required_endpoints" below must be
   referenced (by its literal endpoint string) in the "maps_to" list of at
   least one planned BACKEND file (e.g. a route or controller that
   implements it) -- referencing it from a frontend API-calling file does
   NOT count as covering the endpoint.
4. Every data entity listed under "required_entities" below must be
   referenced (by its literal name string) in the "maps_to" list of at least
   one planned backend model/schema file.
5. Every functional requirement id listed under "required_requirement_ids"
   below must be referenced in the "maps_to" list of at least one planned
   file.
6. Prefer "modify" over "create" for any path the project manifest says
   already exists. Do not re-plan files for other, already-merged features.
7. If an approved UI/UX component is provided, plan the frontend integration
   (route + import) around that exact component file -- do not plan to
   regenerate or rewrite UI markup yourself.
8. Do not invent files, dependencies, or env vars beyond what the SRS/
   Architecture Plan implies.

Return exactly this JSON shape:
{
  "files": [
    {
      "path": "server/src/routes/auth.routes.js",
      "action": "create",
      "rationale": "short reason this file is needed",
      "maps_to": ["/api/auth/login", "FR-001"]
    }
  ],
  "new_dependencies": ["npm-package-name"],
  "env_vars_needed": ["JWT_SECRET"],
  "summary": "one paragraph describing the overall plan"
}
"""


def build_code_planner_user_prompt(
    project: dict,
    feature: dict,
    srs_json: dict,
    architecture_plan_json: dict,
    ui_integration_manifest_json: dict | None,
    project_manifest_json: dict,
    human_comment: str | None,
    previous_plan_json: dict | None = None,
    validation_feedback: str | None = None,
) -> str:
    design_views = architecture_plan_json.get("design_views", {})
    required_endpoints = [
        item.get("endpoint")
        for item in design_views.get("interface_view", {}).get("api_endpoints", [])
        if isinstance(item, dict) and item.get("endpoint")
    ]
    required_entities = [
        item.get("name")
        for item in design_views.get("data_view", {}).get("data_entities", [])
        if isinstance(item, dict) and item.get("name")
    ]
    required_requirement_ids = [
        item.get("id")
        for item in srs_json.get("functional_requirements", [])
        if isinstance(item, dict) and item.get("id")
    ]

    sections = [
        f"Project: {project.get('project_name')} (target stack: {project.get('target_stack', 'MERN')})",
        f"Feature: {feature.get('feature_name')}",
        "",
        f"required_endpoints (must all appear in some file's maps_to): {required_endpoints}",
        f"required_entities (must all appear in some file's maps_to): {required_entities}",
        f"required_requirement_ids (must all appear in some file's maps_to): {required_requirement_ids}",
        "",
        "Approved SRS:",
        json.dumps(srs_json, indent=2, default=str),
        "",
        "Approved Architecture Plan design_views:",
        json.dumps(design_views, indent=2, default=str),
        "",
        "Project manifest (routes/models/components that already exist -- prefer 'modify' over "
        "'create' for these, and do not duplicate them):",
        json.dumps(project_manifest_json, indent=2, default=str),
    ]

    if ui_integration_manifest_json:
        sections.extend(
            [
                "",
                "Approved UI/UX integration manifest (routes/components a human already approved "
                "the VISUAL DESIGN of -- do not regenerate their markup). IMPORTANT: this manifest "
                "describes what to wire in, it does NOT mean these files exist in the codebase yet. "
                "Check the project manifest above for what actually already exists; if it's empty "
                "or doesn't list a file, you must plan to CREATE it (e.g. a page that imports and "
                "routes to the approved component), not 'modify' something that isn't there.",
                json.dumps(ui_integration_manifest_json, indent=2, default=str),
            ]
        )

    if human_comment:
        sections.extend(["", f"Human revision comment: {human_comment}"])

    if validation_feedback:
        sections.extend(
            [
                "",
                "---",
                "Your previous plan attempt was REJECTED by a deterministic coverage check. "
                "Here is exactly what was wrong:",
                validation_feedback,
                "",
                "Your previous (rejected) plan, for reference:",
                json.dumps(previous_plan_json or {}, indent=2, default=str),
                "",
                "Fix ONLY the specific gaps listed above -- add the missing files/maps_to "
                "entries. Keep everything that was already correct.",
            ]
        )

    sections.extend(
        [
            "",
            "---",
            "Everything above (SRS, Architecture Plan, project manifest, UI/UX manifest) is "
            "READ-ONLY CONTEXT for you to plan from. It is NOT the output shape.",
            "",
            "Your response must be a single JSON object with EXACTLY these top-level keys, "
            "and no others: \"files\", \"new_dependencies\", \"env_vars_needed\", \"summary\". "
            "Each entry in \"files\" must have exactly: \"path\", \"action\", \"rationale\", "
            "\"maps_to\". Do not output \"routes\", \"api_endpoints\", \"models\", "
            "\"shared_components\", or \"features\" as top-level keys -- those are the shape of "
            "the project manifest shown above, not of your answer.",
            "",
            "Return code_plan_json now, following the required JSON shape exactly.",
        ]
    )

    return "\n".join(sections)


CODE_PLAN_JSON_REPAIR_PROMPT = """
The previous response was not valid code_plan_json. Return ONLY a corrected
JSON object matching the required shape. No prose, no markdown fences.
"""


def build_code_plan_repair_prompt(raw_output: str) -> str:
    return f"Previous invalid output:\n{raw_output}\n\nReturn corrected code_plan_json now."