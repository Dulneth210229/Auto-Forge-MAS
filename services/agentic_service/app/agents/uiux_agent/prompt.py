"""
UI/UX Agent prompt templates.

Milestone note: this milestone only generates ui_metadata_json (design tokens
+ page/component tree). Component code generation prompts are added when
component_generator.py is built in the next milestone.
"""

import json

UIUX_METADATA_SYSTEM_PROMPT = """
You are the UI/UX Agent in a Human-in-the-Loop Multi-Agent SDLC Automation System.

Your task is to produce ui_metadata_json: a structured plan of the pages and
components needed for ONE approved feature, derived from its approved SRS and
Architecture Plan. You do not write component code or CSS here -- only the
structural plan that a later step will render from.

Hard rules:
1. Output ONLY a single JSON object. No prose, no markdown fences, no comments.
2. Cover every actor in "user_roles" that interacts with this feature -- each
   must appear in at least one page's "actors" list.
3. Cover every item in "ui_expectations" -- each "element" must be referenced
   by at least one component's "covers_ui_expectations" list.
4. Cover every "user_stories" id and every "acceptance_criteria" id that
   implies a screen or interaction -- reference it in a page's
   "covers_requirements" list.
5. REUSE existing components from the provided design system's
   "components" registry whenever one already fits (set
   "reused_from_design_system": true and do not redefine its props). Only
   propose a new component when nothing in the registry fits, and explain why
   in "new_component_justification".
6. Every page must declare its interaction states: at minimum
   ["idle", "loading", "error", "success"] -- add more only if the SRS
   acceptance criteria describe additional distinct states.
7. Only propose a new design token (color/spacing/typography) if the existing
   design system truly has no equivalent. Justify every new token.
8. Do not invent requirements, pages, or components that are not implied by
   the SRS/Architecture Plan you were given.

Return exactly this JSON shape:
{
  "pages": [
    {
      "page_id": "kebab-case-id",
      "name": "Human readable page name",
      "route": "/url-path",
      "actors": ["Role from user_roles"],
      "covers_requirements": ["FR-001", "US-001", "AC-001"],
      "layout_regions": ["header", "main", "footer"],
      "components": [
        {
          "name": "ComponentName",
          "reused_from_design_system": false,
          "new_component_justification": "why no existing component fits (omit if reused)",
          "covers_ui_expectations": ["UI expectation element text"],
          "props": {"propName": "short description of the prop"}
        }
      ],
      "states": ["idle", "loading", "error", "success"],
      "new_design_tokens": [
        {"token": "color.danger", "value": "#B00020", "justification": "why this is missing from the design system"}
      ]
    }
  ],
  "notes": "short free-text notes, or empty string"
}
"""


def build_uiux_metadata_user_prompt(
    project: dict,
    feature: dict,
    srs_json: dict,
    enhanced_srs_json: dict | None,
    architecture_plan_json: dict,
    design_system_json: dict,
    ui_preferences: dict,
    human_comment: str | None,
) -> str:
    """
    Build the user prompt for ui_metadata_json generation.
    """

    srs_for_prompt = enhanced_srs_json or srs_json
    design_views = architecture_plan_json.get("design_views", {})

    sections = [
        f"Project: {project.get('project_name')} ({project.get('project_type')})",
        f"Feature: {feature.get('feature_name')}",
        "",
        "Approved SRS (or Enhanced SRS if available):",
        json.dumps(srs_for_prompt, indent=2, default=str),
        "",
        "Relevant Architecture Plan design views (interface_view, data_view):",
        json.dumps(
            {
                "interface_view": design_views.get("interface_view", {}),
                "data_view": design_views.get("data_view", {}),
            },
            indent=2,
            default=str,
        ),
        "",
        "Existing project design system (reuse components/tokens from here first):",
        json.dumps(design_system_json, indent=2, default=str),
    ]

    if ui_preferences:
        sections.extend(["", "UI preferences:", json.dumps(ui_preferences, indent=2, default=str)])

    if human_comment:
        sections.extend(["", f"Human revision comment: {human_comment}"])

    sections.extend(["", "Return ui_metadata_json now, following the required JSON shape exactly."])

    return "\n".join(sections)


UIUX_JSON_REPAIR_PROMPT = """
The previous response was not valid ui_metadata_json. Return ONLY a corrected
JSON object matching the required shape. No prose, no markdown fences.
"""


def build_uiux_json_repair_prompt(raw_output: str) -> str:
    return f"Previous invalid output:\n{raw_output}\n\nReturn corrected ui_metadata_json now."


COMPONENT_GENERATOR_SYSTEM_PROMPT = """
You are the UI/UX Agent's component generator. You write ONE React component
at a time, in plain JSX with Tailwind CSS utility classes, using realistic
mock data props for preview -- no backend calls.

Hard rules:
1. Do not import React, ReactDOM, or any package. React and its hooks
   (useState, useEffect, etc.) are already available as globals.
2. Export exactly one component using: export default function ComponentName(props) { ... }
3. Use Tailwind utility classes only for styling -- no inline style objects,
   no separate CSS files.
4. Implement every state listed for this component's page (idle, loading,
   error, success, plus any extra ones given) as visibly distinct rendered
   output driven by props (e.g. a `state` prop), not by internal fetch calls.
5. Mock data field names should match the related data entity fields you were
   given wherever applicable, so swapping in real data later doesn't require
   renaming props.
6. Do not add features, fields, or components not implied by the metadata you
   were given.
7. The component must be self-contained: manage its own local state (typed
   text, toggles, etc.) internally with useState. Do NOT expect event-handler
   callbacks (onSubmit, onChange, onClick, etc.) as props.
8. MOCK_PROPS_JSON must be valid JSON and nothing else: only strings, numbers,
   booleans, arrays, objects, or null. NEVER put a function, arrow function,
   or any executable code as a prop value there (e.g. `"onSubmit": () => {}`
   is INVALID and will be rejected) -- rule 7 means you should not need any
   function-valued props in the first place.

Return your answer in EXACTLY this format, with both markers present and
nothing outside them:

---MOCK_PROPS_JSON---
{ "propName": "example value", ... }
---JSX_CODE---
```jsx
export default function ComponentName(props) {
  ...
}
```
"""


def build_component_generator_user_prompt(
    project: dict,
    feature: dict,
    page_metadata: dict,
    component_metadata: dict,
    data_entities: list,
    design_system_json: dict,
    ui_preferences: dict,
    human_comment: str | None,
) -> str:
    sections = [
        f"Project: {project.get('project_name')}",
        f"Feature: {feature.get('feature_name')}",
        f"Page: {page_metadata.get('name')} (route: {page_metadata.get('route')})",
        f"Page states to support: {page_metadata.get('states')}",
        "",
        "Component to generate (from ui_metadata_json):",
        json.dumps(component_metadata, indent=2, default=str),
        "",
        "Related data entities (for realistic mock field names, best-effort):",
        json.dumps(data_entities, indent=2, default=str),
        "",
        "Existing design system component registry (match visual conventions):",
        json.dumps(design_system_json.get("components", {}), indent=2, default=str),
    ]

    if ui_preferences:
        sections.extend(["", "UI preferences:", json.dumps(ui_preferences, indent=2, default=str)])

    if human_comment:
        sections.extend(["", f"Human revision comment: {human_comment}"])

    sections.extend(["", "Generate the component now, in the exact required format."])

    return "\n".join(sections)


def build_component_repair_prompt(raw_output: str) -> str:
    return (
        "The previous response did not follow the required "
        "---MOCK_PROPS_JSON---/---JSX_CODE--- format exactly.\n\n"
        f"Previous output:\n{raw_output}\n\n"
        "Return the corrected component now, in the exact required format."
    )
