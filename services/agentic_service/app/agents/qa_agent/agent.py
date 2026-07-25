"""
QA Agent orchestrator.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from fastapi.encoders import jsonable_encoder

from app.agents.qa_agent.evaluator import QAEvaluator
from app.agents.qa_agent.executor import TestExecutor
from app.agents.qa_agent.generator import TestGenerator
from app.agents.qa_agent.markdown_builder import QAMarkdownBuilder
from app.agents.qa_agent.schemas import (
    QAReport,
    TestingRunRequest,
)
from app.core.enums import (
    AgentName,
    ArtifactFormat,
    ArtifactType,
    FeatureStatus,
)
from app.schemas.agent_schema import AgentRunResponse
from app.services.artifact_service import artifact_service
from app.services.in_memory_store import store
from app.services.workspace_service import workspace_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QAAgent:
    """
    QA Agent.

    Pipeline

    1. Load feature/project
    2. Load project workspace
    3. Generate functional tests
    4. Execute generated tests
    5. Evaluate execution results
    6. Save generated tests
    7. Save Markdown & JSON reports
    8. Return AgentRunResponse
    """

    def __init__(self):
        self.generator = TestGenerator()
        self.executor = TestExecutor()
        self.evaluator = QAEvaluator()
        self.markdown_builder = QAMarkdownBuilder()

    async def run(
        self,
        feature_id: str,
        request: TestingRunRequest | None = None,
    ) -> AgentRunResponse:

        logger.info(
            "QA Agent started for feature_id=%s",
            feature_id,
        )

        request = request or TestingRunRequest()

        feature = store.features.get(feature_id)

        if not feature:
            raise ValueError("Feature not found.")

        project = store.projects.get(
            feature["project_id"]
        )

        if not project:
            raise ValueError(
                "Project not found for this feature."
            )

        feature["feature_status"] = FeatureStatus.IN_PROGRESS
        feature["current_agent"] = AgentName.QA

        try:

            repo = workspace_service.ensure_project_repo(
                project["project_id"]
            )

            workspace = Path(repo.working_tree_dir)

            if not workspace.exists():
                raise FileNotFoundError(
                    f"Workspace not found: {workspace}"
                )

            #
            # ----------------------------------------------------------
            # Generate Tests
            # ----------------------------------------------------------
            #

            logger.info("Generating QA test cases...")

            generation_start = time.perf_counter()

            (
                generated_files,
                generated_tests_dir,
            ) = await self.generator.generate_tests(
                workspace=workspace,
            )

            generation_time = (
                time.perf_counter()
                - generation_start
            )

            #
            # ----------------------------------------------------------
            # Execute Tests
            # ----------------------------------------------------------
            #

            execution_result = self.executor.execute(
                tests_directory=generated_tests_dir,
            )

            #
            # ----------------------------------------------------------
            # Evaluate Results
            # ----------------------------------------------------------
            #

            report = self.evaluator.evaluate(
                feature_id=feature_id,
                generated_files=generated_files,
                execution_result=execution_result,
                generation_time=generation_time,
            )

            #
            # ----------------------------------------------------------
            # Save Artifacts
            # ----------------------------------------------------------
            #

            artifact_ids: list[str] = []

            artifact_ids.extend(
                self._save_generated_tests(
                    project=project,
                    feature=feature,
                    generated_files=generated_files,
                    generated_tests_dir=generated_tests_dir,
                )
            )

            markdown = self.markdown_builder.build(
                project_name=project["project_name"],
                feature_name=feature["feature_name"],
                report=report,
            )

            artifact_ids.extend(
                self._save_reports(
                    project=project,
                    feature=feature,
                    report=report,
                    markdown=markdown,
                )
            )

            #
            # ----------------------------------------------------------
            # Finish Success
            # ----------------------------------------------------------
            #

            feature["feature_status"] = FeatureStatus.COMPLETED

            logger.info(
                "QA Agent completed successfully. "
                "Generated=%d Executed=%d Passed=%d Failed=%d",
                len(generated_files),
                execution_result.total_tests,
                execution_result.passed,
                execution_result.failed,
            )

            return AgentRunResponse(
                feature_id=feature_id,
                agent_name=AgentName.QA,
                status="completed",
                message="QA Agent completed successfully.",
                artifact_ids=artifact_ids,
            )

        except Exception as exc:

            logger.exception(
                "QA Agent failed for feature_id=%s",
                feature_id,
            )

            feature["feature_status"] = FeatureStatus.FAILED

            raise

        finally:
            # Always reset agent
            feature["current_agent"] = None

    # ------------------------------------------------------------------
    # Save Generated Test Files
    # ------------------------------------------------------------------

    def _save_generated_tests(
        self,
        project: dict,
        feature: dict,
        generated_files: list,
        generated_tests_dir: Path,  # kept for future use
    ) -> list[str]:

        artifact_ids: list[str] = []

        version = artifact_service.get_next_version(
            feature_id=feature["feature_id"],
            agent_name=AgentName.QA,
            artifact_type=ArtifactType.TEST_CASES,
        )

        for generated_file in generated_files:

            if (
                generated_file.status != "SUCCESS"
                or not generated_file.generated_code
            ):
                continue

            artifact = artifact_service.save_code_artifact(
                project=project,
                feature=feature,
                agent_name=AgentName.QA,
                artifact_type=ArtifactType.TEST_CASES,
                artifact_format=ArtifactFormat.CODE,
                filename=generated_file.test_file,
                code_content=generated_file.generated_code,
                version_override=version,
            )

            artifact_ids.append(
                artifact.artifact_id
            )

        return artifact_ids

    # ------------------------------------------------------------------
    # Save QA Reports
    # ------------------------------------------------------------------

    def _save_reports(
        self,
        project: dict,
        feature: dict,
        report: QAReport,
        markdown: str,
    ) -> list[str]:

        artifact_ids: list[str] = []

        version = artifact_service.get_next_version(
            feature_id=feature["feature_id"],
            agent_name=AgentName.QA,
            artifact_type=ArtifactType.QA_REPORT,
        )

        feature_slug = self._feature_slug(feature)

        payload = jsonable_encoder(report)

        logger.info(
            "QA JSON generated_at type: %s",
            type(payload.get("generated_at")).__name__,
        )

        json_artifact = artifact_service.save_json_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.QA,
            artifact_type=ArtifactType.QA_REPORT,
            filename=f"{feature_slug}_qa_report_v{version}.json",
            data=payload,
            version_override=version,
        )

        artifact_ids.append(
            json_artifact.artifact_id
        )

        markdown_artifact = artifact_service.save_text_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.QA,
            artifact_type=ArtifactType.QA_REPORT,
            artifact_format=ArtifactFormat.MARKDOWN,
            filename=f"{feature_slug}_qa_report_v{version}.md",
            content=markdown,
            version_override=version,
        )

        artifact_ids.append(
            markdown_artifact.artifact_id
        )

        return artifact_ids

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _feature_slug(
        self,
        feature: dict,
    ) -> str:
        """
        Build a slug for the current feature.
        """

        return self._slug(
            feature.get(
                "feature_name",
                "feature",
            )
        )

    def _slug(
        self,
        value: str,
    ) -> str:
        """
        Convert text into a filesystem-safe slug.
        """

        slug = value.lower().strip()
        slug = re.sub(
            r"[^a-z0-9]+",
            "_",
            slug,
        )

        return slug.strip("_") or "item"


qa_agent = QAAgent()