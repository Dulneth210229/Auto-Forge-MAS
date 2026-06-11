"""
Agent routes.

For now, this file contains placeholder endpoints.

Later, each endpoint will call the real agent class:
- RequirementAgent
- DomainAgent
- ArchitectureAgent
- UIUXAgent
- CoderAgent
- DeploymentAgent

At this foundation step, we only verify the API structure.
"""

from fastapi import APIRouter, HTTPException

from app.core.enums import AgentName
from app.schemas.agent_schema import AgentRunRequest, AgentRunResponse
from app.services.in_memory_store import store

router = APIRouter(prefix="/features/{feature_id}/agents", tags=["Agents"])


def _validate_feature(feature_id: str):
    """
    Helper function to check whether a feature exists.
    """
    feature = store.features.get(feature_id)

    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    return feature


@router.post("/requirement/run", response_model=AgentRunResponse)
def run_requirement_agent(feature_id: str, request: AgentRunRequest):
    """
    Placeholder endpoint for Requirement Agent.

    Real SRS generation will be added in the next step.
    """
    _validate_feature(feature_id)

    return AgentRunResponse(
        feature_id=feature_id,
        agent_name=AgentName.REQUIREMENT,
        status="not_implemented_yet",
        message="Requirement Agent endpoint is ready. Real logic will be added next.",
        artifact_ids=[]
    )


@router.post("/domain/run", response_model=AgentRunResponse)
def run_domain_agent(feature_id: str, request: AgentRunRequest):
    """
    Placeholder endpoint for Domain Agent.
    """
    _validate_feature(feature_id)

    return AgentRunResponse(
        feature_id=feature_id,
        agent_name=AgentName.DOMAIN,
        status="not_implemented_yet",
        message="Domain Agent endpoint is ready. Real logic will be added later.",
        artifact_ids=[]
    )


@router.post("/architecture/run", response_model=AgentRunResponse)
def run_architecture_agent(feature_id: str, request: AgentRunRequest):
    """
    Placeholder endpoint for Architecture Agent.
    """
    _validate_feature(feature_id)

    return AgentRunResponse(
        feature_id=feature_id,
        agent_name=AgentName.ARCHITECTURE,
        status="not_implemented_yet",
        message="Architecture Agent endpoint is ready. Real logic will be added later.",
        artifact_ids=[]
    )


@router.post("/uiux/run", response_model=AgentRunResponse)
def run_uiux_agent(feature_id: str, request: AgentRunRequest):
    """
    Placeholder endpoint for UI/UX Agent.
    """
    _validate_feature(feature_id)

    return AgentRunResponse(
        feature_id=feature_id,
        agent_name=AgentName.UIUX,
        status="not_implemented_yet",
        message="UI/UX Agent endpoint is ready. Real logic will be added later.",
        artifact_ids=[]
    )


@router.post("/coder/run", response_model=AgentRunResponse)
def run_coder_agent(feature_id: str, request: AgentRunRequest):
    """
    Placeholder endpoint for Coder Agent.
    """
    _validate_feature(feature_id)

    return AgentRunResponse(
        feature_id=feature_id,
        agent_name=AgentName.CODER,
        status="not_implemented_yet",
        message="Coder Agent endpoint is ready. Real logic will be added later.",
        artifact_ids=[]
    )


@router.post("/deployment/run", response_model=AgentRunResponse)
def run_deployment_agent(feature_id: str, request: AgentRunRequest):
    """
    Placeholder endpoint for Deployment Agent.
    """
    _validate_feature(feature_id)

    return AgentRunResponse(
        feature_id=feature_id,
        agent_name=AgentName.DEPLOYMENT,
        status="not_implemented_yet",
        message="Deployment Agent endpoint is ready. Real logic will be added later.",
        artifact_ids=[]
    )