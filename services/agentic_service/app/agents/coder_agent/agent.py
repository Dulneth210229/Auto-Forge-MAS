"""
Coder Agent orchestrator.

Purpose:
    Coordinate the full Coder Agent workflow for one feature iteration.

Architecture fit:
    - Called by the API route (agents.py) after building CoderAgentInput.
    - Orchestrates all internal Coder Agent modules in the correct order.
    - Returns CoderAgentOutput to the API route, which saves it as artifacts.
    - Does NOT know about FastAPI, artifact saving, or HTTP concerns.

Workflow (step by step):
    1.  [LOAD]     Load approved artifact content via ContextBuilder.
    2.  [LOAD]     Load previous project snapshot via ContextBuilder.
    3.  [VALIDATE] Validate required environment variables via EnvVarValidator.
    4.  [CONTEXT]  Select relevant existing files for the LLM prompt.
    5.  [PROMPT]   Build user prompt via build_coder_user_prompt().
    6.  [LLM]      Call provider.generate() via LLMProviderService.
    7.  [PARSE]    Parse LLM response via parse_coder_agent_response().
    8.  [MERGE]    Merge new/updated files with previous snapshot via ProjectMerger.
    9.  [OUTPUT]   Assemble and return CoderAgentOutput.

Error handling:
    - MissingEnvVarsError  → re-raised as ValueError (caller returns HTTP 400).
    - LLM timeout/network  → re-raised with descriptive message.
    - JSON parse failure   → re-raised with raw response excerpt.
    - Missing artifacts    → re-raised as ValueError (caller returns HTTP 400).

Author: Coder Agent (Auto-Forge MAS)
Version: 1.0.0
"""

from datetime import datetime, timezone

from app.agents.coder_agent.context_builder import context_builder
from app.agents.coder_agent.env_validator import env_validator, MissingEnvVarsError
from app.agents.coder_agent.parser import parse_coder_agent_response
from app.agents.coder_agent.project_merger import project_merger
from app.agents.coder_agent.prompt import (
    CODER_AGENT_SYSTEM_PROMPT,
    build_coder_user_prompt,
)
from app.agents.coder_agent.schemas import CoderAgentInput, CoderAgentOutput
from app.services.llm_provider_service import llm_provider_service
from app.utils.logger import get_logger
from app.utils.json_utils import extract_json_object

logger = get_logger("coder_agent.agent")


class CoderAgent:
    """
    Coder Agent — generates production-ready source code for one approved feature.

    This class is stateless. Each call to run() is a complete, independent workflow.
    All state is carried in CoderAgentInput and CoderAgentOutput.

    Usage:
        agent = CoderAgent()
        output = await agent.run(agent_input)
    """

    async def run(self, agent_input: CoderAgentInput) -> CoderAgentOutput:
        """
        Execute the full Coder Agent workflow.

        Args:
            agent_input: Fully populated CoderAgentInput from the API route.

        Returns:
            CoderAgentOutput with all generated/updated/unchanged files and metadata.

        Raises:
            ValueError:          On missing artifacts, missing env vars, or parse failure.
            RuntimeError:        On unexpected LLM or workflow errors.
        """
        run_start = datetime.now(timezone.utc)
        logger.info(
            "=== [CoderAgent] RUN STARTED === feature='%s' project='%s' stack='%s'",
            agent_input.feature_name,
            agent_input.project_name,
            agent_input.target_stack,
        )

        try:
            # ------------------------------------------------------------------
            # Step 1: Load approved artifact content (if not pre-loaded)
            # ------------------------------------------------------------------
            # The API route may have pre-loaded artifact content into agent_input.
            # If any approved content fields are empty, load them now.
            # ------------------------------------------------------------------
            logger.info("[CoderAgent] Step 1: Verifying approved artifact content.")

            agent_input = await self._ensure_artifact_content(agent_input)

            logger.info(
                "[CoderAgent] Step 1 complete. SRS: %d chars, Enhanced SRS: %d chars, SDS: %d chars.",
                len(agent_input.approved_srs_markdown),
                len(agent_input.approved_enhanced_srs_markdown),
                len(agent_input.approved_sds_markdown),
            )

            # ------------------------------------------------------------------
            # Step 2: Load previous project snapshot
            # ------------------------------------------------------------------
            logger.info("[CoderAgent] Step 2: Loading previous project snapshot.")

            if not agent_input.previous_project_snapshot:
                (
                    previous_snapshot,
                    previous_feature_names,
                ) = context_builder.load_previous_project_snapshot(
                    project_id=agent_input.project_id
                )

                # Rebuild the input with the loaded snapshot
                agent_input = CoderAgentInput(
                    **{
                        **agent_input.model_dump(),
                        "previous_project_snapshot": previous_snapshot,
                        "previous_feature_names": (
                            agent_input.previous_feature_names or previous_feature_names
                        ),
                    }
                )
            else:
                previous_snapshot = agent_input.previous_project_snapshot

            logger.info(
                "[CoderAgent] Step 2 complete. Previous snapshot: %d files, "
                "known features: %s",
                len(previous_snapshot),
                agent_input.previous_feature_names,
            )

            # ------------------------------------------------------------------
            # Step 3: Validate environment variables
            # ------------------------------------------------------------------
            logger.info("[CoderAgent] Step 3: Validating environment variables.")

            sds_json = self._try_parse_sds_json(agent_input.approved_sds_markdown)
            required_vars = env_validator.validate_from_sds(
                sds_json=sds_json,
                provided_vars=agent_input.env_vars_provided,
            )

            logger.info(
                "[CoderAgent] Step 3 complete. %d required env vars validated.",
                len(required_vars),
            )

            # ------------------------------------------------------------------
            # Step 4: Select relevant existing files for the prompt
            # ------------------------------------------------------------------
            logger.info("[CoderAgent] Step 4: Selecting relevant existing files for prompt.")

            relevant_files = context_builder.select_relevant_files(
                feature_name=agent_input.feature_name,
                all_files=previous_snapshot,
            )

            # Rebuild agent_input with only the relevant subset in the snapshot
            # so the prompt builder sends minimal context to the LLM
            agent_input_for_prompt = CoderAgentInput(
                **{
                    **agent_input.model_dump(),
                    "previous_project_snapshot": relevant_files,
                }
            )

            logger.info(
                "[CoderAgent] Step 4 complete. %d / %d files selected as relevant.",
                len(relevant_files),
                len(previous_snapshot),
            )

            # ------------------------------------------------------------------
            # Step 5: Build user prompt
            # ------------------------------------------------------------------
            logger.info("[CoderAgent] Step 5: Building LLM prompt.")

            user_prompt = build_coder_user_prompt(agent_input_for_prompt)

            logger.info(
                "[CoderAgent] Step 5 complete. Prompt length: %d chars.", len(user_prompt)
            )

            # ------------------------------------------------------------------
            # Step 6: Call LLM
            # ------------------------------------------------------------------
            logger.info(
                "[CoderAgent] Step 6: Calling LLM provider for feature='%s'.",
                agent_input.feature_name,
            )

            provider = llm_provider_service.get_provider()
            logger.info(
                "[CoderAgent] Using provider='%s' model='%s'.",
                type(provider).__name__,
                provider.model,
            )

            try:
                raw_response = await provider.generate(
                    prompt=user_prompt,
                    system_prompt=CODER_AGENT_SYSTEM_PROMPT,
                )
            except Exception as exc:
                raise RuntimeError(
                    f"Coder Agent: LLM provider call failed for feature "
                    f"'{agent_input.feature_name}'. Detail: {exc}"
                ) from exc

            logger.info(
                "[CoderAgent] Step 6 complete. LLM response: %d chars.", len(raw_response)
            )

            # ------------------------------------------------------------------
            # Step 7: Parse LLM response
            # ------------------------------------------------------------------
            logger.info("[CoderAgent] Step 7: Parsing LLM response.")

            # Determine version for this run
            version = self._compute_version(agent_input)

            parsed_output = parse_coder_agent_response(
                raw_response=raw_response,
                feature_id=agent_input.feature_id,
                feature_name=agent_input.feature_name,
                project_id=agent_input.project_id,
                project_name=agent_input.project_name,
                target_stack=agent_input.target_stack,
                version=version,
            )

            logger.info(
                "[CoderAgent] Step 7 complete. Parsed: %d new, %d updated, %d unchanged files.",
                len(parsed_output.generated_files),
                len(parsed_output.updated_files),
                len(parsed_output.unchanged_files),
            )

            # ------------------------------------------------------------------
            # Step 8: Merge with previous snapshot
            # ------------------------------------------------------------------
            logger.info("[CoderAgent] Step 8: Merging files with previous project snapshot.")

            merge_result = project_merger.merge(
                previous_snapshot=previous_snapshot,
                llm_generated=parsed_output.generated_files,
                llm_updated=parsed_output.updated_files,
                feature_id=agent_input.feature_id,
                feature_name=agent_input.feature_name,
                project_id=agent_input.project_id,
                project_name=agent_input.project_name,
                target_stack=agent_input.target_stack,
                version=version,
            )

            logger.info(
                "[CoderAgent] Step 8 complete. Final: %d new, %d updated, %d unchanged.",
                len(merge_result.generated_files),
                len(merge_result.updated_files),
                len(merge_result.unchanged_files),
            )

            # ------------------------------------------------------------------
            # Step 9: Assemble final CoderAgentOutput
            # ------------------------------------------------------------------
            logger.info("[CoderAgent] Step 9: Assembling final output.")

            final_output = CoderAgentOutput(
                file_tree=merge_result.file_tree,
                generated_files=merge_result.generated_files,
                updated_files=merge_result.updated_files,
                unchanged_files=merge_result.unchanged_files,
                env_vars_required=parsed_output.env_vars_required,
                run_commands=parsed_output.run_commands,
                integration_notes=parsed_output.integration_notes,
                requirement_mapping=parsed_output.requirement_mapping,
                artifact_metadata=parsed_output.artifact_metadata,
                setup_instructions_markdown=parsed_output.setup_instructions_markdown,
                merge_report_markdown=merge_result.merge_report_markdown,
            )

            run_elapsed = (datetime.now(timezone.utc) - run_start).total_seconds()
            logger.info(
                "=== [CoderAgent] RUN COMPLETE === feature='%s' elapsed=%.2fs "
                "new=%d updated=%d unchanged=%d",
                agent_input.feature_name,
                run_elapsed,
                len(final_output.generated_files),
                len(final_output.updated_files),
                len(final_output.unchanged_files),
            )

            return final_output

        except MissingEnvVarsError as exc:
            logger.error("[CoderAgent] ENV VAR GATE: %s", exc)
            raise ValueError(str(exc)) from exc

        except ValueError:
            # Re-raise ValueErrors as-is (they carry descriptive messages)
            raise

        except RuntimeError:
            raise

        except Exception as exc:
            logger.exception("[CoderAgent] Unexpected error: %s", exc)
            raise RuntimeError(
                f"Coder Agent encountered an unexpected error "
                f"for feature '{agent_input.feature_name}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Private helper methods
    # ------------------------------------------------------------------

    async def _ensure_artifact_content(
        self, agent_input: CoderAgentInput
    ) -> CoderAgentInput:
        """
        Ensure all required artifact content fields are populated.

        The API route pre-loads artifact content into CoderAgentInput.
        This method is a safety net: if any required field is empty
        (e.g., for testing or direct agent invocation), it loads the
        content from the artifact service.

        Only SRS, Enhanced SRS, and SDS are required.
        UI Design is optional (UI/UX Agent may not have run yet).
        """
        # If all required fields are already populated, nothing to do
        if (
            agent_input.approved_srs_markdown
            and agent_input.approved_enhanced_srs_markdown
            and agent_input.approved_sds_markdown
        ):
            return agent_input

        # Load missing content from artifact service
        updates: dict = {}

        if not agent_input.approved_srs_markdown:
            logger.info("[CoderAgent] SRS content missing — loading from artifact service.")
            updates["approved_srs_markdown"] = context_builder.load_approved_srs_content(
                agent_input.feature_id
            )

        if not agent_input.approved_enhanced_srs_markdown:
            logger.info(
                "[CoderAgent] Enhanced SRS content missing — loading from artifact service."
            )
            updates["approved_enhanced_srs_markdown"] = (
                context_builder.load_approved_enhanced_srs_content(agent_input.feature_id)
            )

        if not agent_input.approved_sds_markdown:
            logger.info("[CoderAgent] SDS content missing — loading from artifact service.")
            updates["approved_sds_markdown"] = context_builder.load_approved_sds_content(
                agent_input.feature_id
            )

        if updates:
            return CoderAgentInput(**{**agent_input.model_dump(), **updates})

        return agent_input

    def _try_parse_sds_json(self, sds_markdown: str) -> dict:
        """
        Attempt to extract a JSON block from the SDS Markdown content.

        The Architecture Agent saves both SDS Markdown and SDS JSON artifacts.
        The JSON artifact contains structured env var declarations.
        If the SDS content passed here is Markdown (not JSON), we return
        an empty dict and let the env validator fall back to keyword detection.
        """
        try:
            return extract_json_object(sds_markdown)
        except ValueError:
            logger.info(
                "[CoderAgent] SDS content is Markdown (not JSON). "
                "EnvVarValidator will use keyword detection only."
            )
            return {}

    def _compute_version(self, agent_input: CoderAgentInput) -> int:
        """
        Compute the artifact version number for this run.

        Version starts at 1 for the first feature iteration.
        For revision runs, increment from the previous snapshot's max version.
        """
        if not agent_input.previous_project_snapshot:
            return 1

        max_version = max(
            (f.version for f in agent_input.previous_project_snapshot),
            default=0,
        )
        return max_version + 1