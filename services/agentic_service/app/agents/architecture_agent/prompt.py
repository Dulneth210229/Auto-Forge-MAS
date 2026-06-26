# """
# Architecture Agent prompt.

# This file contains only Architecture Agent prompts.

# Important rules:
# - Generate architecture only for the given feature.
# - Do not design unrelated features.
# - LLM generates JSON only.
# - Backend converts SDS JSON into Markdown.
# - Backend converts usecase_json into PlantUML.
# - No API contract is generated.
# - No OpenAPI YAML is generated.
# - No code is generated.
# - No UI is generated.
# """

# ARCHITECTURE_AGENT_SYSTEM_PROMPT = """
# You are the Architecture Agent in AutoForge.

# Your task:
# Generate Software Design Specification JSON and Use Case Diagram JSON
# for exactly one approved feature.

# Strict rules:
# - Return only valid JSON.
# - Do not return Markdown.
# - Do not return code fences.
# - Do not return explanation outside JSON.
# - Do not generate source code.
# - Do not generate UI design.
# - Do not generate API contract.
# - Do not generate OpenAPI YAML.
# - Do not generate component diagrams.
# - Do not generate class diagrams.
# - Do not generate sequence diagrams.
# - Generate architecture only for the given feature, not the full project.
# - Keep the design practical for MERN stack implementation.
# - Reference requirement IDs from the approved SRS wherever possible.
# - Preserve the selected architecture style from requirements.

# The JSON must have exactly this top-level structure:

# {
#   "sds_json": {
#     "project_id": "",
#     "project_name": "",
#     "project_type": "",
#     "feature_id": "",
#     "feature_name": "",
#     "target_stack": "",
#     "architecture_style": "",
#     "feature_design_overview": "",
#     "frontend_responsibilities": [],
#     "backend_responsibilities": [],
#     "database_design": {
#       "collections": [],
#       "data_notes": []
#     },
#     "api_design_summary": [
#       {
#         "endpoint": "",
#         "method": "",
#         "purpose": "",
#         "related_requirements": []
#       }
#     ],
#     "data_flow": [],
#     "error_handling_design": [],
#     "authentication_authorization_design": [],
#     "folder_structure_suggestion": [],
#     "dependency_list": [],
#     "integration_with_previous_features": [],
#     "scalability_notes": [],
#     "assumptions": [],
#     "constraints": [],
#     "traceability": [
#       {
#         "requirement_id": "",
#         "sds_section": "",
#         "design_decision": ""
#       }
#     ]
#   },
#   "usecase_json": {
#     "system_boundary": "",
#     "diagram_title": "",
#     "actors": [
#       {
#         "id": "ACT-001",
#         "name": "",
#         "type": "primary",
#         "description": ""
#       }
#     ],
#     "use_cases": [
#       {
#         "id": "UC-001",
#         "name": "",
#         "description": "",
#         "related_requirements": []
#       }
#     ],
#     "relationships": [
#       {
#         "from": "ACT-001",
#         "to": "UC-001",
#         "type": "association",
#         "label": ""
#       }
#     ],
#     "standards_notes": []
#   }
# }

# Use Case Diagram Standards:
# - Actor names must be roles, not system components.
# - Use case names must be user-goal actions, usually verb phrases.
# - The diagram must have a clear system boundary.
# - Use association for actor-to-use-case communication.
# - Use <<include>> only for mandatory reusable behavior.
# - Use <<extend>> only for optional or conditional behavior.
# - Use generalization only for true is-a relationships.
# - Do not show database tables, controllers, APIs, or UI components as actors.
# - Do not include unrelated features outside this feature scope.
# """


# JSON_REPAIR_PROMPT = """
# You are a JSON repair assistant.

# The given output should be valid JSON but may be malformed.

# Fix it and return only valid JSON.

# Rules:
# - Do not add Markdown.
# - Do not add explanation.
# - Do not add comments.
# - Preserve original meaning as much as possible.
# """


# def build_architecture_user_prompt(
#     project: dict,
#     feature: dict,
#     srs_json: dict,
#     enhanced_srs_json: dict | None = None,
#     architecture_notes: str | None = None,
#     human_comment: str | None = None
# ) -> str:
#     """
#     Build Architecture Agent user prompt.

#     project:
#         Project metadata.

#     feature:
#         Feature metadata.

#     srs_json:
#         Approved Requirement Agent SRS JSON.

#     enhanced_srs_json:
#         Approved Domain Agent Enhanced SRS JSON if available.

#     architecture_notes:
#         Optional user instruction about architecture.

#     human_comment:
#         Optional human comment.
#     """

#     enhanced_text = "No approved Enhanced SRS is available."

#     if enhanced_srs_json:
#         enhanced_text = str(enhanced_srs_json)

#     return f"""
# Generate SDS JSON and Use Case Diagram JSON for this feature only.

# Project:
# {project}

# Feature:
# {feature}

# Approved SRS JSON:
# {srs_json}

# Approved Enhanced SRS JSON if available:
# {enhanced_text}

# Architecture Notes:
# {architecture_notes}

# Human Comment:
# {human_comment}

# Remember:
# - Generate only SDS JSON and usecase_json.
# - Do not generate API contract.
# - Do not generate OpenAPI YAML.
# - Do not generate code.
# - Do not generate UI.
# - Do not design unrelated features.
# - Keep the output practical for MERN stack.
# - Return only valid JSON.
# """


# def build_json_repair_prompt(raw_output: str) -> str:
#     """
#     Build prompt to repair invalid JSON.
#     """

#     return f"""
# Repair this malformed JSON and return only valid JSON:

# {raw_output}
# """


"""
Architecture Agent prompt.

This file contains only Architecture Agent prompts.

Main design:
- LLM generates JSON only.
- Backend converts SDS JSON into Markdown.
- Backend converts usecase_json into PlantUML.
- Backend validates usecase_json before saving.

Important:
The user requested:
- No API contract.
- No OpenAPI YAML.
- SDS and use case diagram only.
- Use case diagram must align with SRS, SDS, and user requirements.
"""

import json

def safe_json_dumps(data: dict) -> str:
    """
    Convert Python dictionary into JSON string safely.

    Why:
    MongoDB/project/feature data may contain datetime objects.
    Normal json.dumps() cannot serialize datetime.
    default=str converts datetime into string.
    """

    return json.dumps(data, indent=2, default=str)

ARCHITECTURE_AGENT_SYSTEM_PROMPT = """
You are the Architecture Agent in AutoForge.

Your task:
Generate Software Design Specification JSON and an advanced UML Use Case Diagram model
for exactly one approved feature.

You must produce a real-world use case scenario, not a simple generic diagram.

Strict output rules:
- Return only valid JSON.
- Do not return Markdown.
- Do not return code fences.
- Do not return explanation outside JSON.
- Do not generate source code.
- Do not generate UI design.
- Do not generate API contract.
- Do not generate OpenAPI YAML.
- Do not generate component diagrams.
- Do not generate class diagrams.
- Do not generate sequence diagrams.
- Generate architecture only for the given feature, not the full project.
- Keep the design practical for MERN stack implementation.
- Reference requirement IDs from the approved SRS wherever possible.
- Preserve the selected architecture style from requirements.

Use Case Diagram Modelling Rules:
- Actors must be external user roles, not system components.
- Do not use Database, API, Controller, MongoDB, React, Node, JWT Library, or Server as actors.
- Use cases must be user-goal actions or visible system behaviours.
- Use case names should be short verb phrases.
- Main use case must represent the main feature goal.
- Mandatory internal behaviours should be represented using <<include>>.
- Optional, alternative, or error behaviours should be represented using <<extend>>.
- Constraints and non-functional requirements should usually be represented as notes, not use cases.
- Validation rules can be represented as included use cases if they are mandatory.
- Error scenarios from acceptance criteria should appear as extend flows.
- Recovery actions such as forgot password should appear as extend flows if they are optional/alternative.
- Do not add unrelated features outside the approved feature scope.
- Every important FR, AC, and VR should be traceable to a use case, relationship, or note.

The JSON must have exactly this top-level structure:

{
  "sds_json": {
    "project_id": "",
    "project_name": "",
    "project_type": "",
    "feature_id": "",
    "feature_name": "",
    "target_stack": "",
    "architecture_style": "",
    "feature_design_overview": "",
    "frontend_responsibilities": [],
    "backend_responsibilities": [],
    "database_design": {
      "collections": [],
      "data_notes": []
    },
    "api_design_summary": [
      {
        "endpoint": "",
        "method": "",
        "purpose": "",
        "related_requirements": []
      }
    ],
    "data_flow": [],
    "error_handling_design": [],
    "authentication_authorization_design": [],
    "folder_structure_suggestion": [],
    "dependency_list": [],
    "integration_with_previous_features": [],
    "scalability_notes": [],
    "assumptions": [],
    "constraints": [],
    "traceability": [
      {
        "requirement_id": "",
        "sds_section": "",
        "design_decision": ""
      }
    ]
  },
  "usecase_analysis_json": {
    "feature_goal": "",
    "primary_actors": [],
    "secondary_actors": [],
    "main_success_scenario": [],
    "mandatory_included_behaviours": [
      {
        "name": "",
        "reason": "",
        "related_requirements": []
      }
    ],
    "alternative_flows": [
      {
        "name": "",
        "condition": "",
        "related_requirements": []
      }
    ],
    "exception_flows": [
      {
        "name": "",
        "condition": "",
        "related_requirements": []
      }
    ],
    "validation_flows": [
      {
        "name": "",
        "rule": "",
        "related_requirements": []
      }
    ],
    "security_flows": [
      {
        "name": "",
        "reason": "",
        "related_requirements": []
      }
    ],
    "diagram_notes": [
      {
        "title": "",
        "description": "",
        "related_requirements": []
      }
    ],
    "traceability": [
      {
        "source_id": "",
        "source_type": "FR | AC | VR | NFR | Constraint | Risk",
        "mapped_to": "",
        "mapping_type": "use_case | include | extend | note"
      }
    ]
  },
  "usecase_json": {
    "system_boundary": "",
    "diagram_title": "",
    "actors": [
      {
        "id": "ACT-001",
        "name": "",
        "type": "primary",
        "description": ""
      }
    ],
    "use_cases": [
      {
        "id": "UC-001",
        "name": "",
        "description": "",
        "category": "main | included | extension",
        "related_requirements": []
      }
    ],
    "relationships": [
      {
        "from": "ACT-001",
        "to": "UC-001",
        "type": "association",
        "label": "",
        "related_requirements": []
      }
    ],
    "notes": [
      {
        "id": "NOTE-001",
        "target": "UC-001",
        "title": "",
        "description": "",
        "related_requirements": []
      }
    ],
    "standards_notes": []
  }
}

Relationship direction rules:
- association: actor -> use case
- include: base use case -> included use case
- extend: extension use case -> base use case
- generalization: child actor/use case -> parent actor/use case

Quality rules:
- Do not produce only one generic use case.
- Do not name the main use case "Use Feature".
- A good diagram should include main flow, mandatory behaviours, alternative/error flows, and notes when the SRS contains them.
"""


JSON_REPAIR_PROMPT = """
You are a JSON repair assistant.

The given output should be valid JSON but may be malformed.

Fix it and return only valid JSON.

Rules:
- Do not add Markdown.
- Do not add explanation.
- Do not add comments.
- Preserve original meaning as much as possible.
"""


def build_architecture_user_prompt(
    project: dict,
    feature: dict,
    srs_json: dict,
    enhanced_srs_json: dict | None = None,
    architecture_notes: str | None = None,
    human_comment: str | None = None
) -> str:
    """
    Build Architecture Agent user prompt.

    We convert Python dictionaries to formatted JSON strings.
    This gives the LLM clearer input and reduces random output.
    """

    enhanced_text = "No approved Enhanced SRS is available."

    if enhanced_srs_json:
        enhanced_text = safe_json_dumps(enhanced_srs_json)

    return f"""
Generate SDS JSON, usecase_analysis_json, and usecase_json for this feature only.

Project:
{safe_json_dumps(project)}

Feature:
{safe_json_dumps(feature)}

Approved SRS JSON:
{safe_json_dumps(srs_json)}

Approved Enhanced SRS JSON if available:
{enhanced_text}

Architecture Notes:
{architecture_notes}

Human Comment:
{human_comment}

Important task:
Before generating usecase_json, deeply analyze the approved SRS and SDS needs.

You must identify:
- Main actor roles from user_roles.
- Main use case from the feature goal.
- Mandatory behaviours from functional requirements.
- Validation behaviours from validation rules.
- Success scenario from acceptance criteria.
- Error and alternative scenarios from acceptance criteria.
- Optional recovery actions such as forgot password if present.
- Constraints and NFRs as diagram notes where appropriate.
- Traceability from FR, AC, VR, NFR, constraints, and risks.

Remember:
- Generate only SDS JSON, usecase_analysis_json, and usecase_json.
- Do not generate API contract.
- Do not generate OpenAPI YAML.
- Do not generate code.
- Do not generate UI.
- Do not design unrelated features.
- Do not create actors from technical components.
- Return only valid JSON.
"""


def build_json_repair_prompt(raw_output: str) -> str:
    """
    Build prompt to repair invalid JSON.
    """

    return f"""
Repair this malformed JSON and return only valid JSON:

{raw_output}
"""