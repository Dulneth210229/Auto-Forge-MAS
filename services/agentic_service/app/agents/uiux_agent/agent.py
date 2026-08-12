"""
UI/UX Agent.

Pipeline:
1. Load context: approved SRS, optional approved Enhanced SRS, approved
   Architecture Plan, and the project's design system.
2. Generate ui_metadata_json (one-shot LLM call via metadata_modeler.py).
3. Validate SRS coverage (metadata_validator.py) -- fail loudly on gaps.
4. Generate each component's JSX + mock props (component_generator.py),
   scoped per-component so a single broken component can be retried alone.
5. Render one PNG screenshot per page (preview_renderer.py, Playwright).
6. Save all artifacts: ui_metadata_json, one .jsx per component, one PNG per
   page, ui_design_markdown, and the integration manifest for the Coder Agent.
7. Update design_system.json with any new tokens/components -- gated on human
   approval (see apply_design_system_patch, invoked from approval_service.py)
   so a rejected run never pollutes the shared design system.
8. Human approval gate happens outside this class (existing approval flow).

See services/agentic_service/instructions .md section 4 for the full plan.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.agents.uiux_agent.component_generator import UIUXComponentGenerator
from app.agents.uiux_agent.design_system_service import uiux_design_system_service
from app.agents.uiux_agent.integration_manifest_builder import uiux_integration_manifest_builder
from app.agents.uiux_agent.markdown_builder import uiux_markdown_builder
from app.agents.uiux_agent.metadata_modeler import UIUXMetadataModeler
from app.agents.uiux_agent.metadata_validator import UIMetadataValidationError, UIMetadataValidator
from app.agents.uiux_agent.preview_renderer import PreviewRenderError, uiux_preview_renderer
from app.agents.uiux_agent.schemas import UIUXAgentInput, UIUXAgentOutput
from app.core.enums import AgentName, ApprovalStatus, ArtifactFormat, ArtifactType
from app.schemas.uiux_schema import UIUXAgentRunRequest
from app.services.artifact_service import artifact_service
from app.services.in_memory_store import store
from app.services.project_memory_service import project_memory_service
from app.utils.file_manager import read_json_file
from app.utils.logger import get_logger

logger = get_logger(__name__)


class UIUXAgent:
    """
    Main UI/UX Agent class.
    """

    # Slightly more headroom than Requirement/Domain/Architecture Agent's usual "one repair
    # attempt" -- UI/UX Agent has no deterministic fallback rung by design (see module
    # docstring: a guessed-at UI plan is worse than none), so it gets more real LLM attempts
    # before failing loudly instead of a synthetic fallback to fall back to. Real testing
    # against llama3:latest showed the missing-requirement-ID error genuinely shrinking each
    # repair round (6 missing -> 4 -> 1), i.e. real convergence, not flailing -- worth a bit
    # more headroom than 2 attempts to let it actually finish converging.
    MAX_VALIDATION_REPAIR_ATTEMPTS = 4

    # Same reasoning as above, applied to preview-render failures (see _render_pages): real
    # testing showed a repair can trade one render error for a different one (a fix for a
    # ReferenceError introduced a JSX syntax error instead), so it can take more than one
    # round to actually converge on working code.
    MAX_RENDER_REPAIR_ATTEMPTS = 3

    def __init__(self):
        self.metadata_modeler = UIUXMetadataModeler()
        self.metadata_validator = UIMetadataValidator()
        self.component_generator = UIUXComponentGenerator()

    async def run(self, feature_id: str, request: UIUXAgentRunRequest) -> UIUXAgentOutput:
        """
        Run the full UI/UX Agent pipeline (steps 1-6; step 7 is triggered
        separately by approval_service.py once the resulting artifact is
        approved).

        Rule:
            UI/UX Agent can only run after Requirement Agent SRS JSON and
            Architecture Agent's Architecture Plan JSON are approved.
        """

        logger.info("UI/UX Agent started for feature_id=%s", feature_id)

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
                "Approve Requirement Agent SRS JSON before running UI/UX Agent."
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
                "Approve Architecture Agent output before running UI/UX Agent."
            )

        design_system_json = uiux_design_system_service.load(project["project_id"])

        agent_input = UIUXAgentInput(
            project=dict(project),
            feature=dict(feature),
            srs_json=srs_json,
            enhanced_srs_json=enhanced_srs_json,
            architecture_plan_json=architecture_plan_json,
            design_system_json=design_system_json,
            ui_preferences=request.ui_preferences,
            human_comment=request.human_comment,
        )

        ui_metadata_json, raw_llm_output = await self._generate_and_validate_metadata(agent_input)

        component_files, page_render_data = await self._generate_components(
            agent_input, ui_metadata_json
        )

        page_screenshots = await self._render_pages(component_files, page_render_data)

        integration_manifest_json = uiux_integration_manifest_builder.build(ui_metadata_json)
        ui_design_markdown = uiux_markdown_builder.build(
            feature_name=feature["feature_name"],
            ui_metadata_json=ui_metadata_json,
            integration_manifest_json=integration_manifest_json,
        )

        output = UIUXAgentOutput(
            ui_metadata_json=ui_metadata_json,
            component_files=component_files,
            page_screenshots=page_screenshots,
            integration_manifest_json=integration_manifest_json,
            ui_design_markdown=ui_design_markdown,
            raw_llm_output=raw_llm_output,
        )

        output.artifact_ids = self._save_artifacts(project=dict(project), feature=dict(feature), output=output)

        logger.info(
            "UI/UX Agent completed for feature_id=%s artifacts=%s",
            feature_id,
            output.artifact_ids,
        )

        return output

    async def _generate_and_validate_metadata(
        self, agent_input: UIUXAgentInput
    ) -> tuple[dict[str, Any], str]:
        ui_metadata_json, raw_llm_output = await self.metadata_modeler.generate(
            project=agent_input.project,
            feature=agent_input.feature,
            srs_json=agent_input.srs_json,
            enhanced_srs_json=agent_input.enhanced_srs_json,
            architecture_plan_json=agent_input.architecture_plan_json,
            design_system_json=agent_input.design_system_json,
            ui_preferences=agent_input.ui_preferences,
            human_comment=agent_input.human_comment,
        )

        srs_for_validation = agent_input.enhanced_srs_json or agent_input.srs_json

        last_error: UIMetadataValidationError | None = None

        for attempt in range(1, self.MAX_VALIDATION_REPAIR_ATTEMPTS + 2):  # +1 initial, +1 inclusive range
            try:
                self.metadata_validator.validate(srs_for_validation, ui_metadata_json)
                return ui_metadata_json, raw_llm_output

            except UIMetadataValidationError as error:
                last_error = error

                if attempt > self.MAX_VALIDATION_REPAIR_ATTEMPTS:
                    break

                logger.warning(
                    "UI metadata validation failed (repair attempt %s/%s): %s",
                    attempt, self.MAX_VALIDATION_REPAIR_ATTEMPTS, error
                )

                ui_metadata_json, raw_llm_output = await self.metadata_modeler.repair_for_validation(
                    raw_llm_output, str(error)
                )

        # No fallback here by design (see module docstring) -- once repair attempts are
        # exhausted, fail loudly rather than proceed with a guessed-at UI plan.
        raise last_error

    async def _generate_components(
        self, agent_input: UIUXAgentInput, ui_metadata_json: dict[str, Any]
    ) -> tuple[dict[str, str], dict[str, list[dict[str, Any]]]]:
        """
        Generate every component's JSX + mock props, one LLM call per
        component. Returns:
            component_files: component name -> jsx source text
            page_render_data: page_id -> [{"name", "jsx_code", "mock_props"}]
        """

        data_entities = (
            agent_input.architecture_plan_json.get("design_views", {})
            .get("data_view", {})
            .get("data_entities", [])
        )

        component_files: dict[str, str] = {}
        page_render_data: dict[str, list[dict[str, Any]]] = {}

        for page in ui_metadata_json.get("pages", []):
            rendered_components = []

            for component_metadata in page.get("components", []) or []:
                component_name = component_metadata["name"]

                if component_metadata.get("reused_from_design_system"):
                    reused_jsx = self._load_existing_approved_component(
                        agent_input.project["project_id"], component_name
                    )

                    if reused_jsx is not None:
                        component_files[component_name] = reused_jsx
                        rendered_components.append(
                            {
                                "name": component_name,
                                "jsx_code": reused_jsx,
                                "mock_props": self._placeholder_mock_props(component_metadata),
                                "reused": True,
                            }
                        )
                        continue

                    logger.warning(
                        "Component '%s' was flagged reused_from_design_system=True but no "
                        "approved component with that name exists yet in this project -- "
                        "generating it instead.",
                        component_name,
                    )

                generated, _raw = await self.component_generator.generate(
                    project=agent_input.project,
                    feature=agent_input.feature,
                    page_metadata=page,
                    component_metadata=component_metadata,
                    data_entities=data_entities,
                    design_system_json=agent_input.design_system_json,
                    ui_preferences=agent_input.ui_preferences,
                    human_comment=agent_input.human_comment,
                )

                component_files[component_name] = generated["jsx_code"]
                rendered_components.append(
                    {
                        "name": component_name,
                        "jsx_code": generated["jsx_code"],
                        "mock_props": generated["mock_props"],
                        "reused": False,
                    }
                )

            page_render_data[page["page_id"]] = rendered_components

        return component_files, page_render_data

    async def _render_pages(
        self, component_files: dict[str, str], page_render_data: dict[str, list[dict[str, Any]]]
    ) -> dict[str, bytes]:
        """
        Render one PNG per page. Playwright's sync API is used inside
        preview_renderer.py, so it is called via asyncio.to_thread here --
        it cannot run inside this already-running event loop.

        On a real browser render failure (e.g. a ReferenceError from JSX that parsed fine but
        is not actually self-contained), attempts up to MAX_RENDER_REPAIR_ATTEMPTS targeted
        repairs: regenerate every freshly-generated (non-reused) component on that page with
        the concrete browser error fed back, then retry the render. Bounded, not unlimited --
        real testing showed a repair can itself introduce a *different* error (e.g. fixing a
        ReferenceError by rewriting the component introduced a JSX syntax error), so one repair
        attempt is not always enough. component_files is mutated in place so whichever attempt's
        JSX is what actually gets saved as the artifact.

        If every attempt still fails, the page's screenshot is skipped (logged as an error) --
        not fatal for the whole run. Unlike ui_metadata_json (which the Architecture/Coder Agent
        pipeline actually depends on), a PNG preview is a human-review convenience only; nothing
        downstream reads it. Real testing surfaced a render failure ("element is not visible")
        that reproduces only inside the live graph-invoked pipeline and not in direct,
        content-identical isolation tests (same JSX, same asyncio.to_thread call pattern,
        increasing the timeout from 30s to 90s made no difference) -- a deeper Playwright/
        threading interaction under the graph's execution context that a code-level component
        fix cannot address. Blocking the entire UI/UX Agent run (and therefore the whole
        pipeline) on a screenshot is the wrong tradeoff.
        """

        page_screenshots: dict[str, bytes] = {}

        for page_id, components in page_render_data.items():
            last_error: PreviewRenderError | None = None

            for attempt in range(self.MAX_RENDER_REPAIR_ATTEMPTS + 1):
                try:
                    if attempt > 0:
                        components = await self._repair_page_components(components, str(last_error))

                        for component in components:
                            component_files[component["name"]] = component["jsx_code"]

                        page_render_data[page_id] = components

                    page_screenshots[page_id] = await asyncio.to_thread(
                        uiux_preview_renderer.render_page_png, components
                    )
                    last_error = None
                    break

                except PreviewRenderError as error:
                    last_error = error

                    if attempt == 0:
                        logger.warning(
                            "Preview render failed for page_id=%s (initial attempt): %s",
                            page_id, error
                        )
                    else:
                        logger.warning(
                            "Preview render failed for page_id=%s (repair attempt %s/%s): %s",
                            page_id, attempt, self.MAX_RENDER_REPAIR_ATTEMPTS, error
                        )

            if last_error is not None:
                logger.error(
                    "Preview render permanently failed for page_id=%s after %s attempts -- "
                    "skipping its screenshot, continuing without it: %s",
                    page_id, self.MAX_RENDER_REPAIR_ATTEMPTS + 1, last_error
                )

        return page_screenshots

    async def _repair_page_components(
        self, components: list[dict[str, Any]], render_error: str
    ) -> list[dict[str, Any]]:
        """
        Regenerate every freshly-generated component on a page whose preview render failed,
        feeding back the real browser error. Reused (already human-approved) components are
        left untouched -- regenerating proven-good code on the assumption it might be the
        culprit would be a regression risk, not a fix.
        """

        repaired = []

        for component in components:
            if component.get("reused"):
                repaired.append(component)
                continue

            fixed, _raw = await self.component_generator.repair_for_render_error(
                jsx_code=component["jsx_code"],
                mock_props=component["mock_props"],
                render_error=render_error,
            )

            repaired.append({
                "name": component["name"],
                "jsx_code": fixed["jsx_code"],
                "mock_props": fixed["mock_props"],
                "reused": False,
            })

        return repaired

    def _load_existing_approved_component(self, project_id: str, component_name: str) -> str | None:
        """
        Look up an already-approved component .jsx file from ANY feature in
        this project (not just the current one) by name, and return its
        exact content verbatim.

        This is what makes "reused_from_design_system: true" an actual reuse
        mechanism instead of just a label the model writes down while a
        fresh (and possibly drifted) copy gets generated anyway -- the
        precise bug this method fixes, found during M8's real second-feature
        test (Signup correctly flagged LoginForm as reused, but nothing
        previously stopped a brand-new LoginForm.jsx from being generated).
        """
        slug = self._slug(component_name)

        matching = []

        for artifact in store.artifacts.values():
            if artifact.get("project_id") != project_id:
                continue
            if artifact.get("agent_name") not in [AgentName.UIUX, AgentName.UIUX.value]:
                continue
            if artifact.get("artifact_type") not in [
                ArtifactType.UI_COMPONENT_CODE,
                ArtifactType.UI_COMPONENT_CODE.value,
            ]:
                continue
            if artifact.get("artifact_format") not in [ArtifactFormat.CODE, ArtifactFormat.CODE.value]:
                continue
            if artifact.get("approval_status") not in [
                ApprovalStatus.APPROVED,
                ApprovalStatus.APPROVED.value,
            ]:
                continue
            if slug not in str(artifact.get("file_path", "")).lower():
                continue

            matching.append(artifact)

        if not matching:
            return None

        latest = max(matching, key=lambda item: item.get("version", 1))
        return Path(latest["file_path"]).read_text(encoding="utf-8")

    def _placeholder_mock_props(self, component_metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Build simple mock props for previewing a reused component. There is
        no component_generator call for a reused component (no LLM involved,
        by design), so there is no generated mock_props either -- use the
        prop descriptions already present in ui_metadata_json as readable
        placeholder values instead.
        """
        return {
            name: str(description)
            for name, description in (component_metadata.get("props") or {}).items()
        }

    def _save_artifacts(self, project: dict, feature: dict, output: UIUXAgentOutput) -> list[str]:
        """
        Save all UI/UX Agent artifacts for this run, all sharing one version
        number (mirrors architecture_agent's markdown+json+diagrams pattern).
        """

        version = artifact_service.get_next_version(
            feature_id=feature["feature_id"],
            agent_name=AgentName.UIUX,
            artifact_type=ArtifactType.UI_METADATA,
        )

        feature_slug = self._feature_slug(feature)
        artifact_ids: list[str] = []

        metadata_artifact = artifact_service.save_json_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.UIUX,
            artifact_type=ArtifactType.UI_METADATA,
            filename=f"{feature_slug}_ui_metadata_v{{version}}.json",
            data=output.ui_metadata_json,
            version_override=version,
        )
        artifact_ids.append(metadata_artifact.artifact_id)

        manifest_artifact = artifact_service.save_json_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.UIUX,
            artifact_type=ArtifactType.UI_INTEGRATION_MANIFEST,
            filename=f"{feature_slug}_integration_manifest_v{{version}}.json",
            data=output.integration_manifest_json,
            version_override=version,
        )
        artifact_ids.append(manifest_artifact.artifact_id)

        markdown_artifact = artifact_service.save_text_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.UIUX,
            artifact_type=ArtifactType.UI_METADATA,
            artifact_format=ArtifactFormat.MARKDOWN,
            filename=f"{feature_slug}_ui_design_v{{version}}.md",
            content=output.ui_design_markdown,
            version_override=version,
        )
        artifact_ids.append(markdown_artifact.artifact_id)

        for component_name, jsx_code in output.component_files.items():
            component_slug = self._slug(component_name)
            component_artifact = artifact_service.save_text_artifact(
                project=project,
                feature=feature,
                agent_name=AgentName.UIUX,
                artifact_type=ArtifactType.UI_COMPONENT_CODE,
                artifact_format=ArtifactFormat.CODE,
                filename=f"{feature_slug}_{component_slug}_v{{version}}.jsx",
                content=jsx_code,
                version_override=version,
            )
            artifact_ids.append(component_artifact.artifact_id)

        for page_id, png_bytes in output.page_screenshots.items():
            page_slug = self._slug(page_id)
            screenshot_artifact = artifact_service.save_binary_artifact(
                project=project,
                feature=feature,
                agent_name=AgentName.UIUX,
                artifact_type=ArtifactType.UI_PREVIEW_SCREENSHOT,
                artifact_format=ArtifactFormat.PNG,
                filename=f"{feature_slug}_{page_slug}_v{version}.png",
                binary_content=png_bytes,
            )
            artifact_ids.append(screenshot_artifact.artifact_id)

        return artifact_ids

    def apply_design_system_patch(self, feature_id: str, version: int) -> None:
        """
        Merge new components/tokens from an approved UI/UX run into the
        project's shared design_system.json.

        Called from approval_service.py only after the UI_METADATA artifact
        for this exact version has been approved -- never before, so a
        rejected run cannot pollute the shared design system.
        """

        feature = store.features.get(feature_id)
        if not feature:
            raise ValueError("Feature not found.")

        project = store.projects.get(feature["project_id"])
        if not project:
            raise ValueError("Project not found for this feature.")

        metadata_artifact = self._find_artifact_by_version(
            feature_id=feature_id,
            agent_name=AgentName.UIUX,
            artifact_type=ArtifactType.UI_METADATA,
            artifact_format=ArtifactFormat.JSON,
            version=version,
        )

        if not metadata_artifact:
            logger.warning(
                "apply_design_system_patch: no ui_metadata artifact found for "
                "feature_id=%s version=%s -- skipping.",
                feature_id,
                version,
            )
            return

        ui_metadata_json = read_json_file(metadata_artifact["file_path"])
        design_system_json = project_memory_service.load_design_system(project["project_id"])

        design_system_json.setdefault("components", {})
        design_system_json.setdefault("tokens", {})

        new_component_count = 0
        new_token_count = 0

        for page in ui_metadata_json.get("pages", []):
            for component in page.get("components", []) or []:
                if component.get("reused_from_design_system"):
                    continue

                name = component.get("name")
                if not name or name in design_system_json["components"]:
                    continue

                design_system_json["components"][name] = {
                    "props": list((component.get("props") or {}).keys()),
                    "introduced_by_feature": feature["feature_name"],
                }
                new_component_count += 1

            for token in page.get("new_design_tokens", []) or []:
                token_name = token.get("token")
                if not token_name or token_name in design_system_json["tokens"]:
                    continue

                design_system_json["tokens"][token_name] = {
                    "value": token.get("value"),
                    "introduced_by_feature": feature["feature_name"],
                }
                new_token_count += 1

        if new_component_count or new_token_count:
            project_memory_service.save_design_system(project["project_id"], design_system_json)

        logger.info(
            "apply_design_system_patch: feature_id=%s version=%s merged %d new components, "
            "%d new tokens.",
            feature_id,
            version,
            new_component_count,
            new_token_count,
        )

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
        Load the approved Architecture Agent design output.

        Tries the current ArtifactType.ARCHITECTURE_PLAN first, then falls
        back to the legacy ArtifactType.SDS -- some approved artifacts predate
        the SDS -> Architecture Plan rename and were never regenerated under
        the new type. Both shapes carry a "design_views" section, which is
        all this agent actually reads.
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

    def _find_latest_approved_artifact(
        self,
        feature_id: str,
        agent_name: AgentName,
        artifact_type: ArtifactType,
        artifact_format: ArtifactFormat,
    ) -> dict | None:
        """
        Find latest approved artifact matching the given filters.
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


uiux_agent = UIUXAgent()
