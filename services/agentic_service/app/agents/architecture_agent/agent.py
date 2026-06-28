"""
Architecture Agent.

Purpose:
- Load approved SRS JSON from Requirement Agent.
- Optionally load approved Enhanced SRS JSON from Domain Agent.
- Generate IEEE 1016-style SDS JSON and usecase_specification_json using LLM.
- Derive UML Use Case, Sequence, and Class diagram models from SRS/SDS.
- Validate SDS coverage against SRS.
- Validate UML diagram quality.
- Convert SDS JSON into Markdown.
- Convert diagram JSON into PlantUML.
- Render PlantUML into PNG.
- Save all Architecture Agent artifacts.

Important:
This implementation does not generate:
- API contract JSON
- OpenAPI YAML
- code
- UI
- component diagram

This implementation now generates:
- use case diagram
- sequence diagram
- class diagram

Outputs:
- SDS Markdown
- SDS JSON
- Use Case Diagram PUML
- Use Case Diagram PNG
- Sequence Diagram PUML
- Sequence Diagram PNG
- Class Diagram PUML
- Class Diagram PNG
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
from app.agents.architecture_agent.sds_validator import (
    ArchitectureSDSValidator,
    SDSValidationError,
)
from app.agents.architecture_agent.usecase_modeler import ArchitectureUseCaseModeler
from app.agents.architecture_agent.usecase_builder import ArchitectureUseCasePlantUMLBuilder
from app.agents.architecture_agent.usecase_renderer import UseCaseDiagramRenderer
from app.agents.architecture_agent.usecase_validator import (
    UseCaseQualityValidator,
    UseCaseValidationError,
)
from app.agents.architecture_agent.sequence_modeler import ArchitectureSequenceModeler
from app.agents.architecture_agent.sequence_builder import ArchitectureSequencePlantUMLBuilder
from app.agents.architecture_agent.sequence_validator import (
    SequenceDiagramValidator,
    SequenceDiagramValidationError,
)
from app.agents.architecture_agent.class_modeler import ArchitectureClassModeler
from app.agents.architecture_agent.class_builder import ArchitectureClassPlantUMLBuilder
from app.agents.architecture_agent.class_validator import (
    ClassDiagramValidator,
    ClassDiagramValidationError,
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
    3. IEEE-style SDS validation.
    4. UML use case, sequence, and class diagram validation.
    5. SDS Markdown generation.
    6. PlantUML generation.
    7. PNG rendering.
    8. Artifact saving.
    """

    REQUIRED_TOP_LEVEL_KEYS = [
        "sds_json",
    ]

    REQUIRED_SDS_KEYS = [
        "document_control",
        "introduction",
        "design_context",
        "design_considerations",
        "architecture_overview",
        "design_views",
        "detailed_design_decisions",
        "traceability_matrix",
        "assumptions",
        "constraints",
        "risks",
        "dependencies",
        "use_case_diagram_reference",
        "human_approval_note",
    ]

    REQUIRED_DESIGN_VIEW_KEYS = [
        "context_view",
        "logical_view",
        "interface_view",
        "data_view",
        "behavior_view",
        "error_handling_view",
        "security_authorization_view",
        "quality_attributes_view",
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

        These helpers are Architecture-Agent-specific.
        No common/shared files are changed.
        """

        self.markdown_builder = ArchitectureSDSMarkdownBuilder()
        self.sds_validator = ArchitectureSDSValidator()

        # Use Case pipeline:
        # LLM/specification -> modeler -> validator -> PlantUML builder -> PNG renderer
        self.usecase_modeler = ArchitectureUseCaseModeler()
        self.usecase_builder = ArchitectureUseCasePlantUMLBuilder()
        self.usecase_validator = UseCaseQualityValidator()

        # Sequence diagram pipeline:
        # SRS/SDS -> modeler -> validator -> PlantUML builder -> PNG renderer
        self.sequence_modeler = ArchitectureSequenceModeler()
        self.sequence_builder = ArchitectureSequencePlantUMLBuilder()
        self.sequence_validator = SequenceDiagramValidator()

        # Class diagram pipeline:
        # SRS/SDS -> modeler -> validator -> PlantUML builder -> PNG renderer
        self.class_modeler = ArchitectureClassModeler()
        self.class_builder = ArchitectureClassPlantUMLBuilder()
        self.class_validator = ClassDiagramValidator()

        # Existing renderer can render any PlantUML file into PNG.
        self.diagram_renderer = UseCaseDiagramRenderer()

    async def run(self, feature_id: str, request: ArchitectureAgentRunRequest) -> AgentRunResponse:
        """
        Run Architecture Agent for one feature.

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

        if request.use_enhanced_srs_if_available:
            enhanced_srs_artifact = self._find_latest_approved_artifact(
                feature_id=feature_id,
                agent_name=AgentName.DOMAIN,
                artifact_type=ArtifactType.ENHANCED_SRS,
                artifact_format=ArtifactFormat.JSON
            )

            if enhanced_srs_artifact:
                enhanced_srs_json = read_json_file(enhanced_srs_artifact["file_path"])

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
                "IEEE-style SDS, Use Case Diagram, Sequence Diagram, and Class Diagram artifacts were generated. "
                "Human approval is required before UI/UX Agent can run."
            ),
            artifact_ids=artifact_ids
        )

    async def _generate_architecture_output(self, agent_input: ArchitectureAgentInput) -> ArchitectureAgentOutput:
        """
        Generate Architecture Agent output.

        Flow:
        1. Ask LLM for JSON only.
        2. Parse and validate JSON structure.
        3. Validate SDS against approved SRS.
        4. Build and validate use case, sequence, and class diagrams.
        5. If LLM output is invalid, repair once.
        6. If still invalid, build dynamic IEEE-style fallback from SRS.
        7. Convert SDS JSON to Markdown.
        8. Convert diagram JSON models to PlantUML.
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
            parsed = self._parse_and_validate_output(raw_output)
            parsed = self._complete_usecase_model(agent_input, parsed)
            parsed = self._complete_sequence_model(agent_input, parsed)
            parsed = self._complete_class_model(agent_input, parsed)
            self._validate_full_output(agent_input, parsed)

        except Exception as first_error:
            logger.warning("Architecture output validation failed: %s", first_error)

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
                parsed = self._complete_usecase_model(agent_input, parsed)
                parsed = self._complete_sequence_model(agent_input, parsed)
                parsed = self._complete_class_model(agent_input, parsed)
                self._validate_full_output(agent_input, parsed)
                raw_output = repaired_output

            except Exception as second_error:
                logger.warning("Architecture JSON repair failed: %s", second_error)

                parsed = self._build_fallback_architecture_output(
                    agent_input=agent_input,
                    reason=str(second_error)
                )
                parsed = self._complete_usecase_model(agent_input, parsed)
                parsed = self._complete_sequence_model(agent_input, parsed)
                parsed = self._complete_class_model(agent_input, parsed)

                # The fallback is generated from SRS, so it should still be validated.
                self._validate_full_output(agent_input, parsed)

                raw_output = json.dumps(parsed, indent=2, default=str)

        sds_json = parsed["sds_json"]
        usecase_analysis_json = parsed["usecase_analysis_json"]
        usecase_json = parsed["usecase_json"]
        sequence_diagram_json = parsed["sequence_diagram_json"]
        class_diagram_json = parsed["class_diagram_json"]

        sds_markdown = self.markdown_builder.build(sds_json)
        usecase_puml = self.usecase_builder.build(usecase_json)
        sequence_puml = self.sequence_builder.build(sequence_diagram_json)
        class_puml = self.class_builder.build(class_diagram_json)

        return ArchitectureAgentOutput(
            sds_json=sds_json,
            sds_markdown=sds_markdown,
            usecase_analysis_json=usecase_analysis_json,
            usecase_json=usecase_json,
            usecase_puml=usecase_puml,
            sequence_diagram_json=sequence_diagram_json,
            sequence_puml=sequence_puml,
            class_diagram_json=class_diagram_json,
            class_puml=class_puml,
            raw_llm_output=raw_output
        )

    def _complete_usecase_model(
        self,
        agent_input: ArchitectureAgentInput,
        parsed: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Build the final use case model using the dedicated modeler.

        The LLM may provide usecase_specification_json, usecase_analysis_json,
        or usecase_json. However, the final diagram must always pass through
        ArchitectureUseCaseModeler so that actors, use cases, relationships,
        and notes are normalized using feature-independent UML rules.
        """

        srs_for_modeling = agent_input.enhanced_srs_json or agent_input.srs_json

        usecase_specification_json = parsed.get("usecase_specification_json")

        if not isinstance(usecase_specification_json, dict):
            usecase_specification_json = {}

        usecase_analysis_json, usecase_json = self.usecase_modeler.build(
            srs_json=srs_for_modeling,
            sds_json=parsed["sds_json"],
            usecase_specification_json=usecase_specification_json,
        )

        parsed["usecase_specification_json"] = usecase_specification_json
        parsed["usecase_analysis_json"] = usecase_analysis_json
        parsed["usecase_json"] = usecase_json

        self._ensure_keys(usecase_json, self.REQUIRED_USECASE_KEYS)
        self._validate_usecase_json(usecase_json)

        return parsed

    def _complete_sequence_model(
        self,
        agent_input: ArchitectureAgentInput,
        parsed: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Build the sequence diagram model from approved SRS/SDS.

        The LLM does not directly control this diagram.
        This keeps the sequence diagram deterministic and aligned with the SDS.
        """

        srs_for_modeling = agent_input.enhanced_srs_json or agent_input.srs_json

        sequence_diagram_json = self.sequence_modeler.build(
            srs_json=srs_for_modeling,
            sds_json=parsed["sds_json"],
        )

        parsed["sequence_diagram_json"] = sequence_diagram_json

        return parsed

    def _complete_class_model(
        self,
        agent_input: ArchitectureAgentInput,
        parsed: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Build the class diagram model from approved SRS/SDS.

        The class diagram is derived from the SDS logical, interface,
        and data views rather than directly from free-form LLM PlantUML.
        """

        srs_for_modeling = agent_input.enhanced_srs_json or agent_input.srs_json

        class_diagram_json = self.class_modeler.build(
            srs_json=srs_for_modeling,
            sds_json=parsed["sds_json"],
        )

        parsed["class_diagram_json"] = class_diagram_json

        return parsed

    def _validate_full_output(
        self,
        agent_input: ArchitectureAgentInput,
        parsed: dict[str, Any]
    ) -> None:
        """
        Run full SDS and Use Case validations.
        """

        srs_for_validation = agent_input.enhanced_srs_json or agent_input.srs_json

        self.sds_validator.validate(
            srs_json=srs_for_validation,
            sds_json=parsed["sds_json"]
        )

        self.usecase_validator.validate(
            srs_json=srs_for_validation,
            sds_json=parsed["sds_json"],
            usecase_analysis_json=parsed["usecase_analysis_json"],
            usecase_json=parsed["usecase_json"],
        )

        self.sequence_validator.validate(
            srs_json=srs_for_validation,
            sequence_json=parsed["sequence_diagram_json"],
        )

        self.class_validator.validate(
            srs_json=srs_for_validation,
            class_json=parsed["class_diagram_json"],
        )

    def _parse_and_validate_output(self, raw_output: str) -> dict[str, Any]:
        """
        Parse and validate Architecture Agent JSON structure.
        """

        parsed = self._extract_json_object(raw_output)

        self._ensure_keys(parsed, self.REQUIRED_TOP_LEVEL_KEYS)

        sds_json = parsed.get("sds_json")

        if not isinstance(sds_json, dict):
            raise ValueError("sds_json must be a JSON object.")

        self._ensure_keys(sds_json, self.REQUIRED_SDS_KEYS)

        design_views = sds_json.get("design_views", {})

        if not isinstance(design_views, dict):
            raise ValueError("sds_json.design_views must be a JSON object.")

        self._ensure_keys(design_views, self.REQUIRED_DESIGN_VIEW_KEYS)

        # Use case output is intentionally completed by _complete_usecase_model().
        # This prevents weak or random LLM usecase_json from becoming the final diagram.
        return parsed

    def _extract_json_object(self, text: str) -> dict[str, Any]:
        """
        Extract JSON object from LLM output.
        """

        cleaned = text.strip()

        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in Architecture Agent output.")

        return json.loads(cleaned[start:end + 1])

    def _ensure_keys(self, data: dict[str, Any], required_keys: list[str]) -> None:
        """
        Validate required keys.
        """

        missing = [key for key in required_keys if key not in data]

        if missing:
            raise ValueError(f"Missing required keys: {missing}")

    def _validate_usecase_json(self, usecase_json: dict[str, Any]) -> None:
        """
        Validate basic use case diagram structure.
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
        Save Architecture Agent artifacts.

        Files:
        - {feature}_sds_v1.md
        - {feature}_sds_v1.json
        - {feature}_usecase_v1.puml / .png
        - {feature}_sequence_v1.puml / .png
        - {feature}_class_v1.puml / .png
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
        sequence_puml_path = stage_folder / f"{feature_slug}_sequence_v{version}.puml"
        class_puml_path = stage_folder / f"{feature_slug}_class_v{version}.puml"

        saved_sds_md = write_text_file(sds_md_path, output.sds_markdown)
        saved_sds_json = write_json_file(sds_json_path, output.sds_json)
        saved_puml = write_text_file(usecase_puml_path, output.usecase_puml)
        saved_sequence_puml = write_text_file(sequence_puml_path, output.sequence_puml)
        saved_class_puml = write_text_file(class_puml_path, output.class_puml)

        png_path = self.diagram_renderer.render_png(Path(saved_puml))
        sequence_png_path = self.diagram_renderer.render_png(Path(saved_sequence_puml))
        class_png_path = self.diagram_renderer.render_png(Path(saved_class_puml))

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

        artifact_ids.append(
            self._register_artifact(
                project=project,
                feature=feature,
                artifact_type=ArtifactType.SEQUENCE_DIAGRAM,
                artifact_format=ArtifactFormat.TEXT,
                file_path=saved_sequence_puml,
                version=version,
                created_at=created_at
            )
        )

        artifact_ids.append(
            self._register_artifact(
                project=project,
                feature=feature,
                artifact_type=ArtifactType.SEQUENCE_DIAGRAM,
                artifact_format=ArtifactFormat.PNG,
                file_path=str(sequence_png_path),
                version=version,
                created_at=created_at
            )
        )

        artifact_ids.append(
            self._register_artifact(
                project=project,
                feature=feature,
                artifact_type=ArtifactType.CLASS_DIAGRAM,
                artifact_format=ArtifactFormat.TEXT,
                file_path=saved_class_puml,
                version=version,
                created_at=created_at
            )
        )

        artifact_ids.append(
            self._register_artifact(
                project=project,
                feature=feature,
                artifact_type=ArtifactType.CLASS_DIAGRAM,
                artifact_format=ArtifactFormat.PNG,
                file_path=str(class_png_path),
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
        Register artifact metadata in store.
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
    ) -> dict[str, Any]:
        """
        Build dynamic IEEE-style fallback architecture output.

        This fallback is feature-independent.
        It reads the approved SRS and builds SDS sections from SRS fields.
        """

        srs = agent_input.enhanced_srs_json or agent_input.srs_json
        feature = agent_input.feature
        project = agent_input.project

        project_id = project.get("project_id", srs.get("project_id", "project"))
        project_name = project.get("project_name", srs.get("project_name", "Project"))
        project_type = project.get("project_type", srs.get("project_type", "General"))
        feature_id = feature.get("feature_id", srs.get("feature_id", "feature"))
        feature_name = feature.get("feature_name", srs.get("feature_name", "Feature"))
        target_stack = project.get("target_stack", srs.get("target_stack", "MERN"))
        architecture_style = srs.get("preferred_architectural_style", srs.get("architecture_style", srs.get("architectural_style", "mvc")))

        sds_json = self._build_ieee_sds_from_srs(
            srs=srs,
            project_id=project_id,
            project_name=project_name,
            project_type=project_type,
            feature_id=feature_id,
            feature_name=feature_name,
            target_stack=target_stack,
            architecture_style=architecture_style,
            reason=reason,
        )

        usecase_analysis_json, usecase_json = self._build_usecase_from_srs(
            srs=srs,
            feature_name=feature_name
        )

        return {
            "sds_json": sds_json,
            "usecase_analysis_json": usecase_analysis_json,
            "usecase_json": usecase_json
        }

    def _build_ieee_sds_from_srs(
        self,
        srs: dict[str, Any],
        project_id: str,
        project_name: str,
        project_type: str,
        feature_id: str,
        feature_name: str,
        target_stack: str,
        architecture_style: str,
        reason: str,
    ) -> dict[str, Any]:
        """
        Build IEEE-style SDS JSON from SRS.

        This method maps SRS sections into generic design views.
        """

        scope = self._as_text_list(srs.get("scope", []))
        out_of_scope = self._as_text_list(srs.get("out_of_scope", []))
        user_roles = self._as_text_list(srs.get("user_roles", []))
        assumptions = self._as_text_list(srs.get("assumptions", []))
        constraints = self._as_text_list(srs.get("constraints", []))
        dependencies = self._as_text_list(srs.get("dependencies", []))
        risks = self._as_record_list(srs.get("risks", []))
        nfrs = self._as_record_list(srs.get("non_functional_requirements", []))
        functional_requirements = self._as_record_list(srs.get("functional_requirements", []))
        acceptance_criteria = self._as_record_list(srs.get("acceptance_criteria", []))
        validation_rules = self._as_record_list(srs.get("validation_rules", []))
        api_expectations = self._as_record_list(srs.get("api_expectations", []))
        input_requirements = self._as_record_list(srs.get("input_requirements", []))
        output_requirements = self._as_record_list(srs.get("output_requirements", []))
        data_requirements = self._as_record_list(srs.get("data_requirements", []))
        ui_expectations = self._as_record_list(srs.get("ui_expectations", []))
        business_goal = srs.get("business_goal", f"Support the {feature_name} feature.")

        interface_view = self._build_interface_view(
            feature_name=feature_name,
            api_expectations=api_expectations,
            input_requirements=input_requirements,
            output_requirements=output_requirements,
            functional_requirements=functional_requirements,
        )

        data_view = self._build_data_view(
            feature_name=feature_name,
            data_requirements=data_requirements,
            validation_rules=validation_rules,
            functional_requirements=functional_requirements,
        )

        behavior_view = self._build_behavior_view(
            feature_name=feature_name,
            acceptance_criteria=acceptance_criteria,
            functional_requirements=functional_requirements,
        )

        error_handling_view = self._build_error_handling_view(
            validation_rules=validation_rules,
            acceptance_criteria=acceptance_criteria,
            nfrs=nfrs,
        )

        security_view = self._build_security_view(
            constraints=constraints,
            risks=risks,
            functional_requirements=functional_requirements,
            nfrs=nfrs,
        )

        quality_view = self._build_quality_view(nfrs=nfrs)

        traceability_matrix = self._build_sds_traceability_matrix(
            srs=srs,
            interface_view=interface_view,
            data_view=data_view,
            behavior_view=behavior_view,
            error_handling_view=error_handling_view,
            security_view=security_view,
            quality_view=quality_view,
        )

        srs_related_ids = self._collect_requirement_ids(functional_requirements)

        return {
            "document_control": {
                "document_title": f"Software Design Specification: {feature_name}",
                "document_type": "Software Design Specification",
                "standard_basis": "IEEE 1016-style Software Design Description",
                "project_id": project_id,
                "project_name": project_name,
                "project_type": project_type,
                "feature_id": feature_id,
                "feature_name": feature_name,
                "target_stack": target_stack,
                "architecture_style": architecture_style,
                "version": "v1",
                "generated_by": "Architecture Agent",
                "input_artifacts": ["Approved SRS JSON", "Approved Enhanced SRS JSON if available"],
                "approval_status": "pending"
            },
            "introduction": {
                "purpose": f"Describe the software design for the {feature_name} feature based on the approved SRS.",
                "scope": scope or [f"Design the approved {feature_name} feature only."],
                "out_of_scope": out_of_scope,
                "intended_audience": [
                    "Human reviewer",
                    "UI/UX Agent",
                    "Coder Agent",
                    "Project supervisor",
                    "Software engineering team"
                ],
                "definitions": self._build_definitions_from_srs(srs)
            },
            "design_context": {
                "business_goal": business_goal,
                "user_roles": user_roles,
                "feature_boundary": f"This SDS covers only the {feature_name} feature and excludes unrelated features.",
                "operating_environment": f"Generated application target stack: {target_stack}.",
                "dependencies": dependencies,
                "assumptions": assumptions
            },
            "design_considerations": {
                "constraints": constraints,
                "non_functional_requirements": nfrs,
                "risks": risks,
                "design_tradeoffs": [
                    "Design is derived directly from the approved SRS to preserve traceability and feature scope.",
                    "Design is kept feature-scoped to preserve feature-by-feature SDLC development.",
                    "Internal generation or repair details are kept in backend logs and are not exposed in the approval-ready SDS."
                ]
            },
            "architecture_overview": {
                "architecture_style": architecture_style,
                "architecture_rationale": (
                    f"Use {architecture_style} to keep the {feature_name} feature separated into presentation, "
                    "business logic, and data responsibilities where applicable."
                ),
                "frontend_overview": self._build_frontend_overview(ui_expectations, input_requirements),
                "backend_overview": self._build_backend_overview(functional_requirements, validation_rules),
                "data_overview": self._build_data_overview(data_requirements),
                "integration_overview": self._build_integration_overview(api_expectations, dependencies)
            },
            "design_views": {
                "context_view": {
                    "actors": user_roles,
                    "external_systems": dependencies,
                    "feature_boundary": f"{feature_name} feature boundary.",
                    "main_interactions": self._build_main_interactions(user_roles, functional_requirements, feature_name)
                },
                "logical_view": {
                    "frontend_modules": self._build_logical_modules("frontend", feature_name, ui_expectations, input_requirements),
                    "backend_modules": self._build_logical_modules("backend", feature_name, functional_requirements, validation_rules),
                    "domain_services": self._build_domain_services(feature_name, functional_requirements),
                    "data_modules": self._build_data_modules(feature_name, data_requirements),
                    "integration_points": self._build_integration_points(api_expectations, dependencies)
                },
                "interface_view": interface_view,
                "data_view": data_view,
                "behavior_view": behavior_view,
                "error_handling_view": error_handling_view,
                "security_authorization_view": security_view,
                "quality_attributes_view": quality_view
            },
            "detailed_design_decisions": self._build_design_decisions(
                feature_name=feature_name,
                functional_requirements=functional_requirements,
                acceptance_criteria=acceptance_criteria,
                validation_rules=validation_rules,
                nfrs=nfrs,
                risks=risks,
                api_expectations=api_expectations,
                data_requirements=data_requirements,
            ),
            "traceability_matrix": traceability_matrix,
            "assumptions": assumptions,
            "constraints": constraints,
            "risks": risks,
            "dependencies": dependencies,
            "use_case_diagram_reference": {
                "puml_file": "Generated as a separate Architecture Agent artifact.",
                "png_file": "Generated as a separate Architecture Agent artifact.",
                "diagram_scope": f"Feature-level use case diagram for {feature_name}.",
                "actors": user_roles,
                "main_use_cases": [feature_name],
                "relationship_summary": [
                    "Associations connect actors to main use cases.",
                    "Include relationships represent mandatory supporting behaviours.",
                    "Extend relationships represent optional, alternative, or exception behaviours."
                ]
            },
            "human_approval_note": "This SDS must be reviewed and approved before the UI/UX Agent starts."
        }

    def _build_interface_view(
        self,
        feature_name: str,
        api_expectations: list[dict[str, Any]],
        input_requirements: list[dict[str, Any]],
        output_requirements: list[dict[str, Any]],
        functional_requirements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Build interface view generically from API/input/output requirements.
        """

        request_model_name = f"{self._pascal_case(feature_name)}Request"
        success_model_name = f"{self._pascal_case(feature_name)}SuccessResponse"
        error_model_name = f"{self._pascal_case(feature_name)}ErrorResponse"

        request_model = {
            "name": request_model_name,
            "fields": [
                {
                    "name": item.get("field", item.get("name", "field")),
                    "type": item.get("type", "string"),
                    "format": item.get("format", item.get("description", "")),
                    "required": True
                }
                for item in input_requirements
            ],
            "related_requirements": self._collect_requirement_ids(functional_requirements)
        }

        success_fields = []
        error_fields = []

        for item in output_requirements:
            field_text = str(item.get("field", item.get("name", item))).lower()

            field_record = {
                "name": item.get("field", item.get("name", "field")),
                "type": item.get("type", "string"),
                "description": item.get("description", "")
            }

            if "error" in field_text or "message" in field_text:
                error_fields.append(field_record)
            else:
                success_fields.append(field_record)

        if not success_fields and output_requirements:
            success_fields = output_requirements

        response_models = [
            {
                "name": success_model_name,
                "type": "success",
                "fields": success_fields,
                "related_requirements": self._collect_requirement_ids(functional_requirements)
            },
            {
                "name": error_model_name,
                "type": "error",
                "fields": error_fields,
                "related_requirements": []
            }
        ]

        endpoints = []

        for item in api_expectations:
            endpoint = item.get("endpoint", "")
            method = item.get("method", "GET")
            payload = item.get("payload", item.get("purpose", ""))
            related_ids = self._infer_related_requirement_ids_from_text(
                text=f"{endpoint} {method} {payload}",
                requirement_items=functional_requirements
            )

            endpoints.append({
                "endpoint": endpoint or f"/api/{self._slug(feature_name)}",
                "method": method,
                "purpose": payload or f"Support the {feature_name} feature.",
                "request_model": request_model_name,
                "success_response_model": success_model_name,
                "error_response_model": error_model_name,
                "related_requirements": related_ids
            })

        if not endpoints:
            endpoints.append({
                "endpoint": f"/api/{self._slug(feature_name)}",
                "method": "POST",
                "purpose": f"Support the {feature_name} feature.",
                "request_model": request_model_name,
                "success_response_model": success_model_name,
                "error_response_model": error_model_name,
                "related_requirements": self._collect_requirement_ids(functional_requirements)
            })

        return {
            "api_endpoints": endpoints,
            "request_models": [request_model],
            "response_models": response_models
        }

    def _build_data_view(
        self,
        feature_name: str,
        data_requirements: list[dict[str, Any]],
        validation_rules: list[dict[str, Any]],
        functional_requirements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Build data view from data and validation requirements.
        """

        data_entities = []

        for index, item in enumerate(data_requirements, start=1):
            data_name = (
                item.get("data_point")
                or item.get("name")
                or item.get("field")
                or f"{feature_name}DataEntity{index}"
            )

            data_entities.append({
                "name": data_name,
                "purpose": item.get("description", f"Support data handling for {feature_name}."),
                "fields": self._infer_fields_from_text(item.get("description", str(item))),
                "relationships": [],
                "indexes_or_constraints": self._infer_data_constraints_from_text(item.get("description", str(item))),
                "related_requirements": self._infer_related_requirement_ids_from_text(
                    text=str(item),
                    requirement_items=functional_requirements
                )
            })

        if not data_entities:
            data_entities.append({
                "name": f"{self._pascal_case(feature_name)}Data",
                "purpose": f"Data needed to support the {feature_name} feature.",
                "fields": [],
                "relationships": [],
                "indexes_or_constraints": [],
                "related_requirements": self._collect_requirement_ids(functional_requirements)
            })

        return {
            "data_entities": data_entities,
            "storage_rules": [
                item.get("description", str(item))
                for item in data_requirements
            ] or [f"Store only data required for the {feature_name} feature."],
            "data_validation_rules": [
                {
                    "rule_id": item.get("id", f"VR-{index:03d}"),
                    "rule": item.get("description", str(item)),
                    "related_requirements": [item.get("id")] if item.get("id") else []
                }
                for index, item in enumerate(validation_rules, start=1)
            ]
        }

    def _build_behavior_view(
        self,
        feature_name: str,
        acceptance_criteria: list[dict[str, Any]],
        functional_requirements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Build behavior view from acceptance criteria and FRs.
        """

        main_success_flow = []
        alternative_flows = []
        exception_flows = []

        for item in acceptance_criteria:
            text = item.get("description", str(item))
            text_lower = text.lower()

            record = {
                "id": item.get("id", ""),
                "description": text,
                "related_requirements": self._infer_related_requirement_ids_from_text(text, functional_requirements)
            }

            if self._contains_any(text_lower, ["invalid", "error", "fail", "denied", "prevent"]):
                exception_flows.append(record)
            elif self._contains_any(text_lower, ["click", "optional", "alternative", "redirect", "directed", "recover", "forgot", "reset"]):
                alternative_flows.append(record)
            else:
                main_success_flow.append(record)

        if not main_success_flow:
            main_success_flow = [
                {
                    "step": 1,
                    "description": f"Actor initiates the {feature_name} feature.",
                    "related_requirements": self._collect_requirement_ids(functional_requirements)
                },
                {
                    "step": 2,
                    "description": "System validates the request according to approved SRS rules.",
                    "related_requirements": []
                },
                {
                    "step": 3,
                    "description": "System returns the expected result or a clear error response.",
                    "related_requirements": []
                }
            ]

        return {
            "main_success_flow": main_success_flow,
            "alternative_flows": alternative_flows,
            "exception_flows": exception_flows,
            "state_changes": self._infer_state_changes(feature_name, functional_requirements, acceptance_criteria)
        }

    def _build_error_handling_view(
        self,
        validation_rules: list[dict[str, Any]],
        acceptance_criteria: list[dict[str, Any]],
        nfrs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Build error handling view generically.
        """

        validation_errors = [
            {
                "source_id": item.get("id", ""),
                "condition": item.get("description", str(item)),
                "handling": "Return a clear validation message and prevent invalid processing."
            }
            for item in validation_rules
        ]

        business_errors = []
        authorization_errors = []

        for item in acceptance_criteria:
            text = item.get("description", str(item))
            text_lower = text.lower()

            if self._contains_any(text_lower, ["invalid", "error", "fail", "prevent", "incorrect"]):
                business_errors.append({
                    "source_id": item.get("id", ""),
                    "condition": text,
                    "handling": "Return a clear, user-friendly error and prevent the invalid action."
                })

            if self._contains_any(text_lower, ["unauthorized", "forbidden", "access", "permission"]):
                authorization_errors.append({
                    "source_id": item.get("id", ""),
                    "condition": text,
                    "handling": "Prevent unauthorized access and return an authorization-safe response."
                })

        user_message_rules = [
            item.get("description", str(item))
            for item in nfrs
            if "error" in str(item).lower() or "clear" in str(item).lower()
        ]

        return {
            "validation_errors": validation_errors,
            "business_errors": business_errors,
            "authorization_errors": authorization_errors,
            "system_errors": [
                "Unexpected system errors should return safe generic messages without exposing internal details."
            ],
            "user_message_rules": user_message_rules or [
                "All user-facing errors must be clear, non-technical, and aligned with the approved SRS."
            ]
        }

    def _build_security_view(
        self,
        constraints: list[str],
        risks: list[dict[str, Any]],
        functional_requirements: list[dict[str, Any]],
        nfrs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Build security/authorization view only from SRS-related security hints.
        """

        security_text = " ".join(map(str, constraints + risks + functional_requirements + nfrs)).lower()

        authentication_design = []
        authorization_design = []
        sensitive_data_rules = []

        if self._contains_any(security_text, ["auth", "login", "token", "jwt", "credential", "password"]):
            authentication_design.append(
                "Apply authentication behaviour required by the SRS and selected architecture."
            )

        if self._contains_any(security_text, ["role", "admin", "customer", "permission", "authorize", "access"]):
            authorization_design.append(
                "Apply role/access rules required by the SRS."
            )

        if self._contains_any(security_text, ["password", "token", "secret", "credential", "personal", "sensitive"]):
            sensitive_data_rules.append(
                "Sensitive values must not be exposed in responses, logs, or generated artifacts."
            )

        risk_mitigations = []

        for risk in risks:
            risk_mitigations.append({
                "risk": risk.get("risk", str(risk)),
                "mitigation": risk.get("mitigation", "Apply suitable mitigation based on project security policy."),
                "related_requirements": self._infer_related_requirement_ids_from_text(
                    text=str(risk),
                    requirement_items=functional_requirements
                )
            })

        return {
            "authentication_design": authentication_design,
            "authorization_design": authorization_design,
            "sensitive_data_rules": sensitive_data_rules,
            "risk_mitigations": risk_mitigations
        }

    def _build_quality_view(self, nfrs: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Build quality attributes view from NFR category or text.
        """

        quality_view = {
            "performance": [],
            "usability": [],
            "reliability": [],
            "scalability": [],
            "maintainability": [],
            "accessibility": []
        }

        for item in nfrs:
            description = item.get("description", str(item))
            category = str(item.get("category", "")).lower()
            text = f"{category} {description}".lower()

            record = {
                "nfr_id": item.get("id", ""),
                "description": description,
                "design_decision": self._quality_decision_from_nfr(description)
            }

            if "performance" in text or "fast" in text or "response" in text or "load" in text:
                quality_view["performance"].append(record)
            elif "usability" in text or "responsive" in text or "user" in text or "clear" in text:
                quality_view["usability"].append(record)
            elif "reliability" in text or "available" in text or "recover" in text:
                quality_view["reliability"].append(record)
            elif "scalability" in text or "scale" in text or "peak" in text:
                quality_view["scalability"].append(record)
            elif "accessibility" in text or "wcag" in text:
                quality_view["accessibility"].append(record)
            else:
                quality_view["maintainability"].append(record)

        return quality_view

    def _build_sds_traceability_matrix(
        self,
        srs: dict[str, Any],
        interface_view: dict[str, Any],
        data_view: dict[str, Any],
        behavior_view: dict[str, Any],
        error_handling_view: dict[str, Any],
        security_view: dict[str, Any],
        quality_view: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Build generic requirement-to-design traceability matrix.
        """

        traceability = []

        traceability.extend(self._trace_items(srs.get("functional_requirements", []), "FR", "Design Views / Detailed Design Decisions"))
        traceability.extend(self._trace_items(srs.get("acceptance_criteria", []), "AC", "Behavior View / Error Handling View"))
        traceability.extend(self._trace_items(srs.get("validation_rules", []), "VR", "Interface View / Data View / Error Handling View"))
        traceability.extend(self._trace_items(srs.get("non_functional_requirements", []), "NFR", "Quality Attributes View"))
        traceability.extend(self._trace_non_id_items(srs.get("constraints", []), "Constraint", "Design Considerations / Architecture Overview"))
        traceability.extend(self._trace_non_id_items(srs.get("risks", []), "Risk", "Design Considerations / Security and Authorization View"))
        traceability.extend(self._trace_non_id_items(srs.get("dependencies", []), "Dependency", "Design Context / Logical View"))
        traceability.extend(self._trace_non_id_items(srs.get("data_requirements", []), "Data", "Data View"))
        traceability.extend(self._trace_non_id_items(srs.get("api_expectations", []), "API", "Interface View"))
        traceability.extend(self._trace_non_id_items(srs.get("ui_expectations", []), "UI", "Context View / Logical View"))

        return traceability

    def _trace_items(self, items: list[Any], source_type: str, section: str) -> list[dict[str, Any]]:
        records = []

        for index, item in enumerate(items, start=1):
            if isinstance(item, dict):
                source_id = item.get("id", f"{source_type}-{index:03d}")
                description = item.get("description", str(item))
            else:
                source_id = f"{source_type}-{index:03d}"
                description = str(item)

            records.append({
                "source_id": source_id,
                "source_type": source_type,
                "sds_section": section,
                "design_element": description,
                "coverage_status": "covered"
            })

        return records

    def _trace_non_id_items(self, items: list[Any], source_type: str, section: str) -> list[dict[str, Any]]:
        records = []

        for index, item in enumerate(items, start=1):
            source_id = f"{source_type.upper()}-{index:03d}"
            description = self._item_description(item)

            records.append({
                "source_id": source_id,
                "source_type": source_type,
                "sds_section": section,
                "design_element": description,
                "coverage_status": "covered"
            })

        return records

    def _build_design_decisions(
        self,
        feature_name: str,
        functional_requirements: list[dict[str, Any]],
        acceptance_criteria: list[dict[str, Any]],
        validation_rules: list[dict[str, Any]],
        nfrs: list[dict[str, Any]],
        risks: list[dict[str, Any]],
        api_expectations: list[dict[str, Any]],
        data_requirements: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Build detailed design decisions from SRS items.
        """

        decisions = []
        counter = 1

        for group_name, items in [
            ("functional requirement", functional_requirements),
            ("acceptance criterion", acceptance_criteria),
            ("validation rule", validation_rules),
            ("non-functional requirement", nfrs),
            ("risk", risks),
            ("API expectation", api_expectations),
            ("data requirement", data_requirements),
        ]:
            for item in items:
                related_ids = [item.get("id")] if isinstance(item, dict) and item.get("id") else []

                decisions.append({
                    "decision_id": f"DD-{counter:03d}",
                    "decision": f"Design must address {group_name}: {self._item_description(item)}",
                    "rationale": f"This design decision is derived from the approved SRS {group_name}.",
                    "related_requirements": related_ids
                })

                counter += 1

        return decisions

    def _build_usecase_from_srs(
        self,
        srs: dict[str, Any],
        feature_name: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Build generic usecase_analysis_json and usecase_json from SRS.
        """

        user_roles = self._as_text_list(srs.get("user_roles", [])) or ["User"]
        functional_requirements = self._as_record_list(srs.get("functional_requirements", []))
        acceptance_criteria = self._as_record_list(srs.get("acceptance_criteria", []))
        validation_rules = self._as_record_list(srs.get("validation_rules", []))
        nfrs = self._as_record_list(srs.get("non_functional_requirements", []))
        constraints = self._as_text_list(srs.get("constraints", []))
        risks = self._as_record_list(srs.get("risks", []))

        actors = [
            {
                "id": f"ACT-{index:03d}",
                "name": role,
                "type": "primary" if index == 1 else "secondary",
                "description": f"{role} interacts with the {feature_name} feature."
            }
            for index, role in enumerate(user_roles, start=1)
        ]

        main_uc_id = "UC-001"

        use_cases = [
            {
                "id": main_uc_id,
                "name": self._verb_phrase_from_feature(feature_name),
                "description": f"Main user goal for the {feature_name} feature.",
                "category": "main",
                "related_requirements": self._collect_requirement_ids(functional_requirements)
            }
        ]

        relationships = [
            {
                "from": actor["id"],
                "to": main_uc_id,
                "type": "association",
                "label": "",
                "related_requirements": []
            }
            for actor in actors
        ]

        mandatory_behaviours = []
        alternative_flows = []
        exception_flows = []
        validation_flows = []
        security_flows = []

        next_uc_number = 2

        for rule in validation_rules:
            uc_id = f"UC-{next_uc_number:03d}"
            name = self._usecase_name_from_text(rule.get("description", str(rule)), prefix="Validate")

            use_cases.append({
                "id": uc_id,
                "name": name,
                "description": rule.get("description", str(rule)),
                "category": "included",
                "related_requirements": [rule.get("id")] if rule.get("id") else []
            })

            relationships.append({
                "from": main_uc_id,
                "to": uc_id,
                "type": "include",
                "label": "",
                "related_requirements": [rule.get("id")] if rule.get("id") else []
            })

            validation_flows.append({
                "name": name,
                "rule": rule.get("description", str(rule)),
                "related_requirements": [rule.get("id")] if rule.get("id") else []
            })

            next_uc_number += 1

        for requirement in functional_requirements:
            description = requirement.get("description", str(requirement))
            description_lower = description.lower()
            related_ids = [requirement.get("id")] if requirement.get("id") else []

            if self._contains_any(description_lower, ["optional", "alternative", "recover", "forgot", "reset", "retry"]):
                relationship_type = "extend"
                category = "extension"
                flow_target = alternative_flows
            elif self._contains_any(description_lower, ["invalid", "error", "fail", "prevent"]):
                relationship_type = "extend"
                category = "extension"
                flow_target = exception_flows
            elif self._contains_any(description_lower, ["validate", "check", "verify", "generate", "calculate", "confirm", "process"]):
                relationship_type = "include"
                category = "included"
                flow_target = mandatory_behaviours
            else:
                continue

            uc_id = f"UC-{next_uc_number:03d}"
            name = self._usecase_name_from_text(description)

            use_cases.append({
                "id": uc_id,
                "name": name,
                "description": description,
                "category": category,
                "related_requirements": related_ids
            })

            if relationship_type == "include":
                relationships.append({
                    "from": main_uc_id,
                    "to": uc_id,
                    "type": "include",
                    "label": "",
                    "related_requirements": related_ids
                })
            else:
                relationships.append({
                    "from": uc_id,
                    "to": main_uc_id,
                    "type": "extend",
                    "label": "alternative/exception flow",
                    "related_requirements": related_ids
                })

            flow_target.append({
                "name": name,
                "reason" if relationship_type == "include" else "condition": description,
                "related_requirements": related_ids
            })

            next_uc_number += 1

        for criterion in acceptance_criteria:
            description = criterion.get("description", str(criterion))
            description_lower = description.lower()
            related_ids = [criterion.get("id")] if criterion.get("id") else []

            if not self._contains_any(description_lower, ["invalid", "error", "fail", "prevent", "optional", "alternative", "recover", "forgot", "reset", "click", "directed"]):
                continue

            uc_id = f"UC-{next_uc_number:03d}"
            name = self._usecase_name_from_text(description, prefix="Handle")

            use_cases.append({
                "id": uc_id,
                "name": name,
                "description": description,
                "category": "extension",
                "related_requirements": related_ids
            })

            relationships.append({
                "from": uc_id,
                "to": main_uc_id,
                "type": "extend",
                "label": "acceptance/alternative flow",
                "related_requirements": related_ids
            })

            if self._contains_any(description_lower, ["invalid", "error", "fail", "prevent"]):
                exception_flows.append({
                    "name": name,
                    "condition": description,
                    "related_requirements": related_ids
                })
            else:
                alternative_flows.append({
                    "name": name,
                    "condition": description,
                    "related_requirements": related_ids
                })

            next_uc_number += 1

        notes = []

        note_parts = []

        if constraints:
            note_parts.append("Constraints: " + "; ".join(constraints))

        if nfrs:
            note_parts.append("NFRs: " + "; ".join(self._item_description(item) for item in nfrs))

        if risks:
            note_parts.append("Risks: " + "; ".join(self._item_description(item) for item in risks))

        if note_parts:
            notes.append({
                "id": "NOTE-001",
                "target": main_uc_id,
                "title": "Design Notes",
                "description": " | ".join(note_parts),
                "related_requirements": self._collect_requirement_ids(nfrs)
            })

        analysis_trace = self._build_usecase_traceability(use_cases, relationships, notes)

        usecase_analysis_json = {
            "feature_goal": srs.get("business_goal", f"Support the {feature_name} feature."),
            "primary_actors": [actor["name"] for actor in actors if actor["type"] == "primary"],
            "secondary_actors": [actor["name"] for actor in actors if actor["type"] != "primary"],
            "main_success_scenario": self._as_text_list(srs.get("scope", [])) or [f"Actor completes the {feature_name} feature successfully."],
            "mandatory_included_behaviours": mandatory_behaviours,
            "alternative_flows": alternative_flows,
            "exception_flows": exception_flows,
            "validation_flows": validation_flows,
            "security_flows": security_flows,
            "diagram_notes": notes,
            "traceability": analysis_trace
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
                "<<include>> is used for mandatory supporting behaviour.",
                "<<extend>> is used for optional, alternative, or exception behaviour.",
                "Constraints, NFRs, and risks are represented as notes where appropriate."
            ]
        }

        return usecase_analysis_json, usecase_json

    # ---------------------------------------------------------------------
    # Generic helper methods
    # ---------------------------------------------------------------------

    def _build_definitions_from_srs(self, srs: dict[str, Any]) -> list[dict[str, str]]:
        definitions = [
            {
                "term": "SDS",
                "definition": "Software Design Specification generated using an IEEE 1016-style design description structure."
            }
        ]

        target_stack = srs.get("target_stack")

        if target_stack:
            definitions.append({
                "term": "Target Stack",
                "definition": str(target_stack)
            })

        return definitions

    def _build_frontend_overview(self, ui_expectations: list[dict[str, Any]], input_requirements: list[dict[str, Any]]) -> str:
        if ui_expectations or input_requirements:
            return "Frontend design should provide the user-facing entry points, inputs, states, and feedback required by the approved SRS."

        return "Frontend design should support the approved feature interactions where applicable."

    def _build_backend_overview(self, functional_requirements: list[dict[str, Any]], validation_rules: list[dict[str, Any]]) -> str:
        if functional_requirements or validation_rules:
            return "Backend design should process feature requests, enforce business rules, validate inputs, and return structured responses."

        return "Backend design should support the approved feature responsibilities."

    def _build_data_overview(self, data_requirements: list[dict[str, Any]]) -> str:
        if data_requirements:
            return "Data design should support the data requirements defined in the approved SRS."

        return "No explicit data requirement was provided; data design should remain minimal and feature-scoped."

    def _build_integration_overview(self, api_expectations: list[dict[str, Any]], dependencies: list[str]) -> str:
        if api_expectations or dependencies:
            return "Integration design should follow the API expectations and dependencies listed in the approved SRS."

        return "No explicit external integration is required beyond the approved feature boundary."

    def _build_main_interactions(self, user_roles: list[str], functional_requirements: list[dict[str, Any]], feature_name: str) -> list[str]:
        interactions = []

        for role in user_roles or ["User"]:
            interactions.append(f"{role} interacts with the {feature_name} feature.")

        for requirement in functional_requirements:
            interactions.append(requirement.get("description", str(requirement)))

        return interactions

    def _build_logical_modules(self, layer: str, feature_name: str, primary_items: list[dict[str, Any]], secondary_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "name": f"{self._pascal_case(feature_name)}{layer.title()}Module",
                "responsibility": f"Handle {layer} responsibilities for the {feature_name} feature.",
                "derived_from": [self._item_description(item) for item in primary_items + secondary_items]
            }
        ]

    def _build_domain_services(self, feature_name: str, functional_requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "name": f"{self._pascal_case(feature_name)}Service",
                "responsibility": f"Apply business rules for the {feature_name} feature.",
                "related_requirements": self._collect_requirement_ids(functional_requirements)
            }
        ]

    def _build_data_modules(self, feature_name: str, data_requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "name": f"{self._pascal_case(feature_name)}DataModule",
                "responsibility": "Manage data access required by the feature.",
                "derived_from": [self._item_description(item) for item in data_requirements]
            }
        ]

    def _build_integration_points(self, api_expectations: list[dict[str, Any]], dependencies: list[str]) -> list[dict[str, Any]]:
        points = []

        for item in api_expectations:
            points.append({
                "type": "API",
                "description": self._item_description(item)
            })

        for dependency in dependencies:
            points.append({
                "type": "Dependency",
                "description": dependency
            })

        return points

    def _build_security_flow_records(self, risks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "name": self._usecase_name_from_text(self._item_description(risk), prefix="Mitigate"),
                "reason": self._item_description(risk),
                "related_requirements": []
            }
            for risk in risks
        ]

    def _build_usecase_traceability(self, use_cases: list[dict[str, Any]], relationships: list[dict[str, Any]], notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
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

    def _infer_fields_from_text(self, text: str) -> list[dict[str, Any]]:
        words = re.findall(r"[A-Za-z][A-Za-z0-9_ ]{1,30}", text)

        if not words:
            return []

        # Keep this generic: use noun-like phrases only as candidate fields.
        fields = []

        for word in words[:5]:
            cleaned = word.strip()
            if len(cleaned) < 3:
                continue

            fields.append({
                "name": self._camel_case(cleaned),
                "type": "String",
                "required": False
            })

        return fields

    def _infer_data_constraints_from_text(self, text: str) -> list[str]:
        constraints = []
        text_lower = text.lower()

        if "unique" in text_lower:
            constraints.append("Unique constraint required where applicable.")

        if "secure" in text_lower or "sensitive" in text_lower:
            constraints.append("Secure storage required where applicable.")

        if "hashed" in text_lower or "encrypted" in text_lower:
            constraints.append("Protected value storage required where applicable.")

        return constraints

    def _infer_state_changes(self, feature_name: str, functional_requirements: list[dict[str, Any]], acceptance_criteria: list[dict[str, Any]]) -> list[dict[str, Any]]:
        records = []

        for item in functional_requirements + acceptance_criteria:
            text = self._item_description(item)
            if self._contains_any(text.lower(), ["redirect", "return", "update", "create", "delete", "change", "status", "receive"]):
                records.append({
                    "description": text,
                    "related_requirements": [item.get("id")] if isinstance(item, dict) and item.get("id") else []
                })

        if not records:
            records.append({
                "description": f"Feature state changes should follow the approved {feature_name} acceptance criteria.",
                "related_requirements": []
            })

        return records

    def _quality_decision_from_nfr(self, description: str) -> str:
        text = description.lower()

        if self._contains_any(text, ["fast", "response", "performance", "load", "ms", "second"]):
            return "Optimize design to satisfy the stated performance expectation."

        if self._contains_any(text, ["responsive", "mobile", "desktop", "usability", "clear"]):
            return "Design frontend/user-facing behaviour to satisfy the stated usability expectation."

        if self._contains_any(text, ["secure", "privacy", "auth", "protect"]):
            return "Apply secure design controls aligned with the stated quality expectation."

        return "Design must satisfy this non-functional requirement."

    def _infer_related_requirement_ids_from_text(self, text: str, requirement_items: list[dict[str, Any]]) -> list[str]:
        related = []
        text_tokens = set(re.findall(r"[a-zA-Z0-9]+", text.lower()))

        for item in requirement_items:
            item_text = self._item_description(item)
            item_tokens = set(re.findall(r"[a-zA-Z0-9]+", item_text.lower()))

            if text_tokens and item_tokens and len(text_tokens.intersection(item_tokens)) >= 2:
                if item.get("id"):
                    related.append(item["id"])

        if not related:
            related = self._collect_requirement_ids(requirement_items)

        return related

    def _collect_requirement_ids(self, items: list[Any]) -> list[str]:
        ids = []

        for item in items:
            if isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]))

        return ids

    def _as_text_list(self, value: Any) -> list[str]:
        if value is None:
            return []

        if isinstance(value, list):
            return [self._item_description(item) for item in value]

        return [str(value)]

    def _as_record_list(self, value: Any) -> list[dict[str, Any]]:
        if value is None:
            return []

        if isinstance(value, list):
            records = []

            for item in value:
                if isinstance(item, dict):
                    records.append(dict(item))
                else:
                    records.append({"description": str(item)})

            return records

        if isinstance(value, dict):
            return [dict(value)]

        return [{"description": str(value)}]

    def _item_description(self, item: Any) -> str:
        if isinstance(item, dict):
            for key in ["description", "expectation", "payload", "risk", "mitigation", "data_point", "field", "endpoint", "name"]:
                if item.get(key):
                    return str(item[key])

            return str(item)

        return str(item)

    def _verb_phrase_from_feature(self, feature_name: str) -> str:
        text = feature_name.strip()

        if not text:
            return "Use Feature"

        # Generic feature names such as Login, Signup, Checkout, Enrollment already work as use cases.
        return text

    def _usecase_name_from_text(self, text: str, prefix: str | None = None) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9 ]+", " ", text).strip()
        words = cleaned.split()

        if prefix:
            words = [prefix] + words

        if not words:
            return prefix or "Handle Scenario"

        return " ".join(words[:5]).title()

    def _contains_any(self, text: str, keywords: list[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    def _guess_source_type(self, requirement_id: str) -> str:
        if requirement_id.startswith("FR"):
            return "FR"

        if requirement_id.startswith("AC"):
            return "AC"

        if requirement_id.startswith("VR"):
            return "VR"

        if requirement_id.startswith("NFR"):
            return "NFR"

        return "Requirement"

    def _pascal_case(self, text: str) -> str:
        parts = re.findall(r"[a-zA-Z0-9]+", text)
        return "".join(part[:1].upper() + part[1:] for part in parts) or "Feature"

    def _camel_case(self, text: str) -> str:
        pascal = self._pascal_case(text)
        return pascal[:1].lower() + pascal[1:] if pascal else "field"

    def _slug(self, text: str) -> str:
        slug = text.lower().strip()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        return slug.strip("-") or "feature"


architecture_agent = ArchitectureAgent()
