"""
Architecture Agent.

Purpose:
- Load approved SRS JSON from Requirement Agent.
- Optionally load approved Enhanced SRS JSON from Domain Agent.
- Generate SDS JSON, usecase_analysis_json, and usecase_json using LLM.
- Convert SDS JSON into Markdown.
- Convert usecase_json into PlantUML.
- Render PlantUML into PNG.
- Save all Architecture Agent artifacts.

Important:
This implementation does not generate:
- API contract JSON
- OpenAPI YAML
- code
- UI
- component diagram
- class diagram
- sequence diagram

Outputs:
- SDS Markdown
- SDS JSON
- Use Case Diagram PUML
- Use Case Diagram PNG

Important improvement:
The Use Case Diagram is no longer allowed to be too simple.
If the LLM generates a weak diagram such as:
    Customer -> Use Login Feature

The validator rejects it and the agent builds a stronger fallback diagram
from the approved SRS.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from app.agents.architecture_agent.markdown_builder import ArchitectureSDSMarkdownBuilder
from app.agents.architecture_agent.prompt import (
    ARCHITECTURE_AGENT_SYSTEM_PROMPT,
    JSON_REPAIR_PROMPT,
    build_architecture_user_prompt,
    build_json_repair_prompt,
)
from app.agents.architecture_agent.schemas import (
    ArchitectureAgentInput,
    ArchitectureAgentOutput,
)
from app.agents.architecture_agent.usecase_builder import ArchitectureUseCasePlantUMLBuilder
from app.agents.architecture_agent.usecase_renderer import UseCaseDiagramRenderer
from app.agents.architecture_agent.usecase_validator import (
    UseCaseQualityValidator,
    UseCaseValidationError,
)
from app.core.enums import (
    AgentName,
    ApprovalStatus,
    ArtifactFormat,
    ArtifactType,
    FeatureStatus,
)
from app.schemas.agent_schema import AgentRunResponse
from app.schemas.architecture_schema import ArchitectureAgentRunRequest
from app.services.artifact_service import artifact_service
from app.services.in_memory_store import store
from app.services.llm_provider_service import llm_provider_service
from app.utils.file_manager import read_json_file, write_json_file, write_text_file
from app.utils.id_generator import generate_id
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ArchitectureAgent:
    """
    Main Architecture Agent class.

    This class controls:
    1. Approved input artifact loading.
    2. LLM architecture generation.
    3. JSON structure validation.
    4. UML use case quality validation.
    5. SDS Markdown generation.
    6. PlantUML generation.
    7. PNG rendering.
    8. Artifact saving.
    """

    REQUIRED_TOP_LEVEL_KEYS = [
        "sds_json",
        "usecase_analysis_json",
        "usecase_json",
    ]

    REQUIRED_SDS_KEYS = [
        "project_id",
        "project_name",
        "project_type",
        "feature_id",
        "feature_name",
        "target_stack",
        "architecture_style",
        "feature_design_overview",
        "frontend_responsibilities",
        "backend_responsibilities",
        "database_design",
        "api_design_summary",
        "data_flow",
        "error_handling_design",
        "authentication_authorization_design",
        "folder_structure_suggestion",
        "dependency_list",
        "traceability",
    ]

    REQUIRED_USECASE_KEYS = [
        "system_boundary",
        "diagram_title",
        "actors",
        "use_cases",
        "relationships",
        "notes",
    ]

    def __init__(self):
        """
        Initialize Architecture Agent helpers.

        These helpers are specific to the Architecture Agent.
        We are not changing common/shared files.
        """

        # Converts SDS JSON to human-readable Markdown.
        self.markdown_builder = ArchitectureSDSMarkdownBuilder()

        # Converts structured usecase_json to PlantUML.
        self.usecase_builder = ArchitectureUseCasePlantUMLBuilder()

        # Validates UML quality before saving.
        # This prevents weak diagrams such as:
        # Customer -> Use Login Feature
        self.usecase_validator = UseCaseQualityValidator()

        # Converts .puml into .png.
        self.diagram_renderer = UseCaseDiagramRenderer()

    async def run(
        self,
        feature_id: str,
        request: ArchitectureAgentRunRequest
    ) -> AgentRunResponse:
        """
        Run Architecture Agent for one feature.

        Endpoint:
            POST /features/{feature_id}/agents/architecture/run

        Rule:
            Architecture Agent can only run after Requirement Agent SRS JSON
            is approved by a human.
        """

        logger.info("Architecture Agent started for feature_id=%s", feature_id)

        feature = store.features.get(feature_id)

        if not feature:
            raise ValueError("Feature not found.")

        project = store.projects.get(feature["project_id"])

        if not project:
            raise ValueError("Project not found for this feature.")

        # Find latest approved SRS JSON from Requirement Agent.
        srs_artifact = self._find_latest_approved_artifact(
            feature_id=feature_id,
            agent_name=AgentName.REQUIREMENT,
            artifact_type=ArtifactType.SRS,
            artifact_format=ArtifactFormat.JSON
        )

        if not srs_artifact:
            raise ValueError(
                "No approved SRS JSON artifact found. "
                "Approve Requirement Agent SRS JSON before running Architecture Agent."
            )

        srs_json = read_json_file(srs_artifact["file_path"])

        enhanced_srs_json = None

        # If Domain Agent output exists and is approved, Architecture Agent can use it.
        # If not available, it still works using approved SRS JSON.
        if request.use_enhanced_srs_if_available:
            enhanced_srs_artifact = self._find_latest_approved_artifact(
                feature_id=feature_id,
                agent_name=AgentName.DOMAIN,
                artifact_type=ArtifactType.ENHANCED_SRS,
                artifact_format=ArtifactFormat.JSON
            )

            if enhanced_srs_artifact:
                enhanced_srs_json = read_json_file(enhanced_srs_artifact["file_path"])

        # Update feature progress.
        feature["feature_status"] = FeatureStatus.IN_PROGRESS
        feature["current_agent"] = AgentName.ARCHITECTURE

        agent_input = ArchitectureAgentInput(
            project=dict(project),
            feature=dict(feature),
            srs_json=srs_json,
            enhanced_srs_json=enhanced_srs_json,
            architecture_notes=request.architecture_notes,
            human_comment=request.human_comment
        )

        output = await self._generate_architecture_output(agent_input)

        artifact_ids = self._save_architecture_artifacts(
            project=dict(project),
            feature=dict(feature),
            output=output
        )

        logger.info(
            "Architecture Agent completed for feature_id=%s artifacts=%s",
            feature_id,
            artifact_ids
        )

        return AgentRunResponse(
            feature_id=feature_id,
            agent_name=AgentName.ARCHITECTURE,
            status="completed",
            message=(
                "Architecture Agent completed successfully. "
                "SDS and Use Case Diagram artifacts were generated. "
                "Human approval is required before UI/UX Agent can run."
            ),
            artifact_ids=artifact_ids
        )

    async def _generate_architecture_output(
        self,
        agent_input: ArchitectureAgentInput
    ) -> ArchitectureAgentOutput:
        """
        Generate Architecture Agent output.

        Main approach:
        1. Ask LLM for JSON only.
        2. Parse and validate basic JSON structure.
        3. Validate use case diagram quality.
        4. If JSON is broken, ask LLM to repair it.
        5. If still broken or too weak, build dynamic fallback from SRS.
        6. Convert SDS JSON to Markdown.
        7. Convert usecase_json to PlantUML.
        """

        provider = llm_provider_service.get_provider()

        prompt = build_architecture_user_prompt(
            project=agent_input.project,
            feature=agent_input.feature,
            srs_json=agent_input.srs_json,
            enhanced_srs_json=agent_input.enhanced_srs_json,
            architecture_notes=agent_input.architecture_notes,
            human_comment=agent_input.human_comment
        )

        raw_output = await provider.invoke_agent([
            {
                "role": "system",
                "content": ARCHITECTURE_AGENT_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ])

        try:
            # First attempt: parse LLM output.
            parsed = self._parse_and_validate_output(raw_output)

        except Exception as first_error:
            logger.warning("Architecture JSON parse failed: %s", first_error)

            # Second attempt: ask LLM to repair its JSON.
            repair_prompt = build_json_repair_prompt(raw_output)

            repaired_output = await provider.invoke_agent([
                {
                    "role": "system",
                    "content": JSON_REPAIR_PROMPT
                },
                {
                    "role": "user",
                    "content": repair_prompt
                }
            ])

            try:
                parsed = self._parse_and_validate_output(repaired_output)
                raw_output = repaired_output

            except Exception as second_error:
                logger.warning("Architecture JSON repair failed: %s", second_error)

                # Final fallback: generate architecture output from SRS
                # without relying on LLM.
                parsed = self._build_fallback_architecture_output(
                    agent_input=agent_input,
                    reason=str(second_error)
                )

                raw_output = json.dumps(parsed, indent=2)

        sds_json = parsed["sds_json"]
        usecase_analysis_json = parsed["usecase_analysis_json"]
        usecase_json = parsed["usecase_json"]

        # Validate UML quality after parsing.
        # This catches simple but bad diagrams.
        try:
            self.usecase_validator.validate(
                srs_json=agent_input.enhanced_srs_json or agent_input.srs_json,
                sds_json=sds_json,
                usecase_analysis_json=usecase_analysis_json,
                usecase_json=usecase_json,
            )

        except UseCaseValidationError as validation_error:
            logger.warning(
                "Generated use case diagram was too weak. Using fallback. Reason: %s",
                validation_error
            )

            parsed = self._build_fallback_architecture_output(
                agent_input=agent_input,
                reason=str(validation_error)
            )

            raw_output = json.dumps(parsed, indent=2)

            sds_json = parsed["sds_json"]
            usecase_analysis_json = parsed["usecase_analysis_json"]
            usecase_json = parsed["usecase_json"]

        # Convert SDS JSON into human-readable Markdown.
        sds_markdown = self.markdown_builder.build(sds_json)

        # Convert usecase_json into PlantUML source.
        usecase_puml = self.usecase_builder.build(usecase_json)

        return ArchitectureAgentOutput(
            sds_json=sds_json,
            sds_markdown=sds_markdown,
            usecase_analysis_json=usecase_analysis_json,
            usecase_json=usecase_json,
            usecase_puml=usecase_puml,
            raw_llm_output=raw_output
        )

    def _parse_and_validate_output(self, raw_output: str) -> dict:
        """
        Parse and validate Architecture Agent JSON output.

        This method only checks JSON structure.
        Deep UML quality checking is handled by UseCaseQualityValidator.
        """

        parsed = self._extract_json_object(raw_output)

        self._ensure_keys(parsed, self.REQUIRED_TOP_LEVEL_KEYS)

        sds_json = parsed.get("sds_json")
        usecase_analysis_json = parsed.get("usecase_analysis_json")
        usecase_json = parsed.get("usecase_json")

        if not isinstance(sds_json, dict):
            raise ValueError("sds_json must be a JSON object.")

        if not isinstance(usecase_analysis_json, dict):
            raise ValueError("usecase_analysis_json must be a JSON object.")

        if not isinstance(usecase_json, dict):
            raise ValueError("usecase_json must be a JSON object.")

        self._ensure_keys(sds_json, self.REQUIRED_SDS_KEYS)
        self._ensure_keys(usecase_json, self.REQUIRED_USECASE_KEYS)

        self._validate_usecase_json(usecase_json)

        return parsed

    def _extract_json_object(self, text: str) -> dict:
        """
        Extract JSON object from LLM output.

        This is Architecture-Agent-specific.
        We are not changing shared json_utils.py.
        """

        cleaned = text.strip()

        # Remove common Markdown code fences if LLM returns them accidentally.
        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Fallback extraction if the LLM added text before/after JSON.
        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in Architecture Agent output.")

        return json.loads(cleaned[start:end + 1])

    def _ensure_keys(self, data: dict, required_keys: list[str]) -> None:
        """
        Validate required keys in a dictionary.
        """

        missing = [key for key in required_keys if key not in data]

        if missing:
            raise ValueError(f"Missing required keys: {missing}")

    def _validate_usecase_json(self, usecase_json: dict) -> None:
        """
        Validate basic use case diagram structure.

        This method checks only:
        - actors
        - use cases
        - relationships
        - notes

        Deeper quality validation is done by UseCaseQualityValidator.
        """

        actors = usecase_json.get("actors", [])
        use_cases = usecase_json.get("use_cases", [])
        relationships = usecase_json.get("relationships", [])
        notes = usecase_json.get("notes", [])

        if not isinstance(actors, list) or not actors:
            raise ValueError("usecase_json.actors must be a non-empty list.")

        if not isinstance(use_cases, list) or not use_cases:
            raise ValueError("usecase_json.use_cases must be a non-empty list.")

        if not isinstance(relationships, list) or not relationships:
            raise ValueError("usecase_json.relationships must be a non-empty list.")

        if not isinstance(notes, list):
            raise ValueError("usecase_json.notes must be a list.")

        for actor in actors:
            if not actor.get("id") or not actor.get("name"):
                raise ValueError("Each actor must have id and name.")

        for use_case in use_cases:
            if not use_case.get("id") or not use_case.get("name"):
                raise ValueError("Each use case must have id and name.")

        for relationship in relationships:
            if not relationship.get("from") or not relationship.get("to"):
                raise ValueError("Each relationship must have from and to.")

            if relationship.get("type") not in [
                "association",
                "include",
                "extend",
                "generalization",
            ]:
                raise ValueError(
                    f"Invalid use case relationship type: {relationship.get('type')}"
                )

    def _find_latest_approved_artifact(
        self,
        feature_id: str,
        agent_name: AgentName,
        artifact_type: ArtifactType,
        artifact_format: ArtifactFormat
    ) -> dict | None:
        """
        Find latest approved artifact.

        Architecture Agent must not use unapproved input artifacts.
        """

        matching_artifacts = []

        for artifact in store.artifacts.values():
            if artifact.get("feature_id") != feature_id:
                continue

            if artifact.get("agent_name") not in [agent_name, agent_name.value]:
                continue

            if artifact.get("artifact_type") not in [artifact_type, artifact_type.value]:
                continue

            if artifact.get("artifact_format") not in [artifact_format, artifact_format.value]:
                continue

            if artifact.get("approval_status") not in [
                ApprovalStatus.APPROVED,
                ApprovalStatus.APPROVED.value
            ]:
                continue

            matching_artifacts.append(artifact)

        if not matching_artifacts:
            return None

        return max(matching_artifacts, key=lambda item: item.get("version", 1))

    def _save_architecture_artifacts(
        self,
        project: dict,
        feature: dict,
        output: ArchitectureAgentOutput
    ) -> list[str]:
        """
        Save Architecture Agent artifacts manually.

        Why manually?
        - We want all Architecture Agent files to share the same version.
        - We do not change common artifact_service.py.
        - This keeps versioning behavior isolated to Architecture Agent.

        Files:
        - {feature}_sds_v1.md
        - {feature}_sds_v1.json
        - {feature}_usecase_v1.puml
        - {feature}_usecase_v1.png
        """

        version = artifact_service.get_next_version(
            feature_id=feature["feature_id"],
            agent_name=AgentName.ARCHITECTURE,
            artifact_type=ArtifactType.SDS
        )

        stage_folder = artifact_service.get_stage_folder(
            project_name=project["project_name"],
            feature_name=feature["feature_name"],
            agent_name=AgentName.ARCHITECTURE
        )

        feature_slug = self._feature_slug(feature)

        sds_md_path = stage_folder / f"{feature_slug}_sds_v{version}.md"
        sds_json_path = stage_folder / f"{feature_slug}_sds_v{version}.json"
        usecase_puml_path = stage_folder / f"{feature_slug}_usecase_v{version}.puml"

        saved_sds_md = write_text_file(sds_md_path, output.sds_markdown)
        saved_sds_json = write_json_file(sds_json_path, output.sds_json)
        saved_puml = write_text_file(usecase_puml_path, output.usecase_puml)

        png_path = self.diagram_renderer.render_png(Path(saved_puml))

        artifact_ids = []
        created_at = datetime.now(timezone.utc)

        artifact_ids.append(
            self._register_artifact(
                project=project,
                feature=feature,
                artifact_type=ArtifactType.SDS,
                artifact_format=ArtifactFormat.MARKDOWN,
                file_path=saved_sds_md,
                version=version,
                created_at=created_at
            )
        )

        artifact_ids.append(
            self._register_artifact(
                project=project,
                feature=feature,
                artifact_type=ArtifactType.SDS,
                artifact_format=ArtifactFormat.JSON,
                file_path=saved_sds_json,
                version=version,
                created_at=created_at
            )
        )

        artifact_ids.append(
            self._register_artifact(
                project=project,
                feature=feature,
                artifact_type=ArtifactType.USE_CASE_DIAGRAM,
                artifact_format=ArtifactFormat.TEXT,
                file_path=saved_puml,
                version=version,
                created_at=created_at
            )
        )

        artifact_ids.append(
            self._register_artifact(
                project=project,
                feature=feature,
                artifact_type=ArtifactType.USE_CASE_DIAGRAM,
                artifact_format=ArtifactFormat.PNG,
                file_path=str(png_path),
                version=version,
                created_at=created_at
            )
        )

        return artifact_ids

    def _register_artifact(
        self,
        project: dict,
        feature: dict,
        artifact_type: ArtifactType,
        artifact_format: ArtifactFormat,
        file_path: str,
        version: int,
        created_at: datetime
    ) -> str:
        """
        Register artifact metadata in database/store.

        This mirrors artifact_service behavior but stays inside Architecture Agent.
        """

        artifact_id = generate_id("artifact")

        store.artifacts[artifact_id] = {
            "artifact_id": artifact_id,
            "project_id": project["project_id"],
            "feature_id": feature["feature_id"],
            "agent_name": AgentName.ARCHITECTURE,
            "artifact_type": artifact_type,
            "artifact_format": artifact_format,
            "file_path": file_path,
            "version": version,
            "approval_status": ApprovalStatus.PENDING,
            "created_at": created_at,
        }

        return artifact_id

    def _feature_slug(self, feature: dict) -> str:
        """
        Build safe file name slug from feature name.

        Example:
            Login -> login
            Product Listing -> product_listing
        """

        feature_name = feature.get("feature_name", "feature")
        slug = feature_name.lower().strip()
        slug = re.sub(r"[^a-z0-9]+", "_", slug)
        slug = slug.strip("_")

        return slug or "feature"

    def _build_fallback_architecture_output(
        self,
        agent_input: ArchitectureAgentInput,
        reason: str
    ) -> dict:
        """
        Build fallback architecture output if LLM fails or generates weak UML.

        This fallback is dynamic.
        It reads the approved SRS and builds use cases from:
        - user roles
        - functional requirements
        - acceptance criteria
        - validation rules
        - non-functional requirements
        - constraints
        - risks

        This avoids weak diagrams such as:
            Customer -> Use Login Feature
        """

        srs = agent_input.enhanced_srs_json or agent_input.srs_json
        feature = agent_input.feature
        project = agent_input.project

        feature_name = feature.get("feature_name", srs.get("feature_name", "Feature"))
        feature_id = feature.get("feature_id", srs.get("feature_id", "feature"))
        project_id = project.get("project_id", srs.get("project_id", "project"))
        project_name = project.get("project_name", srs.get("project_name", "Project"))

        user_roles = srs.get("user_roles", ["User"])
        functional_requirements = srs.get("functional_requirements", [])
        acceptance_criteria = srs.get("acceptance_criteria", [])
        validation_rules = srs.get("validation_rules", [])
        non_functional_requirements = srs.get("non_functional_requirements", [])
        constraints = srs.get("constraints", [])
        risks = srs.get("risks", [])

        main_uc_id = "UC-001"

        actors = self._build_fallback_actors(user_roles)

        use_cases = [
            {
                "id": main_uc_id,
                "name": feature_name,
                "description": f"Main use case for the {feature_name} feature.",
                "category": "main",
                "related_requirements": self._collect_requirement_ids(functional_requirements),
            }
        ]

        relationships = []

        # Connect each SRS user role to the main use case.
        for actor in actors:
            relationships.append({
                "from": actor["id"],
                "to": main_uc_id,
                "type": "association",
                "label": "",
                "related_requirements": []
            })

        include_counter = 2
        extend_counter = 100

        mandatory_included_behaviours = []
        alternative_flows = []
        exception_flows = []
        validation_flows = []
        security_flows = []
        diagram_notes = []

        # Convert validation rules into <<include>> use cases.
        for rule in validation_rules:
            rule_id = (
                rule.get("id", f"VR-{include_counter:03d}")
                if isinstance(rule, dict)
                else f"VR-{include_counter:03d}"
            )

            rule_text = (
                rule.get("description", str(rule))
                if isinstance(rule, dict)
                else str(rule)
            )

            uc_id = f"UC-{include_counter:03d}"
            uc_name = self._build_validation_usecase_name(rule_text)

            use_cases.append({
                "id": uc_id,
                "name": uc_name,
                "description": rule_text,
                "category": "included",
                "related_requirements": [rule_id],
            })

            relationships.append({
                "from": main_uc_id,
                "to": uc_id,
                "type": "include",
                "label": "",
                "related_requirements": [rule_id],
            })

            validation_flows.append({
                "name": uc_name,
                "rule": rule_text,
                "related_requirements": [rule_id],
            })

            include_counter += 1

        # Convert functional requirements into include or extend use cases.
        for requirement in functional_requirements:
            if not isinstance(requirement, dict):
                continue

            req_id = requirement.get("id", "")
            description = requirement.get("description", "")
            description_lower = description.lower()

            if self._is_optional_or_recovery_requirement(description_lower):
                uc_id = f"UC-{extend_counter:03d}"
                uc_name = self._build_recovery_usecase_name(description, feature_name)

                use_cases.append({
                    "id": uc_id,
                    "name": uc_name,
                    "description": description,
                    "category": "extension",
                    "related_requirements": [req_id],
                })

                relationships.append({
                    "from": uc_id,
                    "to": main_uc_id,
                    "type": "extend",
                    "label": "optional/recovery flow",
                    "related_requirements": [req_id],
                })

                alternative_flows.append({
                    "name": uc_name,
                    "condition": description,
                    "related_requirements": [req_id],
                })

                extend_counter += 1

            elif self._is_mandatory_internal_requirement(description_lower):
                uc_id = f"UC-{include_counter:03d}"
                uc_name = self._build_mandatory_usecase_name(description, feature_name)

                use_cases.append({
                    "id": uc_id,
                    "name": uc_name,
                    "description": description,
                    "category": "included",
                    "related_requirements": [req_id],
                })

                relationships.append({
                    "from": main_uc_id,
                    "to": uc_id,
                    "type": "include",
                    "label": "",
                    "related_requirements": [req_id],
                })

                mandatory_included_behaviours.append({
                    "name": uc_name,
                    "reason": description,
                    "related_requirements": [req_id],
                })

                include_counter += 1

        # Convert acceptance criteria into extension/error flows.
        for criterion in acceptance_criteria:
            if not isinstance(criterion, dict):
                continue

            ac_id = criterion.get("id", "")
            description = criterion.get("description", "")
            description_lower = description.lower()

            if self._is_error_acceptance_criterion(description_lower):
                uc_id = f"UC-{extend_counter:03d}"
                uc_name = self._build_error_usecase_name(description)

                use_cases.append({
                    "id": uc_id,
                    "name": uc_name,
                    "description": description,
                    "category": "extension",
                    "related_requirements": [ac_id],
                })

                relationships.append({
                    "from": uc_id,
                    "to": main_uc_id,
                    "type": "extend",
                    "label": "error flow",
                    "related_requirements": [ac_id],
                })

                exception_flows.append({
                    "name": uc_name,
                    "condition": description,
                    "related_requirements": [ac_id],
                })

                extend_counter += 1

            elif self._is_recovery_acceptance_criterion(description_lower):
                uc_id = f"UC-{extend_counter:03d}"
                uc_name = self._build_recovery_usecase_name(description, feature_name)

                use_cases.append({
                    "id": uc_id,
                    "name": uc_name,
                    "description": description,
                    "category": "extension",
                    "related_requirements": [ac_id],
                })

                relationships.append({
                    "from": uc_id,
                    "to": main_uc_id,
                    "type": "extend",
                    "label": "alternative flow",
                    "related_requirements": [ac_id],
                })

                alternative_flows.append({
                    "name": uc_name,
                    "condition": description,
                    "related_requirements": [ac_id],
                })

                extend_counter += 1

        # Constraints, NFRs, and risks should be notes, not actors.
        note_description_parts = []

        if constraints:
            note_description_parts.append(
                "Constraints: " + "; ".join(map(str, constraints))
            )

        if non_functional_requirements:
            readable_nfrs = [
                item.get("description", str(item))
                if isinstance(item, dict)
                else str(item)
                for item in non_functional_requirements
            ]

            note_description_parts.append(
                "NFRs: " + "; ".join(readable_nfrs)
            )

        if risks:
            readable_risks = [
                item.get("risk", str(item))
                if isinstance(item, dict)
                else str(item)
                for item in risks
            ]

            note_description_parts.append(
                "Risks: " + "; ".join(readable_risks)
            )

        if note_description_parts:
            diagram_notes.append({
                "title": "Architecture and Quality Notes",
                "description": " | ".join(note_description_parts),
                "related_requirements": self._collect_requirement_ids(non_functional_requirements),
            })

        notes = []

        for index, note in enumerate(diagram_notes, start=1):
            notes.append({
                "id": f"NOTE-{index:03d}",
                "target": main_uc_id,
                "title": note["title"],
                "description": note["description"],
                "related_requirements": note["related_requirements"],
            })

        sds_json = {
            "project_id": project_id,
            "project_name": project_name,
            "project_type": project.get("project_type", srs.get("project_type", "General")),
            "feature_id": feature_id,
            "feature_name": feature_name,
            "target_stack": project.get("target_stack", srs.get("target_stack", "MERN")),
            "architecture_style": srs.get(
                "architectural_style",
                srs.get("architecture_style", "mvc")
            ),
            "feature_design_overview": (
                f"SDS for the {feature_name} feature. "
                "This fallback SDS was generated from the approved SRS because "
                "the LLM output was invalid or too weak."
            ),
            "frontend_responsibilities": [
                f"Provide user interface for {feature_name}.",
                "Validate user input before sending request.",
                "Display success, validation, and error feedback clearly."
            ],
            "backend_responsibilities": [
                f"Process {feature_name} request.",
                "Validate request data.",
                "Apply required business rules.",
                "Return structured success or error responses."
            ],
            "database_design": {
                "collections": [
                    "Use existing user/account-related collection where applicable."
                ],
                "data_notes": [
                    "Store and retrieve only required feature data.",
                    "Do not expose sensitive data in responses."
                ]
            },
            "api_design_summary": self._build_fallback_api_summary(srs, feature_name),
            "data_flow": [
                "Actor starts the feature action from the frontend.",
                "Frontend validates required inputs.",
                "Frontend sends request to backend endpoint.",
                "Backend validates input and performs business logic.",
                "Backend accesses required database records.",
                "Backend returns success or error response.",
                "Frontend displays the result."
            ],
            "error_handling_design": [
                "Return clear validation error messages.",
                "Return generic authentication/business errors where needed.",
                "Prevent sensitive internal details from being exposed."
            ],
            "authentication_authorization_design": [
                "Apply authentication/authorization behaviour required by the SRS.",
                "Use token-based session handling if specified."
            ],
            "folder_structure_suggestion": [
                "frontend/src/pages/",
                "frontend/src/components/",
                "backend/src/controllers/",
                "backend/src/routes/",
                "backend/src/services/",
                "backend/src/models/"
            ],
            "dependency_list": [
                "React",
                "Express.js",
                "MongoDB",
                "Mongoose",
                "Axios",
                "JWT library if authentication is required"
            ],
            "integration_with_previous_features": [
                "Preserve already approved features.",
                "Do not rewrite unrelated modules."
            ],
            "scalability_notes": [
                "Keep feature logic modular.",
                "Use service layer for business logic.",
                "Use database indexes where needed."
            ],
            "assumptions": [
                f"Fallback architecture generated because: {reason}"
            ],
            "constraints": constraints,
            "traceability": self._build_fallback_sds_traceability(functional_requirements)
        }

        usecase_analysis_json = {
            "feature_goal": f"Support the {feature_name} feature according to the approved SRS.",
            "primary_actors": [
                actor["name"]
                for actor in actors
                if actor.get("type") == "primary"
            ],
            "secondary_actors": [
                actor["name"]
                for actor in actors
                if actor.get("type") != "primary"
            ],
            "main_success_scenario": [
                f"Actor initiates {feature_name}.",
                "System validates mandatory inputs.",
                "System processes the request.",
                "System returns successful response if all rules pass."
            ],
            "mandatory_included_behaviours": mandatory_included_behaviours,
            "alternative_flows": alternative_flows,
            "exception_flows": exception_flows,
            "validation_flows": validation_flows,
            "security_flows": security_flows,
            "diagram_notes": diagram_notes,
            "traceability": self._build_fallback_usecase_traceability(
                use_cases=use_cases,
                relationships=relationships,
                notes=notes
            )
        }

        usecase_json = {
            "system_boundary": f"{feature_name} Feature",
            "diagram_title": f"{feature_name} Use Case Diagram",
            "actors": actors,
            "use_cases": use_cases,
            "relationships": relationships,
            "notes": notes,
            "standards_notes": [
                "Actors are external roles.",
                "Use cases are inside the system boundary.",
                "<<include>> is used for mandatory behaviour.",
                "<<extend>> is used for optional, alternative, or error behaviour.",
                "Constraints and NFRs are represented as notes."
            ]
        }

        return {
            "sds_json": sds_json,
            "usecase_analysis_json": usecase_analysis_json,
            "usecase_json": usecase_json
        }

    def _build_fallback_actors(self, user_roles: list) -> list[dict]:
        """
        Build actors from SRS user roles.

        Example:
            Customer -> ACT-001
            Admin -> ACT-002
        """

        actors = []

        for index, role in enumerate(user_roles, start=1):
            role_name = str(role)

            actors.append({
                "id": f"ACT-{index:03d}",
                "name": role_name,
                "type": "primary" if index == 1 else "secondary",
                "description": f"{role_name} interacts with this feature."
            })

        if not actors:
            actors.append({
                "id": "ACT-001",
                "name": "User",
                "type": "primary",
                "description": "Default actor."
            })

        return actors

    def _collect_requirement_ids(self, items: list) -> list[str]:
        """
        Collect IDs from SRS items.

        Works for:
        - FR
        - AC
        - VR
        - NFR
        """

        ids = []

        for item in items:
            if isinstance(item, dict) and item.get("id"):
                ids.append(item["id"])

        return ids

    def _is_mandatory_internal_requirement(self, text: str) -> bool:
        """
        Detect functional requirements that should become <<include>> use cases.

        These are mandatory behaviours needed to complete the main use case.
        """

        keywords = [
            "validate",
            "generate",
            "return",
            "verify",
            "check",
            "authenticate",
            "token",
            "jwt",
            "credential",
        ]

        return any(keyword in text for keyword in keywords)

    def _is_optional_or_recovery_requirement(self, text: str) -> bool:
        """
        Detect requirements that should become <<extend>> use cases.

        These are optional, alternative, or recovery behaviours.
        """

        keywords = [
            "forgot",
            "recover",
            "reset",
            "optional",
            "alternative",
            "re-enter",
            "retry",
        ]

        return any(keyword in text for keyword in keywords)

    def _is_error_acceptance_criterion(self, text: str) -> bool:
        """
        Detect error/exception acceptance criteria.
        """

        keywords = [
            "invalid",
            "error",
            "failed",
            "prevent access",
            "incorrect",
            "denied",
        ]

        return any(keyword in text for keyword in keywords)

    def _is_recovery_acceptance_criterion(self, text: str) -> bool:
        """
        Detect recovery or alternative acceptance criteria.
        """

        keywords = [
            "forgot",
            "recover",
            "reset",
            "directed",
            "re-enter",
            "retry",
        ]

        return any(keyword in text for keyword in keywords)

    def _build_validation_usecase_name(self, rule_text: str) -> str:
        """
        Build readable validation use case name.

        Example:
            Email must conform to email regex -> Validate email format
        """

        text = rule_text.lower()

        if "email" in text:
            return "Validate email format"

        if "password" in text:
            return "Validate password rule"

        return "Validate input"

    def _build_mandatory_usecase_name(
        self,
        description: str,
        feature_name: str
    ) -> str:
        """
        Build included use case name from functional requirement.
        """

        text = description.lower()

        if "credential" in text:
            return "Validate credentials"

        if "jwt" in text or "token" in text:
            return "Generate authentication token"

        if "authenticate" in text:
            return f"Authenticate {feature_name} request"

        if "validate" in text:
            return "Validate submitted data"

        return f"Process {feature_name} rule"

    def _build_recovery_usecase_name(
        self,
        description: str,
        feature_name: str
    ) -> str:
        """
        Build extension use case name for recovery/optional flows.
        """

        text = description.lower()

        if "forgot password" in text:
            return "Initiate forgot password"

        if "forgot username" in text:
            return "Initiate forgot username"

        if "reset" in text:
            return "Initiate recovery flow"

        return f"Alternative {feature_name} flow"

    def _build_error_usecase_name(self, description: str) -> str:
        """
        Build extension use case name for error flows.
        """

        text = description.lower()

        if "invalid" in text and "credential" in text:
            return "Show invalid credential error"

        if "error" in text:
            return "Show error message"

        return "Handle failed scenario"

    def _build_fallback_api_summary(
        self,
        srs: dict,
        feature_name: str
    ) -> list[dict]:
        """
        Build SDS-level API summary from SRS API expectations.

        Important:
        This is not a separate API contract.
        It is only part of the SDS.
        """

        api_expectations = srs.get("api_expectations", [])
        summary = []

        for item in api_expectations:
            if isinstance(item, dict):
                summary.append({
                    "endpoint": item.get("endpoint", f"/api/{feature_name.lower()}"),
                    "method": item.get("method", "POST"),
                    "purpose": item.get("payload", f"Support {feature_name} feature."),
                    "related_requirements": []
                })

        if not summary:
            summary.append({
                "endpoint": f"/api/{feature_name.lower()}",
                "method": "POST",
                "purpose": f"Support {feature_name} feature.",
                "related_requirements": []
            })

        return summary

    def _build_fallback_sds_traceability(
        self,
        functional_requirements: list
    ) -> list[dict]:
        """
        Build SDS traceability from functional requirements.
        """

        traceability = []

        for requirement in functional_requirements:
            if not isinstance(requirement, dict):
                continue

            traceability.append({
                "requirement_id": requirement.get("id", "FR-000"),
                "sds_section": "Feature Design Overview",
                "design_decision": requirement.get(
                    "description",
                    "Requirement handled in SDS."
                )
            })

        return traceability

    def _build_fallback_usecase_traceability(
        self,
        use_cases: list[dict],
        relationships: list[dict],
        notes: list[dict]
    ) -> list[dict]:
        """
        Build traceability records for usecase_analysis_json.
        """

        traceability = []

        for use_case in use_cases:
            for requirement_id in use_case.get("related_requirements", []):
                traceability.append({
                    "source_id": requirement_id,
                    "source_type": self._guess_source_type(requirement_id),
                    "mapped_to": use_case.get("name", use_case.get("id")),
                    "mapping_type": "use_case"
                })

        for relationship in relationships:
            for requirement_id in relationship.get("related_requirements", []):
                traceability.append({
                    "source_id": requirement_id,
                    "source_type": self._guess_source_type(requirement_id),
                    "mapped_to": f"{relationship.get('from')} -> {relationship.get('to')}",
                    "mapping_type": relationship.get("type", "relationship")
                })

        for note in notes:
            for requirement_id in note.get("related_requirements", []):
                traceability.append({
                    "source_id": requirement_id,
                    "source_type": self._guess_source_type(requirement_id),
                    "mapped_to": note.get("title", note.get("id")),
                    "mapping_type": "note"
                })

        return traceability

    def _guess_source_type(self, requirement_id: str) -> str:
        """
        Guess traceability source type from ID prefix.
        """

        if requirement_id.startswith("FR"):
            return "FR"

        if requirement_id.startswith("AC"):
            return "AC"

        if requirement_id.startswith("VR"):
            return "VR"

        if requirement_id.startswith("NFR"):
            return "NFR"

        return "Requirement"


architecture_agent = ArchitectureAgent()