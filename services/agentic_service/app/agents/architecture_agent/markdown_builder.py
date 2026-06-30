"""
Architecture Agent Architecture Plan Markdown Builder.

Purpose:
Convert Architecture Plan JSON into a human-readable Markdown document.

Important:
- This is not an SDS document.
- It is an implementation-support architecture plan for the Coder Agent.
- Diagram generation files are separate and are not referenced inside this plan.
"""

from __future__ import annotations

from typing import Any


class ArchitecturePlanMarkdownBuilder:
    """
    Converts Architecture Plan JSON into Architecture Plan Markdown.
    """

    def build(self, architecture_plan_json: dict[str, Any]) -> str:
        """
        Build a feature-level Architecture Plan Markdown document.
        """

        document_control = architecture_plan_json.get("document_control", {})
        feature_overview = architecture_plan_json.get("feature_overview", {})
        requirement_interpretation = architecture_plan_json.get("requirement_interpretation", {})
        architecture_approach = architecture_plan_json.get("architecture_approach", {})
        design_views = architecture_plan_json.get("design_views", {})

        feature_name = (
            document_control.get("feature_name")
            or architecture_plan_json.get("feature_name")
            or "Untitled Feature"
        )

        return f"""# Architecture Plan: {feature_name}

> Artifact Type: Feature-level Architecture Plan  
> Purpose: Convert approved SRS requirements into implementation-ready architecture guidance for the Coder Agent.

---

## 1. Document Control

{self._document_control(document_control)}

---

## 2. Feature Overview

### 2.1 Business Goal
{feature_overview.get("business_goal", "Not specified.")}

### 2.2 Scope
{self._simple_list(feature_overview.get("scope", []))}

### 2.3 Out of Scope
{self._simple_list(feature_overview.get("out_of_scope", []))}

### 2.4 User Roles
{self._simple_list(feature_overview.get("user_roles", []))}

### 2.5 Feature Boundary
{feature_overview.get("feature_boundary", "Not specified.")}

---

## 3. Requirement Interpretation

### 3.1 Functional Requirements Interpretation
{self._records_list(requirement_interpretation.get("functional_requirements", []))}

### 3.2 Acceptance Criteria Interpretation
{self._records_list(requirement_interpretation.get("acceptance_criteria", []))}

### 3.3 Validation Rules Interpretation
{self._records_list(requirement_interpretation.get("validation_rules", []))}

### 3.4 Non-Functional Requirements Interpretation
{self._records_list(requirement_interpretation.get("non_functional_requirements", []))}

---

## 4. Architecture Approach

### 4.1 Architecture Style
{architecture_approach.get("architecture_style", "Not specified.")}

### 4.2 Architecture Rationale
{architecture_approach.get("architecture_rationale", "Not specified.")}

### 4.3 Frontend Overview
{architecture_approach.get("frontend_overview", "Not specified.")}

### 4.4 Backend Overview
{architecture_approach.get("backend_overview", "Not specified.")}

### 4.5 Data Overview
{architecture_approach.get("data_overview", "Not specified.")}

### 4.6 Integration Overview
{architecture_approach.get("integration_overview", "Not specified.")}

### 4.7 Design Trade-offs
{self._simple_list(architecture_approach.get("design_tradeoffs", []))}

---

## 5. Frontend Architecture Plan

{self._frontend_plan(architecture_plan_json.get("frontend_architecture_plan", {}), design_views)}

---

## 6. Backend Architecture Plan

{self._backend_plan(architecture_plan_json.get("backend_architecture_plan", {}), design_views)}

---

## 7. API and Interface Plan

{self._interface_view(design_views.get("interface_view", {}))}

---

## 8. Data Model Plan

{self._data_view(design_views.get("data_view", {}))}

---

## 9. Validation Plan

{self._validation_plan(architecture_plan_json.get("validation_plan", {}), design_views)}

---

## 10. Error Handling Plan

{self._error_handling_view(design_views.get("error_handling_view", {}))}

---

## 11. Security Plan

{self._security_view(design_views.get("security_authorization_view", {}))}

---

## 12. Quality / NFR Plan

{self._quality_view(design_views.get("quality_attributes_view", {}))}

---

## 13. Coder Implementation Tasks

{self._implementation_tasks(architecture_plan_json.get("coder_implementation_tasks", []))}

---

## 14. Requirement-to-Architecture Traceability

{self._traceability_matrix(architecture_plan_json.get("traceability_matrix", []))}

---

## 15. Assumptions, Constraints, Risks, and Dependencies

### 15.1 Assumptions
{self._simple_list(architecture_plan_json.get("assumptions", []))}

### 15.2 Constraints
{self._simple_list(architecture_plan_json.get("constraints", []))}

### 15.3 Risks
{self._records_list(architecture_plan_json.get("risks", []))}

### 15.4 Dependencies
{self._simple_list(architecture_plan_json.get("dependencies", []))}

---

## 16. Human Approval Note

{architecture_plan_json.get("human_approval_note", "This Architecture Plan must be reviewed and approved before the UI/UX Agent or Coder Agent starts.")}
"""

    def _document_control(self, data: dict[str, Any]) -> str:
        rows = [
            ("Document Title", data.get("document_title", "N/A")),
            ("Document Type", data.get("document_type", "Feature Architecture Plan")),
            ("Project ID", data.get("project_id", "N/A")),
            ("Project Name", data.get("project_name", "N/A")),
            ("Project Type", data.get("project_type", "N/A")),
            ("Feature ID", data.get("feature_id", "N/A")),
            ("Feature Name", data.get("feature_name", "N/A")),
            ("Target Stack", data.get("target_stack", "N/A")),
            ("Architecture Style", data.get("architecture_style", "N/A")),
            ("Version", data.get("version", "v1")),
            ("Generated By", data.get("generated_by", "Architecture Agent")),
            ("Approval Status", data.get("approval_status", "pending")),
        ]

        lines = ["| Field | Value |", "|---|---|"]
        for key, value in rows:
            lines.append(f"| {key} | {self._inline(value)} |")

        input_artifacts = data.get("input_artifacts", [])
        lines.append(f"| Input Artifacts | {self._inline(', '.join(map(str, input_artifacts)) if input_artifacts else 'N/A')} |")
        return "\n".join(lines)

    def _frontend_plan(self, data: dict[str, Any], design_views: dict[str, Any]) -> str:
        logical_view = design_views.get("logical_view", {})
        return "\n".join([
            "**Frontend Responsibilities:**",
            self._records_list(data.get("responsibilities", logical_view.get("frontend_modules", []))),
            "",
            "**Pages / Components:**",
            self._records_list(data.get("pages_or_components", [])),
            "",
            "**State and User Feedback:**",
            self._simple_list(data.get("state_and_feedback", [])),
        ])

    def _backend_plan(self, data: dict[str, Any], design_views: dict[str, Any]) -> str:
        logical_view = design_views.get("logical_view", {})
        return "\n".join([
            "**Backend Responsibilities:**",
            self._records_list(data.get("responsibilities", logical_view.get("backend_modules", []))),
            "",
            "**Controller / Service / Data Responsibilities:**",
            self._records_list(data.get("layers", logical_view.get("domain_services", []) + logical_view.get("data_modules", []))),
            "",
            "**Integration Points:**",
            self._records_list(data.get("integration_points", logical_view.get("integration_points", []))),
        ])

    def _validation_plan(self, data: dict[str, Any], design_views: dict[str, Any]) -> str:
        data_view = design_views.get("data_view", {})
        return "\n".join([
            "**Input Validation Rules:**",
            self._records_list(data.get("input_validation", data_view.get("data_validation_rules", []))),
            "",
            "**Processing Validation Rules:**",
            self._records_list(data.get("processing_validation", [])),
        ])

    def _interface_view(self, data: dict[str, Any]) -> str:
        return "\n".join([
            "**API Endpoints:**",
            self._api_endpoints(data.get("api_endpoints", [])),
            "",
            "**Request Models:**",
            self._models(data.get("request_models", [])),
            "",
            "**Response Models:**",
            self._models(data.get("response_models", [])),
            "",
            "> Note: This is an Architecture Plan interface summary. It is not a separate API contract artifact.",
        ])

    def _data_view(self, data: dict[str, Any]) -> str:
        return "\n".join([
            "**Data Entities:**",
            self._data_entities(data.get("data_entities", [])),
            "",
            "**Storage Rules:**",
            self._simple_list(data.get("storage_rules", [])),
            "",
            "**Data Validation Rules:**",
            self._records_list(data.get("data_validation_rules", [])),
        ])

    def _error_handling_view(self, data: dict[str, Any]) -> str:
        return "\n".join([
            "**Validation Errors:**",
            self._records_list(data.get("validation_errors", [])),
            "",
            "**Business Errors:**",
            self._records_list(data.get("business_errors", [])),
            "",
            "**Authorization Errors:**",
            self._records_list(data.get("authorization_errors", [])),
            "",
            "**System Errors:**",
            self._records_list(data.get("system_errors", [])),
            "",
            "**User Message Rules:**",
            self._simple_list(data.get("user_message_rules", [])),
        ])

    def _security_view(self, data: dict[str, Any]) -> str:
        return "\n".join([
            "**Authentication Design:**",
            self._records_list(data.get("authentication_design", [])),
            "",
            "**Authorization Design:**",
            self._records_list(data.get("authorization_design", [])),
            "",
            "**Sensitive Data Rules:**",
            self._records_list(data.get("sensitive_data_rules", [])),
            "",
            "**Risk Mitigations:**",
            self._records_list(data.get("risk_mitigations", [])),
        ])

    def _quality_view(self, data: dict[str, Any]) -> str:
        sections = []
        for key, title in [
            ("performance", "Performance"),
            ("usability", "Usability"),
            ("reliability", "Reliability"),
            ("scalability", "Scalability"),
            ("maintainability", "Maintainability"),
            ("accessibility", "Accessibility"),
        ]:
            sections.append(f"**{title}:**")
            sections.append(self._records_list(data.get(key, [])))
            sections.append("")
        return "\n".join(sections).strip()

    def _api_endpoints(self, endpoints: list[Any]) -> str:
        if not endpoints:
            return "- Not specified."
        lines = []
        for endpoint in endpoints:
            if not isinstance(endpoint, dict):
                lines.append(f"- {endpoint}")
                continue
            lines.append(f"- **{endpoint.get('method', 'METHOD')} {endpoint.get('endpoint', '/path')}**")
            lines.append(f"  - Purpose: {endpoint.get('purpose', 'No purpose provided.')}")
            lines.append(f"  - Request Model: {endpoint.get('request_model', 'N/A')}")
            lines.append(f"  - Success Response Model: {endpoint.get('success_response_model', 'N/A')}")
            lines.append(f"  - Error Response Model: {endpoint.get('error_response_model', 'N/A')}")
            lines.append(f"  - Related Requirements: {self._join(endpoint.get('related_requirements', []))}")
        return "\n".join(lines)

    def _models(self, models: list[Any]) -> str:
        if not models:
            return "- Not specified."
        lines = []
        for model in models:
            if not isinstance(model, dict):
                lines.append(f"- {model}")
                continue
            lines.append(f"- **{model.get('name', 'Model')}**")
            if model.get("type"):
                lines.append(f"  - Type: {model.get('type')}")
            lines.append("  - Fields:")
            for field in model.get("fields", []) or ["Not specified."]:
                lines.append(f"    - {self._inline(field)}")
            lines.append(f"  - Related Requirements: {self._join(model.get('related_requirements', []))}")
        return "\n".join(lines)

    def _data_entities(self, entities: list[Any]) -> str:
        if not entities:
            return "- Not specified."
        lines = []
        for entity in entities:
            if not isinstance(entity, dict):
                lines.append(f"- {entity}")
                continue
            lines.append(f"- **{entity.get('name', 'Entity')}**")
            lines.append(f"  - Purpose: {entity.get('purpose', 'Not specified.')}")
            lines.append("  - Fields:")
            for field in entity.get("fields", []) or ["Not specified."]:
                lines.append(f"    - {self._inline(field)}")
            lines.append("  - Relationships:")
            for relationship in entity.get("relationships", []) or ["Not specified."]:
                lines.append(f"    - {self._inline(relationship)}")
            lines.append("  - Indexes / Constraints:")
            for constraint in entity.get("indexes_or_constraints", []) or ["Not specified."]:
                lines.append(f"    - {self._inline(constraint)}")
            lines.append(f"  - Related Requirements: {self._join(entity.get('related_requirements', []))}")
        return "\n".join(lines)

    def _implementation_tasks(self, tasks: list[Any]) -> str:
        if not tasks:
            return "- Not specified."
        lines = []
        for task in tasks:
            if not isinstance(task, dict):
                lines.append(f"- {task}")
                continue
            lines.append(f"- **{task.get('task_id', 'TASK')}**: {task.get('task', task.get('description', 'Not specified.'))}")
            lines.append(f"  - Layer: {task.get('layer', 'N/A')}")
            lines.append(f"  - Suggested Files: {self._join(task.get('suggested_files', []))}")
            lines.append(f"  - Related Requirements: {self._join(task.get('related_requirements', []))}")
        return "\n".join(lines)

    def _traceability_matrix(self, items: list[Any]) -> str:
        if not items:
            return "- Not specified."
        lines = [
            "| Source ID | Source Type | Architecture Plan Section | Design / Task Element | Coverage |",
            "|---|---|---|---|---|",
        ]
        for item in items:
            if not isinstance(item, dict):
                continue
            section = item.get("architecture_plan_section") or item.get("sds_section") or "N/A"
            element = item.get("design_element") or item.get("task") or "N/A"
            lines.append(
                f"| {item.get('source_id', 'N/A')} | {item.get('source_type', 'N/A')} | {section} | {element} | {item.get('coverage_status', 'covered')} |"
            )
        return "\n".join(lines)

    def _records_list(self, items: list[Any]) -> str:
        if not items:
            return "- Not specified."
        lines = []
        for item in items:
            if isinstance(item, dict):
                lines.append(f"- {self._inline(item)}")
            else:
                lines.append(f"- {item}")
        return "\n".join(lines)

    def _simple_list(self, items: list[Any]) -> str:
        if not items:
            return "- Not specified."
        return "\n".join(f"- {self._inline(item)}" for item in items)

    def _definition_list(self, items: list[Any]) -> str:
        if not items:
            return "- Not specified."
        lines = []
        for item in items:
            if isinstance(item, dict):
                lines.append(f"- **{item.get('term', 'Term')}:** {item.get('definition', 'Not specified.')}")
            else:
                lines.append(f"- {item}")
        return "\n".join(lines)

    def _join(self, items: Any) -> str:
        if not items:
            return "N/A"
        if isinstance(items, list):
            return ", ".join(str(item) for item in items)
        return str(items)

    def _inline(self, value: Any) -> str:
        if isinstance(value, dict):
            return ", ".join(f"{key}: {val}" for key, val in value.items())
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return str(value)


# Backward-compatible alias so older imports do not break immediately.
ArchitectureSDSMarkdownBuilder = ArchitecturePlanMarkdownBuilder
