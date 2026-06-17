"""
Markdown utility functions.

This file converts structured JSON data into clean Markdown.

Why this is needed:
LLMs often make mistakes when they return a large Markdown document
inside a JSON string.

To avoid JSON parsing errors, the Requirement Agent now asks the LLM
to generate only SRS JSON. Then this backend utility creates the
SRS Markdown file from that JSON.

This gives us:
- valid JSON
- consistent Markdown formatting
- fewer LLM parsing errors
- better artifact quality
"""

from typing import Any


def _list_to_markdown(items: list[Any]) -> str:
    """
    Convert a simple list into Markdown bullet points.
    """
    if not items:
        return "- Not specified."

    lines = []

    for item in items:
        if isinstance(item, str):
            lines.append(f"- {item}")
        elif isinstance(item, dict):
            description = item.get("description") or item.get("name") or str(item)
            item_id = item.get("id")

            if item_id:
                lines.append(f"- **{item_id}**: {description}")
            else:
                lines.append(f"- {description}")
        else:
            lines.append(f"- {str(item)}")

    return "\n".join(lines)


def _requirements_to_markdown(items: list[dict[str, Any]]) -> str:
    """
    Convert requirement objects into Markdown.

    Example input:
    [
        {
            "id": "FR-001",
            "description": "User can login",
            "priority": "Must Have"
        }
    ]
    """
    if not items:
        return "- Not specified."

    lines = []

    for item in items:
        req_id = item.get("id", "N/A")
        description = item.get("description", "No description provided.")
        priority = item.get("priority")
        category = item.get("category")

        extra_parts = []

        if priority:
            extra_parts.append(f"Priority: {priority}")

        if category:
            extra_parts.append(f"Category: {category}")

        extra_text = ""
        if extra_parts:
            extra_text = f" ({', '.join(extra_parts)})"

        lines.append(f"- **{req_id}**: {description}{extra_text}")

    return "\n".join(lines)


def _user_stories_to_markdown(items: list[dict[str, Any]]) -> str:
    """
    Convert user story objects into Markdown.
    """
    if not items:
        return "- Not specified."

    lines = []

    for item in items:
        story_id = item.get("id", "N/A")
        role = item.get("role", "user")
        goal = item.get("goal", "perform this feature")
        benefit = item.get("benefit", "achieve the business goal")

        lines.append(
            f"- **{story_id}**: As a **{role}**, I want to **{goal}**, "
            f"so that **{benefit}**."
        )

    return "\n".join(lines)


def _traceability_to_markdown(items: list[dict[str, Any]]) -> str:
    """
    Convert traceability records into Markdown.
    """
    if not items:
        return "- Not specified."

    lines = []

    for item in items:
        requirement_id = item.get("requirement_id", "N/A")
        acceptance = item.get("related_acceptance_criteria", [])
        notes = item.get("notes", "")

        if isinstance(acceptance, list):
            acceptance_text = ", ".join(acceptance)
        else:
            acceptance_text = str(acceptance)

        lines.append(
            f"- **{requirement_id}** → Acceptance Criteria: "
            f"{acceptance_text or 'N/A'}"
        )

        if notes:
            lines.append(f"  - Notes: {notes}")

    return "\n".join(lines)


def build_srs_markdown(srs_json: dict[str, Any]) -> str:
    """
    Build a complete SRS Markdown document from SRS JSON.

    This function is used by the Requirement Agent after the LLM returns
    valid structured SRS JSON.
    """

    project_name = srs_json.get("project_name", "Untitled Project")
    feature_name = srs_json.get("feature_name", "Untitled Feature")

    return f"""# Software Requirements Specification: {feature_name}

## 1. Project Information

- **Project ID:** {srs_json.get("project_id", "N/A")}
- **Project Name:** {project_name}
- **Project Type:** {srs_json.get("project_type", "N/A")}
- **Feature ID:** {srs_json.get("feature_id", "N/A")}
- **Feature Name:** {feature_name}
- **Target Stack:** {srs_json.get("target_stack", "MERN")}
- **Preferred Architectural Style:** {srs_json.get("architectural_style", "modular")}

---

## 2. Business Goal

{srs_json.get("business_goal", "Not specified.")}

---

## 3. Scope

{_list_to_markdown(srs_json.get("scope", []))}

---

## 4. Out of Scope

{_list_to_markdown(srs_json.get("out_of_scope", []))}

---

## 5. User Roles

{_list_to_markdown(srs_json.get("user_roles", []))}

---

## 6. Functional Requirements

{_requirements_to_markdown(srs_json.get("functional_requirements", []))}

---

## 7. Non-Functional Requirements

{_requirements_to_markdown(srs_json.get("non_functional_requirements", []))}

---

## 8. User Stories

{_user_stories_to_markdown(srs_json.get("user_stories", []))}

---

## 9. Acceptance Criteria

{_requirements_to_markdown(srs_json.get("acceptance_criteria", []))}

---

## 10. Input Requirements

{_list_to_markdown(srs_json.get("input_requirements", []))}

---

## 11. Output Requirements

{_list_to_markdown(srs_json.get("output_requirements", []))}

---

## 12. UI Expectations

{_list_to_markdown(srs_json.get("ui_expectations", []))}

---

## 13. API Expectations

{_list_to_markdown(srs_json.get("api_expectations", []))}

---

## 14. Data Requirements

{_list_to_markdown(srs_json.get("data_requirements", []))}

---

## 15. Validation Rules

{_requirements_to_markdown(srs_json.get("validation_rules", []))}

---

## 16. Constraints

{_list_to_markdown(srs_json.get("constraints", []))}

---

## 17. Assumptions

{_list_to_markdown(srs_json.get("assumptions", []))}

---

## 18. Risks

{_list_to_markdown(srs_json.get("risks", []))}

---

## 19. Dependencies

{_list_to_markdown(srs_json.get("dependencies", []))}

---

## 20. Requirement Traceability Summary

{_traceability_to_markdown(srs_json.get("traceability", []))}

---

## 21. Human Approval Note

This SRS was generated by the Requirement Agent and must be reviewed by a human before it is passed to the Domain Agent.
"""