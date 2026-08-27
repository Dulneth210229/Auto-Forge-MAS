"""
QA Agent.

Turns a Coder-Agent-generated feature into real, executable evidence of whether it works: writes
Unit tests (one module in isolation), Integration tests (a Route Handler together with the real
model/lib files it imports, exercising the real request -> handler -> data flow), and Regression
tests (one per the feature's own approved acceptance criteria) -- see discovery.py/generator.py
for how each category is discovered and generated, and prompt.py for the exact structured
response shape every generation call returns (test_cases metadata + real test_code, parsed the
same resilient way Security Agent's LLM review layer already established: extract, validate,
degrade to a fallback on anything malformed, never fail the whole run over one bad response).

Runs the real suite through Jest inside the same sandboxed execution path every other agent uses
(see executor.py for why Jest replaced the earlier zero-dependency `node:test` runner: its
built-in `--json` output already contains real per-test structured results), then matches each
execution result back to the QaTestCase that planned it (by test_file + name) so the saved report
carries BOTH halves for every test: what it was written to verify (target file/function, inputs,
expected behavior) and what actually happened when it ran (status, duration, the real failure
message).

Auto-approved stage (`ApprovalStatus.APPROVED`), matching QA's continued membership in
`AUTO_APPROVED_STAGES` (graph_orchestrator_service.py) -- unlike Security Agent, this was not
part of the direct request to change; a human reviews the report after the fact rather than
gating on it.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator

from app.agents.qa_agent import discovery, executor, generator
from app.agents.qa_agent.prompt import QA_CHAT_SYSTEM_PROMPT
from app.agents.qa_agent.schemas import QAAgentOutput, QaTestCase
from app.core.enums import AgentName, ApprovalStatus, ArtifactFormat, ArtifactType
from app.services.artifact_service import artifact_service
from app.services.in_memory_store import store
from app.services.workspace_service import workspace_service
from app.utils.file_manager import read_json_file
from app.utils.logger import get_logger

logger = get_logger(__name__)

GENERATED_TESTS_DIRNAME = "generated_tests"
CATEGORIES = ("unit", "integration", "regression")


def _build_markdown_report(report: dict) -> str:
    lines = [
        f"# QA Report -- {report['project_name']} / {report['feature_name']}",
        "",
        f"Generated: {report['generated_at']}",
        f"Framework: {report['framework_used']}",
        f"Tests written: {report['tests_generated']} "
        f"(unit {report['tests_by_category']['unit']['total']}, "
        f"integration {report['tests_by_category']['integration']['total']}, "
        f"regression {report['tests_by_category']['regression']['total']})",
        f"Result: {report['tests_passed']} passed, {report['tests_failed']} failed, "
        f"{report['tests_skipped']} skipped",
        "",
        "## Test cases",
        "",
    ]
    if not report["test_cases"]:
        lines.append("No test cases were generated.")
    for tc in report["test_cases"]:
        status = tc["status"].upper()
        loc = f"{tc['target_file']}::{tc['target_function']}" if tc["target_function"] else tc["target_file"]
        lines.append(f"- **[{status}]** ({tc['category']}) {tc['name']} -- targets `{loc}`")
        if tc.get("failure_message"):
            lines.append(f"  - {tc['failure_message'].splitlines()[0]}")
    lines += [
        "",
        "## Out of scope for this pass",
        "",
    ]
    for path in report["out_of_scope_modules"]:
        lines.append(f"- `{path}`")
    if report["raw_stderr"]:
        lines += ["", "## Test runner stderr (tail)", "", "```", report["raw_stderr"][-2000:], "```"]
    return "\n".join(lines)


class QAAgent:
    async def run(self, **kwargs) -> QAAgentOutput:
        feature_id = kwargs["feature_id"]
        feature = store.features.get(feature_id)
        project = store.projects.get(feature["project_id"])

        repo_path = workspace_service.get_repo_path(project["project_id"])

        if not repo_path.exists():
            logger.warning("QA Agent: repo path %s does not exist, skipping", repo_path)
            return QAAgentOutput(status="skipped", message=f"No workspace found at {repo_path} yet.")

        unit_targets = discovery.discover_unit_test_targets(repo_path)
        integration_targets = discovery.discover_integration_test_targets(repo_path)
        out_of_scope = discovery.discover_out_of_scope_modules(repo_path)
        acceptance_criteria = self._load_approved_acceptance_criteria(feature_id)

        generated_dir = repo_path / GENERATED_TESTS_DIRNAME
        generated_dir.mkdir(exist_ok=True)
        # A fresh run must not accumulate stale test files from a previous run (a since-renamed/
        # deleted module's old test would otherwise keep being executed and reported forever).
        for stale in generated_dir.glob("*.test.ts"):
            stale.unlink()

        all_test_cases: list[QaTestCase] = []

        for target in unit_targets:
            result = await generator.generate_unit_tests(target)
            if result is None:
                continue
            filename = self._write_test_file(generated_dir, Path(target["rel"]).stem, "unit", result.test_code)
            for tc in result.test_cases:
                tc.test_file = filename
                all_test_cases.append(tc)

        for target in integration_targets:
            result = await generator.generate_integration_tests(target)
            if result is None:
                continue
            filename = self._write_test_file(
                generated_dir, Path(target["route_rel"]).parent.name, "integration", result.test_code
            )
            for tc in result.test_cases:
                tc.test_file = filename
                tc.category = "integration"
                all_test_cases.append(tc)

        regression_result = await generator.generate_regression_tests(
            acceptance_criteria, integration_targets[0] if integration_targets else None
        )
        if regression_result is not None:
            filename = self._write_test_file(generated_dir, feature["feature_name"], "regression", regression_result.test_code)
            for tc in regression_result.test_cases:
                tc.test_file = filename
                tc.category = "regression"
                all_test_cases.append(tc)

        if all_test_cases:
            run_result = executor.run_tests(repo_path, project["project_id"])
        else:
            run_result = {"results": [], "passed": 0, "failed": 0, "skipped": 0, "exit_code": None, "raw_stderr": ""}

        merged_test_cases = self._merge_results(all_test_cases, run_result["results"])
        tests_by_category = self._count_by_category(merged_test_cases)

        report = {
            "project_name": project["project_name"],
            "feature_name": feature["feature_name"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "framework_used": "jest",
            "tests_generated": len(all_test_cases),
            "tests_passed": run_result["passed"],
            "tests_failed": run_result["failed"],
            "tests_skipped": run_result["skipped"],
            "tests_by_category": tests_by_category,
            "test_cases": merged_test_cases,
            "out_of_scope_modules": out_of_scope,
            "raw_stderr": run_result["raw_stderr"],
        }
        markdown = _build_markdown_report(report)

        json_artifact = artifact_service.save_json_artifact(
            project=project, feature=feature,
            agent_name=AgentName.QA, artifact_type=ArtifactType.QA_REPORT,
            filename="qa_report_v{version}.json", data=report,
            approval_status=ApprovalStatus.APPROVED,
        )
        md_artifact = artifact_service.save_text_artifact(
            project=project, feature=feature,
            agent_name=AgentName.QA, artifact_type=ArtifactType.QA_REPORT,
            artifact_format=ArtifactFormat.MARKDOWN,
            filename="qa_report_v{version}.md", content=markdown,
            version_override=json_artifact.version,
            approval_status=ApprovalStatus.APPROVED,
        )

        logger.info(
            "QA Agent finished for feature_id=%s: %d generated, %d passed, %d failed, %d skipped",
            feature_id, len(all_test_cases), run_result["passed"], run_result["failed"], run_result["skipped"],
        )

        return QAAgentOutput(
            qa_report_json=report,
            status="completed",
            framework_used="jest",
            tests_generated=len(all_test_cases),
            tests_passed=run_result["passed"],
            tests_failed=run_result["failed"],
            tests_skipped=run_result["skipped"],
            artifact_ids=[json_artifact.artifact_id, md_artifact.artifact_id],
            message=f"{run_result['passed']} passed, {run_result['failed']} failed, "
                    f"{run_result['skipped']} skipped.",
        )

    def _write_test_file(self, generated_dir: Path, stem: str, category: str, test_code: str) -> str:
        import re
        safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "-", stem).strip("-") or category
        filename = f"{safe_stem}.{category}.test.ts"
        (generated_dir / filename).write_text(test_code, encoding="utf-8")
        return filename

    def _merge_results(self, test_cases: list[QaTestCase], results: list[dict]) -> list[dict]:
        """Matches each planned QaTestCase to its real execution result by (test_file, name) --
        the same pairing prompt.py's own testing-conventions section instructs the LLM to
        preserve (every test_cases[].name must appear verbatim as the real test's title). A
        planned case with no matching result (e.g. the file failed to even parse/load) is still
        reported, marked "skipped" with an explicit note, rather than silently disappearing."""
        results_by_key = {(r["test_file"], r["name"]): r for r in results}
        merged = []
        for tc in test_cases:
            match = results_by_key.get((tc.test_file, tc.name))
            merged.append({
                "name": tc.name,
                "category": tc.category,
                "target_file": tc.target_file,
                "target_function": tc.target_function,
                "inputs": tc.inputs,
                "expected_behavior": tc.expected_behavior,
                "test_file": tc.test_file,
                "method": tc.method,
                "status": match["status"] if match else "skipped",
                "duration_ms": match.get("duration_ms") if match else None,
                "failure_message": (match.get("failure_message") if match
                                     else ("This test file did not produce a matching result -- "
                                           "it may have failed to load/parse; see stderr below.")),
            })
        return merged

    def _count_by_category(self, merged_test_cases: list[dict]) -> dict:
        counts = {cat: {"total": 0, "passed": 0, "failed": 0, "skipped": 0} for cat in CATEGORIES}
        for tc in merged_test_cases:
            bucket = counts.setdefault(tc["category"], {"total": 0, "passed": 0, "failed": 0, "skipped": 0})
            bucket["total"] += 1
            bucket[tc["status"]] = bucket.get(tc["status"], 0) + 1
        return counts

    def _load_approved_acceptance_criteria(self, feature_id: str) -> list[dict]:
        artifact = self._find_latest_approved_artifact(
            feature_id=feature_id,
            agent_name=AgentName.REQUIREMENT,
            artifact_type=ArtifactType.SRS,
            artifact_format=ArtifactFormat.JSON,
        )
        if not artifact:
            return []
        srs = read_json_file(artifact["file_path"])
        return srs.get("acceptance_criteria", []) if srs else []

    def _find_latest_approved_artifact(self, feature_id: str, agent_name: AgentName,
                                        artifact_type: ArtifactType, artifact_format: ArtifactFormat) -> dict | None:
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

    def _load_latest_qa_report(self, feature_id: str) -> dict | None:
        artifact = self._find_latest_approved_artifact(
            feature_id=feature_id, agent_name=AgentName.QA,
            artifact_type=ArtifactType.QA_REPORT, artifact_format=ArtifactFormat.JSON,
        )
        if not artifact:
            return None
        return read_json_file(artifact["file_path"])

    def _summarize_report_for_chat(self, report: dict) -> str:
        lines = [
            f"QA report for {report['feature_name']} (generated {report['generated_at']}): "
            f"{report['tests_passed']} passed, {report['tests_failed']} failed, "
            f"{report['tests_skipped']} skipped.",
        ]
        for tc in report.get("test_cases", []):
            loc = f"{tc['target_file']}::{tc['target_function']}" if tc.get("target_function") else tc["target_file"]
            line = f"- [{tc['status'].upper()}] ({tc['category']}) {tc['name']} -- targets {loc}"
            if tc.get("failure_message"):
                line += f" -- failure: {tc['failure_message'][:300]}"
            lines.append(line)
        return "\n".join(lines)

    def _get_chat_history(self, feature_id: str) -> list[dict]:
        document = store.qa_conversations.get(feature_id)
        return document.get("turns", []) if document else []

    def _append_chat_turns(self, feature_id: str, new_turns: list[dict]) -> None:
        existing = self._get_chat_history(feature_id)
        store.qa_conversations[feature_id] = {"feature_id": feature_id, "turns": existing + new_turns}

    async def chat_stream(self, feature_id: str, message: str) -> AsyncGenerator[dict[str, Any], None]:
        """Pure Q&A -- see prompt.py's QA_CHAT_SYSTEM_PROMPT for the explicit "discuss, never
        edit code" boundary (an explicit, separate frontend action re-uses the Coder Agent's own
        real revise() flow for actually fixing something -- see
        qaReportToRevisionComment.js). Streams real tokens via the configured provider's own
        `.stream()` (Ollama or Anthropic, whichever this agent is currently set to --
        llm_provider_service.get_provider, the exact one-shot/no-tool-calling call shape Security
        Agent's LLM review layer already established, so either provider family works with no
        tool-calling requirement), then persists both the human's message and the full reply to
        store.qa_conversations so a reload doesn't lose the conversation."""
        from app.services.llm_provider_service import llm_provider_service

        report = self._load_latest_qa_report(feature_id)
        report_context = (
            self._summarize_report_for_chat(report) if report
            else "No QA report has been generated for this feature yet."
        )

        history = self._get_chat_history(feature_id)
        transcript_lines = [f"{turn['role'].capitalize()}: {turn['content']}" for turn in history]
        transcript_lines.append(f"User: {message}")
        prompt = "\n\n".join(transcript_lines)
        system_prompt = f"{QA_CHAT_SYSTEM_PROMPT}\n\nCurrent QA report:\n{report_context}"

        try:
            provider = llm_provider_service.get_provider(agent_name=AgentName.QA.value)
        except Exception as error:  # noqa: BLE001 -- surface as a real error event, don't crash the route
            yield {"type": "error", "message": f"QA chat could not reach a configured provider: {error}"}
            return

        full_reply = ""
        try:
            async for chunk in provider.stream(prompt, system_prompt=system_prompt):
                full_reply += chunk
                yield {"type": "token", "text": chunk}
        except Exception as error:  # noqa: BLE001 -- surface as a real error event, don't crash the route
            yield {"type": "error", "message": f"QA chat failed: {error}"}
            return

        now = datetime.now(timezone.utc).isoformat()
        self._append_chat_turns(feature_id, [
            {"role": "user", "content": message, "created_at": now},
            {"role": "assistant", "content": full_reply, "created_at": now},
        ])

        yield {"type": "done", "message": full_reply}


qa_agent = QAAgent()