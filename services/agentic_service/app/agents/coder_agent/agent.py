"""
Coder Agent.

Pipeline:
1. Load context: approved SRS, optional approved Enhanced SRS, approved
   Architecture Plan, optional approved UI/UX integration manifest, and the
   project's manifest.
2. Plan (planner.py), with up to MAX_PLANNING_ATTEMPTS: if plan_validator
   rejects a plan, re-prompt with the specific coverage gap before spending
   any workspace/agentic-loop cost.
3. Prepare workspace: start a fresh feature branch.
4. Code + verify, with up to MAX_CODING_ATTEMPTS: run the agentic coding loop
   (coding_loop.py), commit whatever it wrote, then run the deterministic
   sandboxed build/lint/test gate (verify.py). A failing attempt's failure
   text is fed back into the next coding attempt. If every attempt fails
   verification, proceed anyway with verification_passed=False rather than
   silently retrying forever -- the human still has to explicitly approve,
   and the report makes the failure impossible to miss.
5. Build diff/manifest/setup-instructions deterministically from the real
   git diff (diff_builder.py) -- never from the coding loop's self-report.
6. Save all artifacts for human review.
7. Merge-on-approval / discard-on-rejection happens via
   merge_approved_feature()/discard_rejected_feature(), invoked from
   approval_service.py's approval hook (mirrors UIUXAgent's
   apply_design_system_patch pattern).

See services/agentic_service/instructions .md section 5 for the full plan.
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.coder_agent.coding_loop import build_coder_react_agent, build_task_message
from app.agents.coder_agent.diff_builder import (
    build_code_manifest,
    build_file_tree,
    build_merge_report_markdown,
    build_requirement_code_map,
    build_setup_instructions_markdown,
)
from app.agents.coder_agent.plan_validator import CodePlanValidationError, code_plan_validator
from app.agents.coder_agent.planner import code_planner
from app.agents.coder_agent.schemas import CoderAgentInput, CoderAgentOutput
from app.agents.coder_agent.verify import coder_verifier
from app.core.enums import AgentName, ApprovalStatus, ArtifactFormat, ArtifactType
from app.schemas.coder_schema import CoderAgentRunRequest
from app.services.artifact_service import artifact_service
from app.services.in_memory_store import store
from app.services.project_memory_service import project_memory_service
from app.services.workspace_service import workspace_service
from app.utils.file_manager import read_json_file
from app.utils.logger import get_logger

logger = get_logger(__name__)

MAX_PLANNING_ATTEMPTS = 2
MAX_CODING_ATTEMPTS = 3
CODING_LOOP_RECURSION_LIMIT = 50


class CoderAgent:
    """
    Main Coder Agent class.
    """

    def __init__(self):
        self.planner = code_planner
        self.plan_validator = code_plan_validator
        self.verifier = coder_verifier

    async def run(self, feature_id: str, request: CoderAgentRunRequest) -> CoderAgentOutput:
        """
        Run the full Coder Agent pipeline (plan -> code -> verify -> diff).

        Rule:
            Coder Agent can only run after Requirement Agent SRS JSON and
            Architecture Agent's Architecture Plan JSON are approved. The
            UI/UX integration manifest is optional context (some features
            are backend-only).
        """

        logger.info("Coder Agent started for feature_id=%s", feature_id)

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
            artifact_format=ArtifactFormat.JSON,
        )
        if not srs_artifact:
            raise ValueError(
                "No approved SRS JSON artifact found. "
                "Approve Requirement Agent SRS JSON before running Coder Agent."
            )
        srs_json = read_json_file(srs_artifact["file_path"])

        enhanced_srs_json = None
        if request.use_enhanced_srs_if_available:
            enhanced_srs_artifact = self._find_latest_approved_artifact(
                feature_id=feature_id,
                agent_name=AgentName.DOMAIN,
                artifact_type=ArtifactType.ENHANCED_SRS,
                artifact_format=ArtifactFormat.JSON,
            )
            if enhanced_srs_artifact:
                enhanced_srs_json = read_json_file(enhanced_srs_artifact["file_path"])

        architecture_plan_json = self._load_approved_architecture_plan(feature_id)
        if architecture_plan_json is None:
            raise ValueError(
                "No approved Architecture Plan (or legacy SDS) JSON artifact found. "
                "Approve Architecture Agent output before running Coder Agent."
            )

        ui_integration_manifest_json = self._load_approved_ui_integration_manifest(feature_id)
        project_manifest_json = project_memory_service.load_project_manifest(project["project_id"])

        agent_input = CoderAgentInput(
            project=dict(project),
            feature=dict(feature),
            srs_json=srs_json,
            enhanced_srs_json=enhanced_srs_json,
            architecture_plan_json=architecture_plan_json,
            ui_integration_manifest_json=ui_integration_manifest_json,
            project_manifest_json=project_manifest_json,
            human_comment=request.human_comment,
        )

        srs_for_planning = enhanced_srs_json or srs_json
        code_plan_json = await self._plan_with_retries(agent_input, srs_for_planning)

        workspace_service.start_feature_branch(project["project_id"], feature_id)

        verify_result, coding_attempts = await self._code_with_retries(
            project["project_id"], feature_id, code_plan_json
        )

        diff = workspace_service.diff_against_main(project["project_id"], feature_id)

        output = CoderAgentOutput(
            code_plan_json=code_plan_json,
            verification_passed=verify_result["passed"],
            file_tree_json=build_file_tree(diff),
            code_manifest_json=build_code_manifest(code_plan_json, diff),
            requirement_code_map_json=build_requirement_code_map(code_plan_json, diff),
            setup_instructions_markdown=build_setup_instructions_markdown(code_plan_json),
            merge_report_markdown=build_merge_report_markdown(
                feature["feature_name"], diff, verify_result, coding_attempts
            ),
        )

        output.artifact_ids = self._save_artifacts(dict(project), dict(feature), output)

        logger.info(
            "Coder Agent completed for feature_id=%s verification_passed=%s attempts=%d artifacts=%s",
            feature_id,
            verify_result["passed"],
            coding_attempts,
            output.artifact_ids,
        )

        return output

    async def _plan_with_retries(
        self, agent_input: CoderAgentInput, srs_for_planning: dict[str, Any]
    ) -> dict[str, Any]:
        previous_plan_json = None
        validation_feedback = None
        last_error: CodePlanValidationError | None = None

        for attempt in range(1, MAX_PLANNING_ATTEMPTS + 1):
            code_plan_json, _raw = await self.planner.generate(
                project=agent_input.project,
                feature=agent_input.feature,
                srs_json=srs_for_planning,
                architecture_plan_json=agent_input.architecture_plan_json,
                ui_integration_manifest_json=agent_input.ui_integration_manifest_json,
                project_manifest_json=agent_input.project_manifest_json,
                human_comment=agent_input.human_comment,
                previous_plan_json=previous_plan_json,
                validation_feedback=validation_feedback,
            )

            try:
                self.plan_validator.validate(
                    srs_for_planning, agent_input.architecture_plan_json, code_plan_json
                )
                return code_plan_json
            except CodePlanValidationError as error:
                logger.warning(
                    "Plan attempt %d/%d failed validation: %s", attempt, MAX_PLANNING_ATTEMPTS, error
                )
                last_error = error
                previous_plan_json = code_plan_json
                validation_feedback = str(error)

        raise last_error

    async def _code_with_retries(
        self, project_id: str, feature_id: str, code_plan_json: dict[str, Any]
    ) -> tuple[dict[str, Any], int]:
        prior_failure_output = None
        verify_result: dict[str, Any] = {"passed": False, "steps": []}

        for attempt in range(1, MAX_CODING_ATTEMPTS + 1):
            react_agent = build_coder_react_agent(project_id, feature_id)
            task_message = build_task_message(code_plan_json, prior_failure_output)

            await react_agent.ainvoke(
                {"messages": [{"role": "user", "content": task_message}]},
                config={"recursion_limit": CODING_LOOP_RECURSION_LIMIT},
            )

            workspace_service.commit_changes(
                project_id, feature_id, message=f"Coder Agent attempt {attempt}: {feature_id}"
            )

            verify_result = self.verifier.verify(project_id, code_plan_json)

            if verify_result["passed"]:
                return verify_result, attempt

            logger.warning(
                "Coding attempt %d/%d failed verification for feature_id=%s",
                attempt,
                MAX_CODING_ATTEMPTS,
                feature_id,
            )
            prior_failure_output = self._summarize_verify_failure(verify_result)

        return verify_result, MAX_CODING_ATTEMPTS

    def _summarize_verify_failure(self, verify_result: dict[str, Any]) -> str:
        failed_steps = [step for step in verify_result["steps"] if step["status"] == "failed"]
        return "\n\n".join(f"[{step['name']}]\n{step['output']}" for step in failed_steps)

    def _save_artifacts(self, project: dict, feature: dict, output: CoderAgentOutput) -> list[str]:
        version = artifact_service.get_next_version(
            feature_id=feature["feature_id"],
            agent_name=AgentName.CODER,
            artifact_type=ArtifactType.CODE_PLAN,
        )

        feature_slug = self._feature_slug(feature)
        artifact_ids = []

        plan_artifact = artifact_service.save_json_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.CODER,
            artifact_type=ArtifactType.CODE_PLAN,
            filename=f"{feature_slug}_code_plan_v{{version}}.json",
            data=output.code_plan_json,
            version_override=version,
        )
        artifact_ids.append(plan_artifact.artifact_id)

        file_tree_artifact = artifact_service.save_json_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.CODER,
            artifact_type=ArtifactType.CODE_DIFF,
            filename=f"{feature_slug}_file_tree_v{{version}}.json",
            data=output.file_tree_json,
            version_override=version,
        )
        artifact_ids.append(file_tree_artifact.artifact_id)

        merge_report_artifact = artifact_service.save_text_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.CODER,
            artifact_type=ArtifactType.CODE_DIFF,
            artifact_format=ArtifactFormat.MARKDOWN,
            filename=f"{feature_slug}_merge_report_v{{version}}.md",
            content=output.merge_report_markdown,
            version_override=version,
        )
        artifact_ids.append(merge_report_artifact.artifact_id)

        manifest_artifact = artifact_service.save_json_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.CODER,
            artifact_type=ArtifactType.CODE_MANIFEST,
            filename=f"{feature_slug}_code_manifest_v{{version}}.json",
            data=output.code_manifest_json,
            version_override=version,
        )
        artifact_ids.append(manifest_artifact.artifact_id)

        req_map_artifact = artifact_service.save_json_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.CODER,
            artifact_type=ArtifactType.REQUIREMENT_CODE_MAP,
            filename=f"{feature_slug}_requirement_code_map_v{{version}}.json",
            data=output.requirement_code_map_json,
            version_override=version,
        )
        artifact_ids.append(req_map_artifact.artifact_id)

        setup_artifact = artifact_service.save_text_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.CODER,
            artifact_type=ArtifactType.SETUP_INSTRUCTIONS,
            artifact_format=ArtifactFormat.MARKDOWN,
            filename=f"{feature_slug}_setup_instructions_v{{version}}.md",
            content=output.setup_instructions_markdown,
            version_override=version,
        )
        artifact_ids.append(setup_artifact.artifact_id)

        return artifact_ids

    def merge_approved_feature(self, feature_id: str, version: int) -> None:
        """
        Merge an approved feature branch into main and update the project
        manifest so the next feature's plan_node sees what now exists.

        Called from approval_service.py only after the CODE_DIFF artifact for
        this exact version has been approved -- never before.
        """
        feature = store.features.get(feature_id)
        if not feature:
            raise ValueError("Feature not found.")

        project_id = feature["project_id"]

        patch = self._build_project_manifest_patch(feature_id, feature, version)

        workspace_service.merge_feature_branch(project_id, feature_id)
        project_memory_service.update_project_manifest(project_id, patch)

        logger.info(
            "Merged feature_id=%s version=%s into main; project manifest updated.",
            feature_id,
            version,
        )

    def discard_rejected_feature(self, feature_id: str) -> None:
        """
        Discard a rejected feature branch's changes.
        """
        feature = store.features.get(feature_id)
        if not feature:
            raise ValueError("Feature not found.")

        workspace_service.discard_feature_branch(feature["project_id"], feature_id)
        logger.info("Discarded rejected feature branch for feature_id=%s", feature_id)

    def _build_project_manifest_patch(
        self, feature_id: str, feature: dict, version: int
    ) -> dict[str, Any]:
        patch: dict[str, Any] = {
            "routes": [],
            "api_endpoints": [],
            "models": [],
            "shared_components": [],
            "features": {},
        }

        plan_artifact = self._find_artifact_by_version(
            feature_id, AgentName.CODER, ArtifactType.CODE_PLAN, ArtifactFormat.JSON, version
        )
        file_tree_artifact = self._find_artifact_by_version(
            feature_id, AgentName.CODER, ArtifactType.CODE_DIFF, ArtifactFormat.JSON, version
        )

        if not plan_artifact or not file_tree_artifact:
            return patch

        code_plan_json = read_json_file(plan_artifact["file_path"])
        file_tree_json = read_json_file(file_tree_artifact["file_path"])
        touched = set(file_tree_json.get("added", [])) | set(file_tree_json.get("modified", []))

        for file_entry in code_plan_json.get("files", []):
            path = file_entry.get("path")
            if path not in touched:
                continue

            if "/routes/" in path:
                patch["routes"].append(path)
            elif "/models/" in path:
                patch["models"].append(path)
            elif "/components/" in path:
                patch["shared_components"].append(path)

            for mapped in file_entry.get("maps_to", []):
                if isinstance(mapped, str) and mapped.startswith("/"):
                    patch["api_endpoints"].append(mapped)

        patch["features"][feature_id] = {
            "feature_name": feature.get("feature_name"),
            "files": sorted(touched),
        }

        return patch

    def _find_artifact_by_version(
        self,
        feature_id: str,
        agent_name: AgentName,
        artifact_type: ArtifactType,
        artifact_format: ArtifactFormat,
        version: int,
    ) -> dict | None:
        for artifact in store.artifacts.values():
            if artifact.get("feature_id") != feature_id:
                continue
            if artifact.get("agent_name") not in [agent_name, agent_name.value]:
                continue
            if artifact.get("artifact_type") not in [artifact_type, artifact_type.value]:
                continue
            if artifact.get("artifact_format") not in [artifact_format, artifact_format.value]:
                continue
            if artifact.get("version") != version:
                continue

            return artifact

        return None

    def _load_approved_architecture_plan(self, feature_id: str) -> dict | None:
        """
        Tries the current ArtifactType.ARCHITECTURE_PLAN first, then falls
        back to the legacy ArtifactType.SDS (see UIUXAgent for the same
        pattern and rationale).
        """
        artifact = self._find_latest_approved_artifact(
            feature_id=feature_id,
            agent_name=AgentName.ARCHITECTURE,
            artifact_type=ArtifactType.ARCHITECTURE_PLAN,
            artifact_format=ArtifactFormat.JSON,
        )

        if not artifact:
            artifact = self._find_latest_approved_artifact(
                feature_id=feature_id,
                agent_name=AgentName.ARCHITECTURE,
                artifact_type=ArtifactType.SDS,
                artifact_format=ArtifactFormat.JSON,
            )

        if not artifact:
            return None

        return read_json_file(artifact["file_path"])

    def _load_approved_ui_integration_manifest(self, feature_id: str) -> dict | None:
        artifact = self._find_latest_approved_artifact(
            feature_id=feature_id,
            agent_name=AgentName.UIUX,
            artifact_type=ArtifactType.UI_INTEGRATION_MANIFEST,
            artifact_format=ArtifactFormat.JSON,
        )

        if not artifact:
            return None

        return read_json_file(artifact["file_path"])

    def _find_latest_approved_artifact(
        self,
        feature_id: str,
        agent_name: AgentName,
        artifact_type: ArtifactType,
        artifact_format: ArtifactFormat,
    ) -> dict | None:
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
                ApprovalStatus.APPROVED.value,
            ]:
                continue

            matching_artifacts.append(artifact)

        if not matching_artifacts:
            return None

        return max(matching_artifacts, key=lambda item: item.get("version", 1))

    def _feature_slug(self, feature: dict) -> str:
        return self._slug(feature.get("feature_name", "feature"))

    def _slug(self, value: str) -> str:
        slug = value.lower().strip()
        slug = re.sub(r"[^a-z0-9]+", "_", slug)
        return slug.strip("_") or "item"


coder_agent = CoderAgent()
