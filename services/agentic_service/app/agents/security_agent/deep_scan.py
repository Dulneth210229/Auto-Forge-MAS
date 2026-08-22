"""
Security Agent -- AI-model deep-code-read scan layer.

Distinct from agent.py's existing _run_llm_review_layer, which only ever shows the LLM a compact
findings SUMMARY (rule_id/severity/file/line/message strings), never real source. This module
shows the model REAL source file contents directly and asks it to identify genuine vulnerabilities
grounded in that code -- a genuinely new capability, not an extension of the summary-review layer.

Batches real file contents into a bounded number of LLM calls (one call per batch, capped by
MAX_DEEP_SCAN_BATCH_CHARS) -- mirrors this project's own established char-cap-batching precedent
(coder_agent/diff_builder.py's MAX_DIFF_TEXT_CHARS, coder_agent/prompt.py's
MAX_IMPLEMENTATION_SPEC_CHARS) so this never becomes one giant prompt (context-limit risk) nor one
call per file (excessive latency for a real generated project's file count).

Never raises -- mirrors _run_llm_review_layer's own resilience contract exactly: a single batch's
provider/parse failure is logged and skipped (that batch simply contributes zero findings), never
aborting the whole scan.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agents.security_agent.prompt import SECURITY_DEEP_SCAN_SYSTEM_PROMPT
from app.agents.security_agent.scanners import list_scannable_files
from app.agents.security_agent.schemas import SecurityDeepScanResult
from app.core.enums import AgentName
from app.utils.json_utils import extract_json_object
from app.utils.logger import get_logger

logger = get_logger(__name__)

MAX_DEEP_SCAN_BATCH_CHARS = 12_000


def _batch_files(repo_path: Path) -> list[list[tuple[str, str]]]:
    """
    Reads every scannable file's real text (rel_path, content) and groups consecutive files into
    batches whose combined rendered text stays under MAX_DEEP_SCAN_BATCH_CHARS. A single file
    larger than the cap alone becomes its own batch (truncated at construction time, not skipped
    -- partial real code is still more useful than nothing).
    """
    files = list_scannable_files(repo_path)
    batches: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    current_chars = 0

    for path in files:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(path.relative_to(repo_path))
        entry_chars = len(rel) + len(content) + 20  # rough overhead for the "# path\n```\n```" wrapper

        if current and current_chars + entry_chars > MAX_DEEP_SCAN_BATCH_CHARS:
            batches.append(current)
            current = []
            current_chars = 0

        current.append((rel, content))
        current_chars += entry_chars

    if current:
        batches.append(current)
    return batches


def _render_batch(batch: list[tuple[str, str]]) -> str:
    parts = []
    for rel, content in batch:
        parts.append(f"# {rel}\n\n```\n{content}\n```\n")
    return "\n".join(parts)


async def run_ai_model_deep_scan(repo_path: Path) -> tuple[str, list[dict[str, Any]]]:
    """
    Returns (status message, list of SecurityFinding-shaped dicts). Never raises -- an unreachable
    provider or a malformed/unparseable response for any one batch degrades that batch to zero
    findings, so the deterministic findings this layer is combined with are always unaffected.
    """
    batches = _batch_files(repo_path)
    if not batches:
        return "No scannable source files found for the AI model to review.", []

    try:
        from app.services.llm_provider_service import llm_provider_service

        provider = llm_provider_service.get_provider(agent_name=AgentName.SECURITY.value)
    except Exception as error:  # noqa: BLE001 -- an unreachable provider must not fail the whole scan
        logger.warning("Security Agent AI-model deep scan: no provider available, skipping: %s", error)
        return (
            f"Skipped -- LLM provider unreachable in this run ({type(error).__name__}). "
            f"The deterministic layers in this report are unaffected and are its evidence.",
            [],
        )

    all_findings: list[dict[str, Any]] = []
    batches_ok = 0
    batches_failed = 0
    finding_index = 1

    for batch in batches:
        batch_text = _render_batch(batch)
        try:
            raw_output = await provider.invoke_agent([
                {"role": "system", "content": SECURITY_DEEP_SCAN_SYSTEM_PROMPT},
                {"role": "user", "content": f"Review this real source code:\n\n{batch_text}"},
            ])
            parsed = extract_json_object(raw_output)
            result = SecurityDeepScanResult.model_validate(parsed)
        except Exception as error:  # noqa: BLE001 -- one bad batch must not fail the whole scan
            logger.warning(
                "Security Agent AI-model deep scan: batch of %d file(s) failed, skipping: %s",
                len(batch), error,
            )
            batches_failed += 1
            continue

        batches_ok += 1
        for item in result.findings:
            all_findings.append({
                "id": f"SEC-AI-DEEPSCAN:{finding_index}",
                "rule_id": "SEC-AI-DEEPSCAN",
                "layer": "ai_model_deep_scan",
                "severity": item.severity,
                "cwe": item.cwe or "N/A",
                "file": item.file,
                "line": item.line,
                "message": f"{item.title} -- {item.description}".strip(" -"),
                "root_cause": item.root_cause,
                "recommendation": item.recommendation,
            })
            finding_index += 1

    status = (
        f"AI model deep scan ran over {len(batches)} batch(es) of real source code "
        f"({batches_ok} succeeded, {batches_failed} failed): {len(all_findings)} finding(s)."
    )
    return status, all_findings
