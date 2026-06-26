"""
Architecture Agent.

Purpose:
- Load approved SRS JSON from Requirement Agent.
- Optionally load approved Enhanced SRS JSON from Domain Agent.
- Generate SDS JSON and usecase_json using LLM.
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
from app.agents.architecture_agent.usecase_builder import ArchitectureUseCasePlantUMLBuilder
from app.agents.architecture_agent.usecase_renderer import UseCaseDiagramRenderer
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
    1. Input artifact loading.
    2. LLM architecture generation.
    3. SDS Markdown generation.
    4. PlantUML generation.
    5. PNG rendering.
    6. Artifact saving.
    """

    REQUIRED_TOP_LEVEL_KEYS = [
        "sds_json",
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
    ]

    def __init__(self):
        """
        Initialize Architecture Agent helpers.

        These helpers are specific to Architecture Agent.
        """

        self.markdown_builder = ArchitectureSDSMarkdownBuilder()
        self.usecase_builder = ArchitectureUseCasePlantUMLBuilder()
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
        """

        logger.info("Architecture Agent started for feature_id=%s", feature_id)

        feature = store.features.get(feature_id)

        if not feature:
            raise ValueError("Feature not found.")

        project = store.projects.get(feature["project_id"])

        if not project:
            raise ValueError("Project not found for this feature.")

        # Architecture Agent should only run after SRS approval.
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
        - Ask LLM for JSON only.
        - Parse and validate JSON.
        - If invalid, ask LLM to repair JSON.
        - If still invalid, build fallback SDS/usecase JSON.
        - Build Markdown and PlantUML locally.
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

        except Exception as first_error:
            logger.warning("Architecture JSON parse failed: %s", first_error)

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

                parsed = self._build_fallback_architecture_output(
                    agent_input=agent_input,
                    reason=str(second_error)
                )

                raw_output = json.dumps(parsed, indent=2)

        sds_json = parsed["sds_json"]
        usecase_json = parsed["usecase_json"]

        sds_markdown = self.markdown_builder.build(sds_json)
        usecase_puml = self.usecase_builder.build(usecase_json)

        return ArchitectureAgentOutput(
            sds_json=sds_json,
            sds_markdown=sds_markdown,
            usecase_json=usecase_json,
            usecase_puml=usecase_puml,
            raw_llm_output=raw_output
        )

    def _parse_and_validate_output(self, raw_output: str) -> dict:
        """
        Parse and validate Architecture Agent JSON output.
        """

        parsed = self._extract_json_object(raw_output)

        self._ensure_keys(parsed, self.REQUIRED_TOP_LEVEL_KEYS)

        sds_json = parsed.get("sds_json")
        usecase_json = parsed.get("usecase_json")

        if not isinstance(sds_json, dict):
            raise ValueError("sds_json must be a JSON object.")

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

    def _ensure_keys(self, data: dict, required_keys: list[str]) -> None:
        """
        Validate required keys.
        """

        missing = [key for key in required_keys if key not in data]

        if missing:
            raise ValueError(f"Missing required keys: {missing}")

    def _validate_usecase_json(self, usecase_json: dict) -> None:
        """
        Validate use case diagram structure.

        This does not guarantee perfect UML,
        but it prevents clearly invalid diagram data.
        """

        actors = usecase_json.get("actors", [])
        use_cases = usecase_json.get("use_cases", [])

        if not isinstance(actors, list) or not actors:
            raise ValueError("usecase_json.actors must be a non-empty list.")

        if not isinstance(use_cases, list) or not use_cases:
            raise ValueError("usecase_json.use_cases must be a non-empty list.")

        for actor in actors:
            if not actor.get("id") or not actor.get("name"):
                raise ValueError("Each actor must have id and name.")

        for use_case in use_cases:
            if not use_case.get("id") or not use_case.get("name"):
                raise ValueError("Each use case must have id and name.")

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

            if artifact.get("approval_status") not in [ApprovalStatus.APPROVED, ApprovalStatus.APPROVED.value]:
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
        Build fallback architecture output if LLM fails.

        This prevents Architecture Agent from completely failing.
        Human reviewer should carefully review fallback output.
        """

        srs = agent_input.srs_json
        feature = agent_input.feature
        project = agent_input.project

        user_roles = srs.get("user_roles", ["User"])
        functional_requirements = srs.get("functional_requirements", [])

        first_role = user_roles[0] if user_roles else "User"

        sds_json = {
            "project_id": project["project_id"],
            "project_name": project["project_name"],
            "project_type": project["project_type"],
            "feature_id": feature["feature_id"],
            "feature_name": feature["feature_name"],
            "target_stack": project.get("target_stack", "MERN"),
            "architecture_style": srs.get("architectural_style", "modular"),
            "feature_design_overview": (
                f"Fallback SDS for {feature['feature_name']} feature. "
                f"This design should be reviewed by a human architect."
            ),
            "frontend_responsibilities": [
                f"Provide user interface entry point for {feature['feature_name']} feature.",
                "Validate required user inputs before submitting to backend.",
                "Display success and error states clearly."
            ],
            "backend_responsibilities": [
                f"Process {feature['feature_name']} feature request.",
                "Validate request data.",
                "Return structured success or error responses."
            ],
            "database_design": {
                "collections": [
                    "Use existing relevant collections where possible."
                ],
                "data_notes": [
                    "Fallback database design generated due to LLM output issue."
                ]
            },
            "api_design_summary": [
                {
                    "endpoint": f"/api/{feature['feature_name'].lower()}",
                    "method": "POST",
                    "purpose": f"Handle {feature['feature_name']} feature operation.",
                    "related_requirements": [
                        req.get("id", "FR-001")
                        for req in functional_requirements[:3]
                        if isinstance(req, dict)
                    ]
                }
            ],
            "data_flow": [
                "User submits feature request from frontend.",
                "Frontend sends request to backend endpoint.",
                "Backend validates input and processes operation.",
                "Backend returns structured response.",
                "Frontend displays result to user."
            ],
            "error_handling_design": [
                "Return validation errors for invalid input.",
                "Return authentication errors where applicable.",
                "Return generic error response for unexpected failures."
            ],
            "authentication_authorization_design": [
                "Apply authentication and authorization rules if required by SRS."
            ],
            "folder_structure_suggestion": [
                "frontend/src/pages/",
                "frontend/src/components/",
                "backend/src/controllers/",
                "backend/src/routes/",
                "backend/src/services/"
            ],
            "dependency_list": [
                "React",
                "Express.js",
                "MongoDB",
                "Mongoose",
                "Axios"
            ],
            "integration_with_previous_features": [
                "Preserve previous approved features.",
                "Do not rewrite unrelated modules."
            ],
            "scalability_notes": [
                "Keep feature modules separated.",
                "Use service layer for business logic where needed."
            ],
            "assumptions": [
                f"Fallback architecture generated because: {reason}"
            ],
            "constraints": srs.get("constraints", []),
            "traceability": [
                {
                    "requirement_id": req.get("id", "FR-001"),
                    "sds_section": "Feature Design Overview",
                    "design_decision": "Requirement considered in fallback SDS."
                }
                for req in functional_requirements
                if isinstance(req, dict)
            ]
        }

        usecase_json = {
            "system_boundary": f"{feature['feature_name']} Feature",
            "diagram_title": f"{feature['feature_name']} Use Case Diagram",
            "actors": [
                {
                    "id": "ACT-001",
                    "name": first_role,
                    "type": "primary",
                    "description": f"Primary actor using {feature['feature_name']} feature."
                }
            ],
            "use_cases": [
                {
                    "id": "UC-001",
                    "name": f"Use {feature['feature_name']} feature",
                    "description": f"Actor performs {feature['feature_name']} feature operation.",
                    "related_requirements": [
                        req.get("id", "FR-001")
                        for req in functional_requirements
                        if isinstance(req, dict)
                    ]
                }
            ],
            "relationships": [
                {
                    "from": "ACT-001",
                    "to": "UC-001",
                    "type": "association",
                    "label": ""
                }
            ],
            "standards_notes": [
                "Actor is outside system boundary.",
                "Use case is inside system boundary.",
                "Association represents actor interaction with use case."
            ]
        }

        return {
            "sds_json": sds_json,
            "usecase_json": usecase_json
        }


architecture_agent = ArchitectureAgent()