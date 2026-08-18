"""
QA Agent.

Real implementation, replacing the earlier placeholder that always returned
{"status": "skipped"}. Scans the generated project's workspace for
pure-logic modules it can test without a DOM renderer (see testing.py's
module docstring for the exact, deliberately conservative scope), generates
a test file per module -- through the configured LLM when reachable, through
a deterministic template fallback when it is not -- saves the generated
suite under generated_tests/ inside the project's own workspace, executes it
through the same sandboxed command-execution path every other agent uses,
and summarizes the raw pass/fail output into a QAAgentOutput rather than
exposing raw test-runner output directly.

Auto-approved stage, same reasoning as Security Agent: no interrupt() gate
yet, a human reviews the resulting report artifact after the fact.
"""

from datetime import datetime, timezone
from pathlib import Path

from app.agents.qa_agent.schemas import QAAgentOutput
from app.agents.qa_agent.testing import (
    detect_test_framework,
    discover_out_of_scope_modules,
    discover_testable_modules,
    generate_tests_for_module,
    run_tests,
)
from app.core.enums import AgentName, ApprovalStatus, ArtifactFormat, ArtifactType
from app.services.artifact_service import artifact_service
from app.services.in_memory_store import store
from app.services.workspace_service import workspace_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

GENERATED_TESTS_DIRNAME = "generated_tests"


def _build_markdown_report(report: dict) -> str:
    lines = [
        f"# QA Report -- {report['project_name']} / {report['feature_name']}",
        "",
        f"Generated: {report['generated_at']}",
        f"Framework: {report['framework_used']}",
        f"Tests generated: {report['tests_generated']} across "
        f"{len(report['files'])} file(s)",
        f"Result: {report['tests_passed']} passed, {report['tests_failed']} failed, "
        f"{report['tests_skipped']} skipped",
        "",
        "## Generated files",
        "",
    ]
    for f in report["files"]:
        lines.append(f"- `{f['module']}` -> `{f['test_file']}` (generated via {f['method']})")
    lines += [
        "",
        "## Out of scope for this runner (see testing.py docstring)",
        "",
    ]
    for path in report["out_of_scope_modules"]:
        lines.append(f"- `{path}`")
    lines += ["", "## Raw test-runner output (tail)", "", "```", report["raw_output"], "```"]
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

        framework = detect_test_framework(repo_path)
        modules = discover_testable_modules(repo_path)
        out_of_scope = discover_out_of_scope_modules(repo_path)

        generated_dir = repo_path / GENERATED_TESTS_DIRNAME
        generated_dir.mkdir(exist_ok=True)

        files_written = []
        for module in modules:
            source, method = generate_tests_for_module(module, framework, invoke_llm=None)
            if not source:
                continue
            test_filename = Path(module["rel"]).stem + ".test.ts"
            test_path = generated_dir / test_filename
            test_path.write_text(source, encoding="utf-8")
            files_written.append({"module": module["rel"], "test_file": test_filename, "method": method})

        run_result = run_tests(repo_path, generated_dir, project["project_id"]) if files_written else {
            "passed": 0, "failed": 0, "skipped": 0, "exit_code": None, "raw_output": "No testable modules found."
        }

        report = {
            "project_name": project["project_name"],
            "feature_name": feature["feature_name"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "framework_used": framework,
            "tests_generated": len(files_written),
            "files": files_written,
            "out_of_scope_modules": out_of_scope,
            "tests_passed": run_result["passed"],
            "tests_failed": run_result["failed"],
            "tests_skipped": run_result["skipped"],
            "raw_output": run_result["raw_output"],
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
            feature_id, len(files_written), run_result["passed"], run_result["failed"], run_result["skipped"],
        )

        return QAAgentOutput(
            qa_report_json=report,
            status="completed",
            framework_used=framework,
            tests_generated=len(files_written),
            tests_passed=run_result["passed"],
            tests_failed=run_result["failed"],
            tests_skipped=run_result["skipped"],
            artifact_ids=[json_artifact.artifact_id, md_artifact.artifact_id],
            message=f"{run_result['passed']} passed, {run_result['failed']} failed, "
                    f"{run_result['skipped']} skipped.",
        )


qa_agent = QAAgent()
