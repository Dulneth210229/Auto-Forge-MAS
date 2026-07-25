"""
Domain Agent.

Purpose:
- Retrieve domain knowledge (RAG: embed query -> ChromaDB similarity search -> top-K chunks)
  for the approved SRS of one feature.
- Ask the LLM to enhance the SRS using ONLY that retrieved knowledge, producing a full
  Enhanced SRS JSON (inline-flagged with what was added/changed) plus a human-readable
  Domain Improvements JSON summary.
- Convert JSON to Markdown inside Domain Agent (mirrors Requirement Agent's approach).
- Save Markdown, Enhanced SRS JSON, and Domain Improvements JSON as a shared-version artifact
  group.

This file does not change:
- LLM provider
- shared markdown utilities
- other agents

Retrieval is deterministic Python (via domain_knowledge_service), never an LLM tool-calling
loop -- the Domain Agent stays on the one-shot BaseLLMProvider path like Requirement and
Architecture Agents, per this repo's build spec.
"""

import copy
import json
import re
from datetime import datetime, timezone

from app.agents.domain_agent.domain_validator import DomainEnhancementValidationError, DomainEnhancementValidator
from app.agents.domain_agent.markdown_builder import DomainEnhancedSRSMarkdownBuilder
from app.agents.domain_agent.prompt import (
    DOMAIN_AGENT_SYSTEM_PROMPT,
    DOMAIN_REVISION_SYSTEM_PROMPT,
    JSON_REPAIR_PROMPT,
    build_domain_revision_prompt,
    build_domain_user_prompt,
    build_json_repair_prompt,
)
from app.agents.domain_agent.schemas import DomainAgentOutput
from app.core.enums import AgentName, ApprovalStatus, ArtifactFormat, ArtifactType, FeatureStatus
from app.schemas.agent_schema import AgentRunResponse
from app.schemas.domain_schema import DomainAgentReviseRequest, DomainAgentRunRequest
from app.services.artifact_service import artifact_service
from app.services.domain_knowledge_service import domain_knowledge_service
from app.services.in_memory_store import store
from app.services.llm_provider_service import llm_provider_service
from app.utils.file_manager import read_json_file
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Maximum characters of SRS prose fed into the retrieval query embedding. Capped to keep the
# query focused on dense, domain-relevant text rather than the entire SRS JSON dump.
RETRIEVAL_QUERY_MAX_CHARS = 3000


class DomainAgent:
    """
    Main Domain Agent class.

    This class controls the full Domain Agent process:
    1. Read the latest approved SRS JSON for a feature.
    2. Retrieve relevant domain knowledge chunks (RAG).
    3. Call LLM to produce Enhanced SRS JSON + Domain Improvements JSON.
    4. Validate the result against the raw SRS and the retrieved chunks.
    5. Build Markdown from the validated JSON.
    6. Save all three artifacts under one shared version.
    """

    REQUIRED_KEYS = [
        "project_id",
        "project_name",
        "project_type",
        "feature_id",
        "feature_name",
        "target_stack",
        "architectural_style",
        "business_goal",
        "functional_requirements",
        "non_functional_requirements",
        "acceptance_criteria",
        "constraints",
        "assumptions",
        "traceability",
    ]

    def __init__(self):
        self.markdown_builder = DomainEnhancedSRSMarkdownBuilder()
        self.validator = DomainEnhancementValidator()

    async def run(self, feature_id: str, request: DomainAgentRunRequest) -> AgentRunResponse:
        """
        Run the Domain Agent.

        This method is called from:
            POST /features/{feature_id}/agents/domain/run
        """

        logger.info("Domain Agent started for feature_id=%s", feature_id)

        feature = store.features.get(feature_id)

        if not feature:
            raise ValueError("Feature not found.")

        project = store.projects.get(feature["project_id"])

        if not project:
            raise ValueError("Project not found for this feature.")

        srs_artifact = self._find_latest_approved_srs_artifact(feature_id)

        if not srs_artifact:
            raise ValueError(
                "No approved SRS JSON artifact found. "
                "Approve Requirement Agent SRS JSON before running Domain Agent."
            )

        srs_json = read_json_file(srs_artifact["file_path"])

        feature["feature_status"] = FeatureStatus.IN_PROGRESS
        feature["current_agent"] = AgentName.DOMAIN

        retrieved_chunks = self._retrieve_domain_knowledge(srs_json)

        output = await self._generate_domain_output(
            project=project,
            feature=feature,
            srs_json=srs_json,
            retrieved_chunks=retrieved_chunks,
            human_comment=request.human_comment,
            srs_version=srs_artifact.get("version", 1),
        )

        artifact_ids = self._save_domain_artifacts(project=project, feature=feature, output=output)

        logger.info(
            "Domain Agent completed for feature_id=%s artifacts=%s",
            feature_id,
            artifact_ids,
        )

        return AgentRunResponse(
            feature_id=feature_id,
            agent_name=AgentName.DOMAIN,
            status="completed",
            message=(
                "Domain Agent completed successfully. Enhanced SRS Markdown, Enhanced SRS "
                "JSON, and Domain Improvements JSON artifacts were generated. Human approval "
                "is required before Architecture Agent uses the Enhanced SRS."
            ),
            artifact_ids=artifact_ids,
        )

    def _retrieve_domain_knowledge(self, srs_json: dict) -> list[dict]:
        """
        Retrieve domain knowledge chunks relevant to this feature's SRS.

        Delegates to domain_knowledge_service.retrieve(), which never raises --
        an empty knowledge base or embedding failure just means no chunks.
        """

        query = self._build_retrieval_query(srs_json)
        return domain_knowledge_service.retrieve(query)

    def _build_retrieval_query(self, srs_json: dict, extra_text: str | None = None) -> str:
        """
        Build the retrieval query text from the SRS's dense, domain-relevant prose fields.

        Deliberately excludes NFRs/constraints (generic, low domain-signal) and does not dump
        the raw JSON (punctuation/keys/ids add embedding noise).
        """

        parts: list[str] = [
            str(srs_json.get("feature_name", "")),
            str(srs_json.get("business_goal", "")),
        ]

        parts.extend(str(item) for item in srs_json.get("scope", []) if item)

        parts.extend(
            item.get("description", "")
            for item in srs_json.get("functional_requirements", [])
            if isinstance(item, dict) and item.get("description")
        )

        parts.extend(
            item.get("description", "")
            for item in srs_json.get("acceptance_criteria", [])
            if isinstance(item, dict) and item.get("description")
        )

        if extra_text:
            parts.append(extra_text)

        query = " ".join(part for part in parts if part)

        return query[:RETRIEVAL_QUERY_MAX_CHARS]

    async def _generate_domain_output(
        self,
        project: dict,
        feature: dict,
        srs_json: dict,
        retrieved_chunks: list[dict],
        human_comment: str | None,
        srs_version: int,
    ) -> DomainAgentOutput:
        """
        Generate Enhanced SRS + Domain Improvements output.

        Reliability ladder (mirrors Requirement Agent):
        - one-shot LLM call
        - parse + validate
        - on failure, one JSON-repair LLM call
        - on failure again, a deterministic fallback that never fails
        """

        provider = llm_provider_service.get_provider()

        prompt = build_domain_user_prompt(
            project=project,
            feature=feature,
            srs_json=srs_json,
            retrieved_chunks=retrieved_chunks,
            human_comment=human_comment,
        )

        raw_output = await provider.invoke_agent([
            {"role": "system", "content": DOMAIN_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])

        fallback_used = False
        fallback_reason = None

        try:
            enhanced_srs_json, domain_improvements_json = self._parse_and_validate_json(
                raw_output, srs_json, retrieved_chunks
            )

        except Exception as first_error:
            logger.warning("Initial Enhanced SRS JSON parse/validation failed: %s", first_error)

            repair_prompt = build_json_repair_prompt(raw_output)

            repaired_output = await provider.invoke_agent([
                {"role": "system", "content": JSON_REPAIR_PROMPT},
                {"role": "user", "content": repair_prompt},
            ])

            try:
                enhanced_srs_json, domain_improvements_json = self._parse_and_validate_json(
                    repaired_output, srs_json, retrieved_chunks
                )

            except Exception as second_error:
                logger.warning("Enhanced SRS JSON repair failed. Using fallback. Error=%s", second_error)

                fallback_used = True
                fallback_reason = str(second_error)
                enhanced_srs_json, domain_improvements_json = self._build_fallback_domain_output(
                    srs_json, retrieved_chunks, reason=fallback_reason
                )

        self._finalize_enhanced_srs_metadata(
            enhanced_srs_json, srs_version, retrieved_chunks, fallback_used, fallback_reason
        )

        enhanced_srs_markdown = self.markdown_builder.build(enhanced_srs_json, domain_improvements_json)

        return DomainAgentOutput(
            enhanced_srs_markdown=enhanced_srs_markdown,
            enhanced_srs_json=enhanced_srs_json,
            domain_improvements_json=domain_improvements_json,
        )

    def _parse_and_validate_json(
        self, raw_output: str, srs_json: dict, retrieved_chunks: list[dict]
    ) -> tuple[dict, dict]:
        """
        Parse and validate LLM JSON output.

        Kept inside Domain Agent to avoid changing shared/common JSON utilities.
        """

        parsed = self._extract_json_object(raw_output)

        if "enhanced_srs_json" not in parsed or "domain_improvements_json" not in parsed:
            raise ValueError(
                "LLM output missing required top-level keys: enhanced_srs_json, domain_improvements_json"
            )

        enhanced_srs_json = parsed["enhanced_srs_json"]
        domain_improvements_json = parsed["domain_improvements_json"]

        if not isinstance(enhanced_srs_json, dict) or not isinstance(domain_improvements_json, dict):
            raise ValueError("enhanced_srs_json and domain_improvements_json must both be JSON objects.")

        missing = [key for key in self.REQUIRED_KEYS if key not in enhanced_srs_json]

        if missing:
            raise ValueError(f"Missing required Enhanced SRS keys: {missing}")

        try:
            self.validator.validate(srs_json, enhanced_srs_json, domain_improvements_json, retrieved_chunks)
        except DomainEnhancementValidationError as error:
            raise ValueError(str(error)) from error

        return enhanced_srs_json, domain_improvements_json

    def _extract_json_object(self, text: str) -> dict:
        """
        Extract a JSON object from LLM output.

        This is Domain-Agent-specific. It does not change shared json_utils.py.
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
            raise ValueError("No JSON object found in LLM output.")

        possible_json = cleaned[start:end + 1]

        return json.loads(possible_json)

    def _build_fallback_domain_output(
        self, srs_json: dict, retrieved_chunks: list[dict], reason: str
    ) -> tuple[dict, dict]:
        """
        Build a fallback Enhanced SRS + Domain Improvements pair if LLM generation fails.

        Why no fabricated FR-DOM-* items:
        There is no sensible way to regex/keyword-enrich real domain content, and inventing
        content here would violate the RAG honesty guarantee. The fallback leaves the SRS
        content unchanged and honestly reports why no enrichment was applied.
        """

        enhanced_srs_json = copy.deepcopy(srs_json)

        if not retrieved_chunks:
            no_changes_note = "No relevant domain knowledge was retrieved for this feature."
        else:
            no_changes_note = f"Domain knowledge was retrieved but automatic enrichment failed: {reason}"

        domain_improvements_json = {
            "summary": "No domain enrichment was applied to this SRS.",
            "knowledge_sources_used": [],
            "additions": [],
            "modifications": [],
            "no_changes_note": no_changes_note,
        }

        return enhanced_srs_json, domain_improvements_json

    def _finalize_enhanced_srs_metadata(
        self,
        enhanced_srs_json: dict,
        srs_version: int,
        retrieved_chunks: list[dict],
        fallback_used: bool,
        fallback_reason: str | None,
    ) -> None:
        """
        Deterministically set domain_enrichment_metadata, overwriting whatever (if anything)
        the LLM produced for it -- this data must be trustworthy regardless of LLM behavior.
        """

        sources_considered = sorted({
            chunk.get("source_document") for chunk in retrieved_chunks if chunk.get("source_document")
        })

        metadata = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "based_on_srs_version": srs_version,
            "knowledge_sources_considered": sources_considered,
            "fallback_used": fallback_used,
        }

        if fallback_used and fallback_reason:
            metadata["fallback_reason"] = fallback_reason

        enhanced_srs_json["domain_enrichment_metadata"] = metadata

    async def revise(self, feature_id: str, request: DomainAgentReviseRequest) -> AgentRunResponse:
        """
        Revise the latest Enhanced SRS for a feature.
        """

        logger.info("Domain Agent revision started for feature_id=%s", feature_id)

        feature = store.features.get(feature_id)

        if not feature:
            raise ValueError("Feature not found.")

        project = store.projects.get(feature["project_id"])

        if not project:
            raise ValueError("Project not found for this feature.")

        latest_enhanced_srs_artifact = self._find_latest_domain_json_artifact(feature_id, ArtifactType.ENHANCED_SRS)

        if not latest_enhanced_srs_artifact:
            raise ValueError(
                "No existing Enhanced SRS JSON artifact found. "
                "Run Domain Agent first before requesting revision."
            )

        latest_improvements_artifact = self._find_latest_domain_json_artifact(
            feature_id, ArtifactType.DOMAIN_IMPROVEMENTS
        )

        existing_enhanced_srs_json = read_json_file(latest_enhanced_srs_artifact["file_path"])
        existing_domain_improvements_json = (
            read_json_file(latest_improvements_artifact["file_path"]) if latest_improvements_artifact else {}
        )

        # Validation must be against the ORIGINAL raw SRS (dropped-id / consistency checks),
        # not the already-enhanced one.
        srs_artifact = self._find_latest_approved_srs_artifact(feature_id)

        if not srs_artifact:
            raise ValueError("No approved SRS JSON artifact found for this feature.")

        srs_json = read_json_file(srs_artifact["file_path"])

        retrieved_chunks = self._retrieve_domain_knowledge_for_revision(
            existing_enhanced_srs_json, request.revision_comment
        )

        output = await self._revise_domain_output(
            project=project,
            feature=feature,
            srs_json=srs_json,
            existing_enhanced_srs_json=existing_enhanced_srs_json,
            existing_domain_improvements_json=existing_domain_improvements_json,
            retrieved_chunks=retrieved_chunks,
            revision_comment=request.revision_comment,
            revised_by=request.revised_by,
            srs_version=srs_artifact.get("version", 1),
        )

        artifact_ids = self._save_domain_artifacts(project=project, feature=feature, output=output)

        logger.info(
            "Domain Agent revision completed for feature_id=%s artifacts=%s",
            feature_id,
            artifact_ids,
        )

        return AgentRunResponse(
            feature_id=feature_id,
            agent_name=AgentName.DOMAIN,
            status="revised",
            message=(
                "Enhanced SRS revised successfully. "
                "A new version was created and requires human approval."
            ),
            artifact_ids=artifact_ids,
        )

    def _retrieve_domain_knowledge_for_revision(
        self, existing_enhanced_srs_json: dict, revision_comment: str
    ) -> list[dict]:
        query = self._build_retrieval_query(existing_enhanced_srs_json, extra_text=revision_comment)
        return domain_knowledge_service.retrieve(query)

    def _carry_forward_previous_citations(self, existing_domain_improvements_json: dict) -> list[dict]:
        """
        Build synthetic chunk stubs for every source/chunk already cited in the previous
        Domain Improvements JSON.

        Why: revision retrieval is a fresh query and may not resurface every chunk a prior
        run legitimately cited. Without this, the validator's honesty check (no additions/
        modifications without retrieved evidence) would falsely fail a revision that simply
        preserves already-valid prior enrichment. These stubs are used for validation only --
        they are never shown to the LLM (the prompt only shows the fresh retrieval).
        """

        carried: dict[str, dict] = {}

        for section in ("additions", "modifications"):
            for record in existing_domain_improvements_json.get(section, []) or []:
                citation = record.get("domain_citation") or {}
                source_document = citation.get("source_document")
                chunk_id = citation.get("chunk_id")

                if source_document and chunk_id and chunk_id not in carried:
                    carried[chunk_id] = {
                        "chunk_id": chunk_id,
                        "source_document": source_document,
                        "text": "",
                    }

        return list(carried.values())

    def _merge_chunks(self, primary: list[dict], extra: list[dict]) -> list[dict]:
        seen = {chunk.get("chunk_id") for chunk in primary}
        merged = list(primary)

        for chunk in extra:
            if chunk.get("chunk_id") not in seen:
                merged.append(chunk)
                seen.add(chunk.get("chunk_id"))

        return merged

    async def _revise_domain_output(
        self,
        project: dict,
        feature: dict,
        srs_json: dict,
        existing_enhanced_srs_json: dict,
        existing_domain_improvements_json: dict,
        retrieved_chunks: list[dict],
        revision_comment: str,
        revised_by: str,
        srs_version: int,
    ) -> DomainAgentOutput:
        """
        Use the LLM to revise the existing Enhanced SRS + Domain Improvements JSON.

        If LLM revision fails, a fallback revision is created safely.
        """

        provider = llm_provider_service.get_provider()

        prompt = build_domain_revision_prompt(
            project=project,
            feature=feature,
            existing_enhanced_srs_json=existing_enhanced_srs_json,
            existing_domain_improvements_json=existing_domain_improvements_json,
            retrieved_chunks=retrieved_chunks,
            revision_comment=revision_comment,
            revised_by=revised_by,
        )

        raw_output = await provider.invoke_agent([
            {"role": "system", "content": DOMAIN_REVISION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])

        validation_chunks = self._merge_chunks(
            retrieved_chunks, self._carry_forward_previous_citations(existing_domain_improvements_json)
        )

        fallback_used = False
        fallback_reason = None

        try:
            enhanced_srs_json, domain_improvements_json = self._parse_and_validate_json(
                raw_output, srs_json, validation_chunks
            )

        except Exception as error:
            logger.warning("LLM Enhanced SRS revision failed. Using fallback revision. Error=%s", error)

            fallback_used = True
            fallback_reason = str(error)
            enhanced_srs_json, domain_improvements_json = self._build_fallback_revise_domain_output(
                existing_enhanced_srs_json,
                existing_domain_improvements_json,
                revision_comment,
                revised_by,
                fallback_reason,
            )

        self._finalize_enhanced_srs_metadata(
            enhanced_srs_json, srs_version, retrieved_chunks, fallback_used, fallback_reason
        )

        enhanced_srs_markdown = self.markdown_builder.build(enhanced_srs_json, domain_improvements_json)

        return DomainAgentOutput(
            enhanced_srs_markdown=enhanced_srs_markdown,
            enhanced_srs_json=enhanced_srs_json,
            domain_improvements_json=domain_improvements_json,
        )

    def _build_fallback_revise_domain_output(
        self,
        existing_enhanced_srs_json: dict,
        existing_domain_improvements_json: dict,
        revision_comment: str,
        revised_by: str,
        reason: str,
    ) -> tuple[dict, dict]:
        """
        Create a safe fallback revision if the LLM fails. Does not overwrite existing
        enrichment -- appends revision information and a review note.
        """

        enhanced_srs_json = copy.deepcopy(existing_enhanced_srs_json)

        enhanced_srs_json["revision_metadata"] = {
            "revision_type": "domain_enrichment_revision",
            "revision_comment": revision_comment,
            "revised_by": revised_by,
            "fallback_used": True,
            "fallback_reason": reason,
        }

        assumptions = enhanced_srs_json.get("assumptions", [])

        if not isinstance(assumptions, list):
            assumptions = []

        assumptions.append(f"Domain Agent revision requested by {revised_by}: {revision_comment}")
        assumptions.append(f"Fallback revision was used because LLM revision failed: {reason}")

        enhanced_srs_json["assumptions"] = assumptions

        domain_improvements_json = (
            copy.deepcopy(existing_domain_improvements_json)
            if existing_domain_improvements_json
            else {
                "summary": "",
                "knowledge_sources_used": [],
                "additions": [],
                "modifications": [],
                "no_changes_note": None,
            }
        )

        domain_improvements_json.setdefault("additions", [])
        domain_improvements_json.setdefault("modifications", [])
        domain_improvements_json["no_changes_note"] = (
            f"Revision requested ('{revision_comment}') could not be automatically applied: "
            f"{reason}. Existing enrichment was preserved unchanged."
        )

        return enhanced_srs_json, domain_improvements_json

    def _find_latest_approved_srs_artifact(self, feature_id: str) -> dict | None:
        """
        Find the latest APPROVED SRS JSON artifact for this feature.

        Private, enum-and-.value tolerant, matching Architecture/UI-UX/Coder Agent's existing
        private duplicates -- not artifact_service.get_latest_approved_artifact, which compares
        with bare == and does not tolerate the enum/.value mismatch some code paths produce.
        """

        matching_artifacts = []

        for artifact in store.artifacts.values():
            if artifact.get("feature_id") != feature_id:
                continue

            if artifact.get("agent_name") not in [AgentName.REQUIREMENT, AgentName.REQUIREMENT.value]:
                continue

            if artifact.get("artifact_type") not in [ArtifactType.SRS, ArtifactType.SRS.value]:
                continue

            if artifact.get("artifact_format") not in [ArtifactFormat.JSON, ArtifactFormat.JSON.value]:
                continue

            if artifact.get("approval_status") not in [ApprovalStatus.APPROVED, ApprovalStatus.APPROVED.value]:
                continue

            matching_artifacts.append(artifact)

        if not matching_artifacts:
            return None

        return max(matching_artifacts, key=lambda item: item.get("version", 1))

    def _find_latest_domain_json_artifact(self, feature_id: str, artifact_type: ArtifactType) -> dict | None:
        """
        Find the latest Domain Agent JSON artifact of the given type for this feature,
        regardless of approval status -- revision must build on the latest generated
        version even if it is still pending or was rejected.
        """

        matching_artifacts = []

        for artifact in store.artifacts.values():
            if artifact.get("feature_id") != feature_id:
                continue

            if artifact.get("agent_name") not in [AgentName.DOMAIN, AgentName.DOMAIN.value]:
                continue

            if artifact.get("artifact_type") not in [artifact_type, artifact_type.value]:
                continue

            if artifact.get("artifact_format") not in [ArtifactFormat.JSON, ArtifactFormat.JSON.value]:
                continue

            matching_artifacts.append(artifact)

        if not matching_artifacts:
            return None

        return max(matching_artifacts, key=lambda item: item.get("version", 1))

    def _save_domain_artifacts(self, project: dict, feature: dict, output: DomainAgentOutput) -> list[str]:
        """
        Save Enhanced SRS Markdown, Enhanced SRS JSON, and Domain Improvements JSON under one
        shared version number.
        """

        version = artifact_service.get_next_version(
            feature_id=feature["feature_id"],
            agent_name=AgentName.DOMAIN,
            artifact_type=ArtifactType.ENHANCED_SRS,
        )

        feature_slug = self._feature_slug(feature)

        markdown_artifact = artifact_service.save_text_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.DOMAIN,
            artifact_type=ArtifactType.ENHANCED_SRS,
            artifact_format=ArtifactFormat.MARKDOWN,
            filename=f"{feature_slug}_enhanced_srs_v{version}.md",
            content=output.enhanced_srs_markdown,
            version_override=version,
        )

        json_artifact = artifact_service.save_json_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.DOMAIN,
            artifact_type=ArtifactType.ENHANCED_SRS,
            filename=f"{feature_slug}_enhanced_srs_v{version}.json",
            data=output.enhanced_srs_json,
            version_override=version,
        )

        improvements_artifact = artifact_service.save_json_artifact(
            project=project,
            feature=feature,
            agent_name=AgentName.DOMAIN,
            artifact_type=ArtifactType.DOMAIN_IMPROVEMENTS,
            filename=f"{feature_slug}_domain_improvements_v{version}.json",
            data=output.domain_improvements_json,
            version_override=version,
        )

        return [
            markdown_artifact.artifact_id,
            json_artifact.artifact_id,
            improvements_artifact.artifact_id,
        ]

    def _feature_slug(self, feature: dict) -> str:
        feature_name = feature.get("feature_name", "feature")

        feature_slug = feature_name.lower().strip()
        feature_slug = re.sub(r"[^a-z0-9]+", "_", feature_slug)
        feature_slug = feature_slug.strip("_")

        return feature_slug or "feature"


domain_agent = DomainAgent()
