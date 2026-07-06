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

from langgraph.errors import GraphRecursionError

from app.agents.coder_agent.coding_loop import build_coder_react_agent, build_task_message
from app.agents.coder_agent.diff_builder import (
    build_code_manifest,
    build_file_tree,
    build_merge_report_markdown,
    build_requirement_code_map,
    build_setup_instructions_markdown,
)
from app.agents.coder_agent.plan_validator import CodePlanValidationError, code_plan_validator
from app.agents.coder_agent.planner import CodePlanGenerationError, code_planner
from app.agents.coder_agent.schemas import CoderAgentInput, CoderAgentOutput
from app.agents.coder_agent.verify import coder_verifier
from app.core.enums import AgentName, ApprovalStatus, ArtifactFormat, ArtifactType
from app.schemas.coder_schema import CoderAgentReviseRequest, CoderAgentRunRequest
from app.services.artifact_service import artifact_service
from app.services.in_memory_store import store
from app.services.project_memory_service import project_memory_service
from app.services.workspace_service import workspace_service
from app.utils.file_manager import read_json_file
from app.utils.logger import get_logger

logger = get_logger(__name__)

MAX_PLANNING_ATTEMPTS = 2
MAX_CODING_ATTEMPTS = 3
# Bumped 50 -> 65 -> 100. 65 (raised specifically to accommodate the new
# list_unimplemented_planned_files/check_syntax self-check tool calls) still hit
# GraphRecursionError on a real 8-file plan (2 of which were "modify an existing
# component" patches) before the model reached a stop condition -- confirmed via a
# real run against the TaskFlow/Task Comments feature. GraphRecursionError is now
# also caught in _code_with_retries (treated as a failed attempt, not a crash), so
# this limit no longer needs to be exactly right -- just generous enough that a
# realistically-sized plan can usually finish in one attempt.
CODING_LOOP_RECURSION_LIMIT = 100


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

    async def revise(self, feature_id: str, request: CoderAgentReviseRequest) -> CoderAgentOutput:
        """
        Revise the latest Coder Agent output for a feature that already has
        a real prior run -- mirrors RequirementAgent.revise()/
        ArchitectureAgent.revise()'s established pattern (load latest
        output, apply a human revision comment, save as a new version,
        never overwriting), adapted for the fact that this agent's output
        is a live git branch, not just a JSON document.

        Key difference from run(): builds on the EXISTING feature branch
        (workspace_service.resume_feature_branch, never resets it) instead
        of starting fresh from main -- a revision is a targeted change on
        top of already-verified work, not a new attempt at the same plan.
        This is what lets a human iterate by prompt (this session's
        explicit ask) instead of only getting one automatic shot.

        Rule:
            Requires a prior Coder Agent run for this feature (a CODE_PLAN
            artifact and a feature branch must already exist) -- there is
            nothing to revise otherwise.
        """
        logger.info("Coder Agent revision started for feature_id=%s", feature_id)

        feature = store.features.get(feature_id)
        if not feature:
            raise ValueError("Feature not found.")

        project = store.projects.get(feature["project_id"])
        if not project:
            raise ValueError("Project not found for this feature.")

        latest_plan_artifact = self._find_latest_code_plan_artifact(feature_id)
        if not latest_plan_artifact:
            raise ValueError(
                "No existing Coder Agent output found for this feature. "
                "Run the Coder Agent before requesting a revision."
            )
        existing_plan_json = read_json_file(latest_plan_artifact["file_path"])

        srs_artifact = self._find_latest_approved_artifact(
            feature_id=feature_id,
            agent_name=AgentName.REQUIREMENT,
            artifact_type=ArtifactType.SRS,
            artifact_format=ArtifactFormat.JSON,
        )
        if not srs_artifact:
            raise ValueError(
                "No approved SRS JSON artifact found. "
                "Approve Requirement Agent SRS JSON before revising the Coder Agent."
            )
        srs_json = read_json_file(srs_artifact["file_path"])

        architecture_plan_json = self._load_approved_architecture_plan(feature_id)
        if architecture_plan_json is None:
            raise ValueError(
                "No approved Architecture Plan (or legacy SDS) JSON artifact found."
            )

        ui_integration_manifest_json = self._load_approved_ui_integration_manifest(feature_id)
        project_manifest_json = project_memory_service.load_project_manifest(project["project_id"])

        agent_input = CoderAgentInput(
            project=dict(project),
            feature=dict(feature),
            srs_json=srs_json,
            enhanced_srs_json=None,
            architecture_plan_json=architecture_plan_json,
            ui_integration_manifest_json=ui_integration_manifest_json,
            project_manifest_json=project_manifest_json,
            human_comment=request.revision_comment,
        )

        # Frames the existing plan honestly, as a revision request rather than a
        # validation rejection -- reusing _plan_with_retries' rejection-retry
        # mechanism (see that method's docstring) would otherwise tell the model
        # its already-good, already-coded plan was "REJECTED by a deterministic
        # coverage check," which is simply false and would confuse the model
        # about what actually needs to change.
        revision_feedback = (
            "This is a HUMAN-REQUESTED REVISION of an already-implemented and verified "
            "feature, not a validation rejection. The plan below already passed validation "
            "and was successfully coded once. Apply ONLY the specific change described in "
            "the human revision comment above -- keep every existing file entry that "
            "doesn't need to change; add or modify entries only for what this revision "
            "requires."
        )

        coverage_baseline_files = self._collect_cumulative_plan_files(feature_id)

        # Must happen BEFORE planning, not after: the agentic revision planner's
        # tools (list_dir/read_file/search_code) read whatever is currently
        # checked out in the workspace, so the feature branch's real, current
        # file content must already be checked out when planning starts.
        workspace_service.resume_feature_branch(project["project_id"], feature_id)

        code_plan_json = await self._plan_with_retries(
            agent_input,
            srs_json,
            previous_plan_json=existing_plan_json,
            validation_feedback=revision_feedback,
            coverage_baseline_files=coverage_baseline_files,
            exploration_context=(project["project_id"], feature_id),
        )

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
            "Coder Agent revision completed for feature_id=%s verification_passed=%s "
            "attempts=%d artifacts=%s",
            feature_id,
            verify_result["passed"],
            coding_attempts,
            output.artifact_ids,
        )

        return output

    def _find_latest_code_plan_artifact(self, feature_id: str) -> dict | None:
        """
        Find the latest CODE_PLAN JSON artifact for this feature, regardless
        of approval status -- a revision should be possible even before the
        prior version has been approved/merged (a human may want several
        rounds of feedback before approving anything).
        """
        matching = self._find_all_code_plan_artifacts(feature_id)

        if not matching:
            return None

        return max(matching, key=lambda item: item.get("version", 1))

    def _find_all_code_plan_artifacts(self, feature_id: str) -> list[dict]:
        return [
            artifact
            for artifact in store.artifacts.values()
            if artifact.get("feature_id") == feature_id
            and artifact.get("agent_name") in [AgentName.CODER, AgentName.CODER.value]
            and artifact.get("artifact_type") in [ArtifactType.CODE_PLAN, ArtifactType.CODE_PLAN.value]
            and artifact.get("artifact_format") in [ArtifactFormat.JSON, ArtifactFormat.JSON.value]
        ]

    def _collect_cumulative_plan_files(self, feature_id: str) -> list[dict[str, Any]]:
        """
        Union of every file entry across EVERY CODE_PLAN version ever saved
        for this feature -- not just the latest one.

        Each revise() call's own saved code_plan_json only lists the delta
        it actually touched (see _plan_with_retries' coverage_baseline_files
        docstring for why), so the *latest* version alone is not a complete
        picture of everything this feature has ever implemented. Confirmed
        necessary by a real, second revision request: the first revision's
        corrected artifact set was saved with only its own delta plan
        (just the one file it touched) as the "latest" CODE_PLAN, so a
        second revision's coverage baseline -- built from only that latest
        version -- silently lost every file the *original* plan had
        implemented, reproducing the exact "does not cover these API
        endpoints" rejection this whole mechanism exists to prevent. Later
        versions win when the same path appears in more than one version
        (its most recent maps_to/action is the accurate one).
        """
        matching = sorted(
            self._find_all_code_plan_artifacts(feature_id), key=lambda item: item.get("version", 1)
        )

        files_by_path: dict[str, dict[str, Any]] = {}
        for artifact in matching:
            plan = read_json_file(artifact["file_path"])
            if not isinstance(plan, dict):
                continue
            for file_entry in plan.get("files", []) or []:
                path = file_entry.get("path") if isinstance(file_entry, dict) else None
                if path:
                    files_by_path[path] = file_entry

        return list(files_by_path.values())

    async def _plan_with_retries(
        self,
        agent_input: CoderAgentInput,
        srs_for_planning: dict[str, Any],
        previous_plan_json: dict[str, Any] | None = None,
        validation_feedback: str | None = None,
        coverage_baseline_files: list[dict[str, Any]] | None = None,
        exploration_context: tuple[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        previous_plan_json/validation_feedback can be pre-seeded by a caller
        (revise() does this, framing the existing plan + a human revision
        request rather than a validation rejection) -- if plan_validator
        then rejects THAT plan, the retry loop below takes over normally
        from there, with the standard "was rejected" framing, since at that
        point it genuinely would be a rejection.

        coverage_baseline_files: for revise() only -- the file list of the
        already-implemented, already-verified prior plan. A revision's own
        code_plan_json only needs to describe the delta (what this specific
        change touches), not re-declare every endpoint/entity/requirement the
        prior plan already covered -- confirmed necessary against a real
        revise() run, where the model (reasonably) returned only the files
        relevant to the requested change and plan_validator then rejected it
        for "missing" endpoints that were, in fact, already implemented and
        untouched by this revision. Coverage is validated against the union
        of the baseline's files and this attempt's own files; the plan
        actually returned (and coded) is still just this attempt's delta.

        exploration_context: (project_id, feature_id), for revise() only --
        when set, each attempt calls planner.generate_via_exploration(...)
        (an agentic, tool-using planner that can look at the real codebase)
        instead of planner.generate() (a single-shot call with zero
        visibility into it). Confirmed necessary: the single-shot planner
        could only correctly scope a revision when the human named the exact
        file(s) to change -- a vague, file-unspecified request (e.g. "styles
        are missing, add tailwind css") needs the model to actually look at
        the codebase to know which files are affected. Everything else about
        the retry loop (coverage validation, feedback framing) is unchanged.
        """
        last_error: CodePlanValidationError | CodePlanGenerationError | None = None

        for attempt in range(1, MAX_PLANNING_ATTEMPTS + 1):
            if exploration_context:
                project_id, feature_id = exploration_context
                try:
                    code_plan_json, _raw = await self.planner.generate_via_exploration(
                        project_id=project_id,
                        feature_id=feature_id,
                        project=agent_input.project,
                        feature=agent_input.feature,
                        srs_json=srs_for_planning,
                        architecture_plan_json=agent_input.architecture_plan_json,
                        ui_integration_manifest_json=agent_input.ui_integration_manifest_json,
                        project_manifest_json=agent_input.project_manifest_json,
                        human_comment=agent_input.human_comment,
                        previous_plan_json=previous_plan_json,
                        validation_feedback=validation_feedback,
                        coverage_baseline_files=coverage_baseline_files or [],
                    )
                except CodePlanGenerationError as error:
                    # The exploration loop ran out of its turn budget before
                    # calling submit_code_plan -- confirmed a real, reachable
                    # failure mode on a genuinely vague, multi-file revision
                    # request. Treat exactly like a rejected attempt (same
                    # retry mechanism below), not an uncaught crash -- mirrors
                    # _code_with_retries' GraphRecursionError handling.
                    logger.warning(
                        "Exploration-planning attempt %d/%d did not finish in time: %s",
                        attempt,
                        MAX_PLANNING_ATTEMPTS,
                        error,
                    )
                    last_error = error
                    # NOTE: this fresh attempt has zero memory of what the previous one
                    # actually explored (a new agent conversation, not a continuation) --
                    # so the feedback can only be a general strategy change, not "don't
                    # redo X" (it has no idea what X was). Point it at the tools that
                    # answer a question directly instead of requiring per-file reads.
                    validation_feedback = (
                        "Your previous attempt ran out of exploration turns before calling "
                        "submit_code_plan. This is a fresh attempt with no memory of what you "
                        "explored last time, so change strategy rather than trying to pick up "
                        "where you left off: prefer a summarizing tool (check_component_styling, "
                        "read_project_manifest, search_code) over reading each candidate file's "
                        "full content one at a time -- your job here is only to decide WHICH "
                        "files need a plan entry, not to draft the actual code change (a later "
                        "coding step does that and will read each file itself). Call "
                        "submit_code_plan as soon as you can name the affected file(s), without "
                        "verifying every one by reading its source."
                    )
                    continue
            else:
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

            plan_for_coverage_check = code_plan_json
            if coverage_baseline_files:
                plan_for_coverage_check = {
                    **code_plan_json,
                    "files": list(code_plan_json.get("files", []) or []) + coverage_baseline_files,
                }

            try:
                self.plan_validator.validate(
                    srs_for_planning,
                    agent_input.architecture_plan_json,
                    plan_for_coverage_check,
                    enforce_endpoint_coverage=exploration_context is None,
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
        already_touched: dict[str, list[str]] | None = None
        verify_result: dict[str, Any] = {"passed": False, "steps": []}

        for attempt in range(1, MAX_CODING_ATTEMPTS + 1):
            react_agent = build_coder_react_agent(project_id, feature_id, code_plan_json)
            task_message = build_task_message(code_plan_json, prior_failure_output, already_touched)
            hit_recursion_limit = False

            try:
                await react_agent.ainvoke(
                    {"messages": [{"role": "user", "content": task_message}]},
                    config={"recursion_limit": CODING_LOOP_RECURSION_LIMIT},
                )
            except GraphRecursionError:
                # A larger plan (several files, some "modify" patches, plus the
                # self-check tool calls the prompt now encourages) can burn through
                # the turn budget before the model calls a final, tool-free answer.
                # Treat this exactly like an incomplete attempt rather than letting
                # it crash the whole run uncaught: commit whatever was finished,
                # then let the existing gap-detection logic below report precisely
                # what's still missing for the next attempt.
                hit_recursion_limit = True
                logger.warning(
                    "Coding attempt %d/%d for feature_id=%s hit the recursion limit "
                    "(%d) before finishing -- committing partial progress and "
                    "retrying with a note to work efficiently.",
                    attempt,
                    MAX_CODING_ATTEMPTS,
                    feature_id,
                    CODING_LOOP_RECURSION_LIMIT,
                )

            workspace_service.commit_changes(
                project_id, feature_id, message=f"Coder Agent attempt {attempt}: {feature_id}"
            )

            already_touched = workspace_service.get_touched_files(project_id, feature_id)
            gaps = self._find_plan_gaps(code_plan_json, already_touched)

            if gaps or hit_recursion_limit:
                logger.warning(
                    "Coding attempt %d/%d for feature_id=%s left %d planned file(s) untouched",
                    attempt,
                    MAX_CODING_ATTEMPTS,
                    feature_id,
                    len(gaps),
                )
                prior_failure_output = self._format_plan_gaps(gaps)
                if hit_recursion_limit:
                    prior_failure_output = (
                        "The previous attempt ran out of turns before finishing -- work "
                        "efficiently this time: do not re-read files you already know the "
                        "contents of, do not call check_syntax more than once per file, and "
                        "prioritize finishing every remaining planned file over polishing ones "
                        "that are already correct.\n\n" + (prior_failure_output or "")
                    )
                verify_result = {
                    "passed": False,
                    "steps": [
                        {
                            "name": "planned files touched",
                            "status": "failed",
                            "output": prior_failure_output,
                        }
                    ],
                }
                continue

            verify_result = self.verifier.verify(project_id, feature_id, code_plan_json)

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

    def _find_plan_gaps(
        self, code_plan_json: dict[str, Any], touched: dict[str, list[str]]
    ) -> list[dict[str, str]]:
        """
        Deterministically compute which planned files were never created,
        modified, or deleted this attempt -- computed from git (via
        workspace_service.get_touched_files), never trusted from the coding
        loop's own self-report that it "finished." Runs before the expensive
        verify.py gate (npm install x2, server boot, client build) so a
        plan that's silently incomplete fails fast and cheaply instead of
        only being caught after minutes of infra checks that were never
        going to matter.
        """
        touched_paths = set(touched["added"]) | set(touched["modified"]) | set(touched["deleted"])

        return [
            {
                "path": file_entry["path"],
                "action": file_entry.get("action", ""),
                "rationale": file_entry.get("rationale", ""),
            }
            for file_entry in code_plan_json.get("files", [])
            if file_entry.get("path") and file_entry["path"] not in touched_paths
        ]

    def _format_plan_gaps(self, gaps: list[dict[str, str]]) -> str:
        lines = [f"- {gap['path']} (action: {gap['action']}, rationale: {gap['rationale']})" for gap in gaps]
        return (
            "The following planned files were never created, modified, or deleted in this "
            "attempt -- implement these before doing anything else:\n" + "\n".join(lines)
        )

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
