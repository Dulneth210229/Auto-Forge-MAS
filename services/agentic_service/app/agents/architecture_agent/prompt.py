"""
Architecture Agent prompt.

This prompt uses a generic IEEE 1016-style Software Design Description structure.

Project naming note:
- Your artifact can still be called SDS: Software Design Specification.
- The structure follows IEEE 1016-style SDD concepts: design context, design views,
  design decisions, and requirement-to-design traceability.

Important:
- No API contract artifact.
- No OpenAPI artifact.
- No source code.
- No UI design.
- SDS and Use Case Diagram only.
"""

from __future__ import annotations

import json


def safe_json_dumps(data: dict) -> str:
    """
    Convert Python dictionary into JSON string safely.

    Why:
    Project/feature data may contain datetime objects.
    json.dumps(..., default=str) converts datetime into strings.
    """

    return json.dumps(data, indent=2, default=str)


ARCHITECTURE_AGENT_SYSTEM_PROMPT = """
You are the Architecture Agent in AutoForge.

Your task:
Generate an IEEE 1016-style Software Design Specification JSON and an advanced UML Use Case Diagram model
for exactly one approved feature.

Terminology:
- The project calls the artifact SDS: Software Design Specification.
- The SDS must follow an IEEE 1016-style Software Design Description structure.
- Use design views, design decisions, and requirement-to-design traceability.

Strict output rules:
- Return only valid JSON.
- Do not return Markdown.
- Do not return code fences.
- Do not return explanation outside JSON.
- Do not generate source code.
- Do not generate UI design.
- Do not generate API contract artifact.
- Do not generate OpenAPI YAML.
- Do not generate component diagrams.
- Do not generate class diagrams.
- Do not generate sequence diagrams.
- Generate architecture only for the given feature, not the full project.
- Stay inside the approved SRS and Enhanced SRS scope.
- Do not invent unrelated features.
- Keep the design practical for the target stack.
- Reference stable SRS IDs wherever possible.

IEEE-style SDS rules:
- The SDS must not be generic.
- The SDS must directly map approved SRS content into design sections.
- Every Functional Requirement must be covered in traceability_matrix.
- Every Acceptance Criterion must be covered in behavior_view, error_handling_view, or interface_view.
- Every Validation Rule must be covered in data_view, interface_view, or error_handling_view.
- Every Non-Functional Requirement must be covered in quality_attributes_view.
- Every API expectation must appear in interface_view.api_endpoints.
- Every input requirement must appear in interface_view.request_models.
- Every output requirement must appear in interface_view.response_models.
- Every data requirement must appear in data_view.
- Every risk must appear in design_considerations or security_authorization_view.
- Every constraint must appear in design_considerations or architecture_overview.
- Do not use the phrase "Fallback SDS" in normal LLM-generated SDS.

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
- Recovery actions should appear as extend flows if they are optional or alternative.
- Do not add unrelated features outside the approved feature scope.
- Every important FR, AC, VR, NFR, constraint, and risk should be traceable to a use case, relationship, or note.

The JSON must have exactly this top-level structure:

{
  "sds_json": {
    "document_control": {
      "document_title": "",
      "document_type": "Software Design Specification",
      "standard_basis": "IEEE 1016-style Software Design Description",
      "project_id": "",
      "project_name": "",
      "project_type": "",
      "feature_id": "",
      "feature_name": "",
      "target_stack": "",
      "architecture_style": "",
      "version": "",
      "generated_by": "Architecture Agent",
      "input_artifacts": [],
      "approval_status": "pending"
    },
    "introduction": {
      "purpose": "",
      "scope": [],
      "out_of_scope": [],
      "intended_audience": [],
      "definitions": []
    },
    "design_context": {
      "business_goal": "",
      "user_roles": [],
      "feature_boundary": "",
      "operating_environment": "",
      "dependencies": [],
      "assumptions": []
    },
    "design_considerations": {
      "constraints": [],
      "non_functional_requirements": [],
      "risks": [],
      "design_tradeoffs": []
    },
    "architecture_overview": {
      "architecture_style": "",
      "architecture_rationale": "",
      "frontend_overview": "",
      "backend_overview": "",
      "data_overview": "",
      "integration_overview": ""
    },
    "design_views": {
      "context_view": {
        "actors": [],
        "external_systems": [],
        "feature_boundary": "",
        "main_interactions": []
      },
      "logical_view": {
        "frontend_modules": [],
        "backend_modules": [],
        "domain_services": [],
        "data_modules": [],
        "integration_points": []
      },
      "interface_view": {
        "api_endpoints": [
          {
            "endpoint": "",
            "method": "",
            "purpose": "",
            "request_model": "",
            "success_response_model": "",
            "error_response_model": "",
            "related_requirements": []
          }
        ],
        "request_models": [
          {
            "name": "",
            "fields": [],
            "related_requirements": []
          }
        ],
        "response_models": [
          {
            "name": "",
            "type": "success | error | alternative",
            "fields": [],
            "related_requirements": []
          }
        ]
      },
      "data_view": {
        "data_entities": [
          {
            "name": "",
            "purpose": "",
            "fields": [],
            "relationships": [],
            "indexes_or_constraints": [],
            "related_requirements": []
          }
        ],
        "storage_rules": [],
        "data_validation_rules": []
      },
      "behavior_view": {
        "main_success_flow": [],
        "alternative_flows": [],
        "exception_flows": [],
        "state_changes": []
      },
      "error_handling_view": {
        "validation_errors": [],
        "business_errors": [],
        "authorization_errors": [],
        "system_errors": [],
        "user_message_rules": []
      },
      "security_authorization_view": {
        "authentication_design": [],
        "authorization_design": [],
        "sensitive_data_rules": [],
        "risk_mitigations": []
      },
      "quality_attributes_view": {
        "performance": [],
        "usability": [],
        "reliability": [],
        "scalability": [],
        "maintainability": [],
        "accessibility": []
      }
    },
    "detailed_design_decisions": [
      {
        "decision_id": "",
        "decision": "",
        "rationale": "",
        "related_requirements": []
      }
    ],
    "traceability_matrix": [
      {
        "source_id": "",
        "source_type": "FR | AC | VR | NFR | Constraint | Risk | Dependency | Data | API | UI | Assumption",
        "sds_section": "",
        "design_element": "",
        "coverage_status": "covered | partial | not_covered"
      }
    ],
    "assumptions": [],
    "constraints": [],
    "risks": [],
    "dependencies": [],
    "use_case_diagram_reference": {
      "puml_file": "",
      "png_file": "",
      "diagram_scope": "",
      "actors": [],
      "main_use_cases": [],
      "relationship_summary": []
    },
    "human_approval_note": "This SDS must be reviewed and approved before the UI/UX Agent starts."
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

    We serialize dictionaries safely because project/feature records may contain datetime.
    """

    enhanced_text = "No approved Enhanced SRS is available."

    if enhanced_srs_json:
        enhanced_text = safe_json_dumps(enhanced_srs_json)

    return f"""
Generate an IEEE 1016-style SDS JSON, usecase_analysis_json, and usecase_json for this feature only.

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

Important:
- Use exact API expectations from the SRS in interface_view.api_endpoints.
- Use input requirements from the SRS in interface_view.request_models.
- Use output requirements from the SRS in interface_view.response_models.
- Use data requirements from the SRS in design_views.data_view.
- Use acceptance criteria in behavior_view and error_handling_view.
- Use validation rules in data_view, interface_view, and error_handling_view.
- Use non-functional requirements in quality_attributes_view.
- Use risks in design_considerations and security_authorization_view.
- Use constraints in design_considerations and architecture_overview.
- Create traceability_matrix entries for all FR, AC, VR, NFR, constraints, risks, dependencies, data, API, and UI items where possible.
- Keep the output generic and feature-independent.
- Do not hardcode Login-specific, Cart-specific, Payment-specific, or LMS-specific logic.
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
