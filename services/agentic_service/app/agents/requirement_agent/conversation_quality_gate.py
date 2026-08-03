"""
Requirement Agent conversation quality gate.

Deterministic (no LLM), same idiom as domain_validator.py / plan_validator.py elsewhere in this
codebase -- a small, rule-based check of whether the current conversation's srs_preview is
concrete enough to confirm as the real SRS. `ready=False` never blocks a human from confirming
anyway (see RequirementConversationConfirmRequest.override_quality_gate); it only means the
reasons must be shown and explicitly overridden, not silently ignored.

Only Tier 1 fields (see conversation_engine.TIER_1_FIELDS) being auto-assumed rather than
answered is treated as blocking on its own -- these are the fields the Architecture Agent depends
on most heavily, and a real, documented failure in this project (see conversation_engine.py's
module docstring) traces directly back to exactly these fields being vague. Tier 2 fields being
defaulted is expected/acceptable (that's what "ask if relevant, otherwise default" means) and does
not by itself block readiness.
"""

from __future__ import annotations

import re

from app.agents.requirement_agent.conversation_engine import TIER_1_FIELDS
from app.schemas.requirement_conversation_schema import QualityGateResult

_ENDPOINT_PATTERN = re.compile(r"^(GET|POST|PUT|PATCH|DELETE)\s+/\S+", re.IGNORECASE)
_VAGUE_FIELD_WORD_LIMIT = 6


def assess(srs_preview: dict, defaulted_fields: list[str], feature_description: str = "") -> QualityGateResult:
    """
    Check the current srs_preview for the concrete gaps most likely to cause real downstream
    damage (see module docstring). Returns a QualityGateResult; never raises.
    """
    reasons: list[str] = []

    functional_requirements = srs_preview.get("functional_requirements") or []
    if not functional_requirements:
        reasons.append("No functional requirements captured yet.")
    elif len(functional_requirements) == 1 and feature_description.strip():
        only_fr = str(functional_requirements[0].get("description", "")).strip().lower()
        if only_fr and only_fr == feature_description.strip().lower():
            reasons.append(
                "The only functional requirement just restates the feature description -- "
                "ask for concrete, distinct actions."
            )

    api_expectations = srs_preview.get("api_expectations") or []
    for endpoint in api_expectations:
        if not _ENDPOINT_PATTERN.match(str(endpoint).strip()):
            reasons.append(
                f'API expectation "{endpoint}" doesn\'t look like a real "METHOD /path" endpoint.'
            )
            break

    data_requirements = srs_preview.get("data_requirements") or []
    for field in data_requirements:
        if len(str(field).split()) > _VAGUE_FIELD_WORD_LIMIT:
            reasons.append(
                f'Data requirement "{field}" reads like a vague sentence, not a concrete field name.'
            )
            break

    tier1_defaulted = [field for field in TIER_1_FIELDS if field in defaulted_fields]
    if tier1_defaulted:
        reasons.append(
            "These high-impact fields were assumed instead of answered: "
            + ", ".join(tier1_defaulted)
            + "."
        )

    feature_name = srs_preview.get("feature_name", "")
    project_type = srs_preview.get("project_type", "")
    boilerplate_goal = f"Deliver the {feature_name} feature for the {project_type} application."
    if str(srs_preview.get("business_goal", "")).strip() == boilerplate_goal:
        reasons.append(
            "Business goal is still a generic template -- consider clarifying why this feature matters."
        )

    return QualityGateResult(
        ready=not reasons,
        reasons=reasons,
        auto_assumed_tier1_count=len(tier1_defaulted),
    )
