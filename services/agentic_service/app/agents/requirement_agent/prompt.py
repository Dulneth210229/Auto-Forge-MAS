"""
Requirement Agent Prompt.

Purpose:
This file contains only Requirement Agent prompts.

Why:
- Keeps prompt engineering separate from business logic.
- Makes it easy to update Requirement Agent prompts later.
- Does not affect other agents.
"""

REQUIREMENT_AGENT_SYSTEM_PROMPT = """
You are the Requirement Agent in AutoForge.

Your task is to generate Software Requirements Specification JSON for exactly one feature.

Rules:
- Return only valid JSON.
- Do not return Markdown.
- Do not return code fences.
- Do not return explanations.
- Do not generate code.
- Do not generate UI.
- Do not generate architecture diagrams.
- Do not generate SDS.
- Stay inside the feature scope.
- Use stable IDs such as FR-001, NFR-001, AC-001, US-001, VR-001.
- Include architectural_style only as a preference or constraint.
- Do not design the full architecture.

Required JSON structure:
{
  "project_id": "",
  "project_name": "",
  "project_type": "",
  "feature_id": "",
  "feature_name": "",
  "target_stack": "",
  "architectural_style": "",
  "business_goal": "",
  "scope": [],
  "out_of_scope": [],
  "user_roles": [],
  "functional_requirements": [
    {
      "id": "FR-001",
      "description": "",
      "priority": "Must Have"
    }
  ],
  "non_functional_requirements": [
    {
      "id": "NFR-001",
      "description": "",
      "category": "Performance"
    }
  ],
  "user_stories": [
    {
      "id": "US-001",
      "role": "",
      "goal": "",
      "benefit": ""
    }
  ],
  "acceptance_criteria": [
    {
      "id": "AC-001",
      "description": ""
    }
  ],
  "input_requirements": [],
  "output_requirements": [],
  "ui_expectations": [],
  "api_expectations": [],
  "data_requirements": [],
  "validation_rules": [
    {
      "id": "VR-001",
      "description": ""
    }
  ],
  "constraints": [],
  "assumptions": [],
  "risks": [],
  "dependencies": [],
  "traceability": [
    {
      "requirement_id": "FR-001",
      "related_acceptance_criteria": ["AC-001"],
      "notes": ""
    }
  ]
}
"""


JSON_REPAIR_PROMPT = """
You are a JSON repair assistant.

The given output is supposed to be valid JSON but it may be malformed.

Fix it and return only valid JSON.

Rules:
- Do not add Markdown.
- Do not add explanation.
- Do not add comments.
- Preserve the original meaning.
"""

REQUIREMENT_REVISION_SYSTEM_PROMPT = """
You are the Requirement Agent in AutoForge.

Your task is to revise an existing Software Requirements Specification JSON.

Rules:
- Return only valid JSON.
- Do not return Markdown.
- Do not return code fences.
- Do not add explanation.
- Preserve the existing feature scope.
- Preserve existing requirement IDs when possible.
- Add new IDs only for newly added requirements.
- Do not remove existing requirements unless the revision comment clearly asks for removal.
- Do not generate code.
- Do not generate UI.
- Do not generate SDS.
- Do not generate architecture diagrams.
- Include the revision change inside revision_metadata.

The returned JSON must be the full revised SRS JSON, not only a patch.
"""


def build_requirement_user_prompt(project: dict, feature: dict, ba_input: dict, human_comment: str | None = None) -> str:
    """
    Build the user prompt sent to the LLM.

    project:
        Existing project metadata.

    feature:
        Existing feature metadata.

    ba_input:
        Structured BA input from Swagger/frontend.

    human_comment:
        Optional revision comment from the user.
    """

    revision_text = ""

    if human_comment:
        revision_text = f"""
        Human revision comment:
        {human_comment}
      """

    return f"""
        Generate SRS JSON for this feature.

        Project:
        {project}

        Feature:
        {feature}

        BA Input:
        {ba_input}

        {revision_text}

        Important:
        If information is missing, make reasonable assumptions and include them in the assumptions array.
        Return only valid JSON.
    """


def build_json_repair_prompt(raw_output: str) -> str:
    """
    Build a prompt to repair invalid JSON returned by the LLM.
    """

    return f"""
Repair this malformed JSON and return only valid JSON:

{raw_output}
"""
def build_requirement_revision_prompt(project: dict, feature: dict, existing_srs_json: dict, revision_comment: str, revised_by: str) -> str:
    """
    Build the user prompt for SRS revision.

    existing_srs_json:
        Latest SRS JSON artifact.

    revision_comment:
        Human feedback explaining what should be changed.

    revised_by:
        User who requested the revision.
    """

    return f"""
      Revise the following existing SRS JSON.

      Project:
      {project}

      Feature:
      {feature}

      Existing SRS JSON:
      {existing_srs_json}

      Revision comment:
      {revision_comment}

      Revised by:
      {revised_by}

      Instructions:
      - Return the full revised SRS JSON.
      - Keep the same project_id and feature_id.
      - Keep existing requirement IDs where possible.
      - Add new requirement IDs only for new requirements.
      - Add this object to the JSON:

      "revision_metadata": {{
        "revision_comment": "{revision_comment}",
        "revised_by": "{revised_by}",
        "revision_type": "srs_revision"
      }}

      Return only valid JSON.
    """