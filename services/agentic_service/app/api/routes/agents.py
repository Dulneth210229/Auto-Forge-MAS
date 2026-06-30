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

from fastapi import APIRouter, HTTPException, Body

from app.core.enums import AgentName
from app.schemas.agent_schema import AgentRunRequest, AgentRunResponse
from app.services.in_memory_store import store
from app.agents.requirement_agent.agent import requirement_agent
from app.agents.architecture_agent.agent import architecture_agent
from app.core.enums import AgentName, ArtifactType, ArtifactFormat
from app.schemas.agent_schema import AgentRunRequest, AgentRunResponse
from app.services.artifact_service import artifact_service
from app.schemas.requirement_schema import (
    RequirementAgentRunRequest,
    RequirementAgentReviseRequest,
)
from app.schemas.architecture_schema import (
    ArchitectureAgentRunRequest,
    ArchitectureAgentReviseRequest,
)
from app.services.in_memory_store import store
from app.services.plantuml_service import plantuml_service
import traceback

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
async def run_requirement_agent(
    feature_id: str,
    request: RequirementAgentRunRequest
):
    """
    Run the Requirement Agent.

    This endpoint:
    - receives structured BA input
    - supports architectural_style input
    - calls the selected LLM provider
    - generates SRS Markdown and SRS JSON
    - saves both files as artifacts
    - returns artifact IDs

    Human approval is required after this.
    """
    _validate_feature(feature_id)

    try:
        return await requirement_agent.run(
            feature_id=feature_id,
            request=request
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        print("========== REQUIREMENT AGENT ERROR ==========")
        print(traceback.format_exc())
        print("============================================")

        raise HTTPException(
            status_code=500,
            detail=f"Requirement Agent failed: {str(error)}"
        )

@router.post("/requirement/revise", response_model=AgentRunResponse)
async def revise_requirement_agent(
    feature_id: str,
    request: RequirementAgentReviseRequest
):
    """
    Revise the latest Requirement Agent SRS.

    This endpoint:
    - loads the latest SRS JSON artifact
    - applies the human revision comment
    - creates a new SRS version
    - keeps previous versions unchanged
    """

    _validate_feature(feature_id)

    try:
        return await requirement_agent.revise(
            feature_id=feature_id,
            request=request
        )

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Requirement Agent revision failed: {str(error)}"
        )

@router.post("/domain/run", response_model=AgentRunResponse)
async def run_domain_agent(feature_id: str, request: AgentRunRequest):
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
async def run_architecture_agent(
    feature_id: str,
    request: ArchitectureAgentRunRequest
):
    """
    Run Architecture Agent.

    This endpoint:
    - requires approved SRS JSON
    - optionally uses approved Enhanced SRS JSON
    - generates Architecture Plan Markdown
    - generates Architecture Plan JSON
    - generates Use Case, Sequence, and Class Diagram PUML/PNG artifacts

    It does not generate a separate API contract.
    """

    _validate_feature(feature_id)

    try:
        return await architecture_agent.run(
            feature_id=feature_id,
            request=request
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Architecture Agent failed: {str(error)}"
        )
    


@router.post("/architecture/revise", response_model=AgentRunResponse)
async def revise_architecture_agent(
    feature_id: str,
    request: ArchitectureAgentReviseRequest
):
    """
    Revise the latest Architecture Agent output.

    This endpoint:
    - loads the latest Architecture Plan JSON
    - applies the human/client revision comment
    - regenerates Use Case, Sequence, and Class diagrams from the revised plan
    - creates a new Architecture Agent version
    - keeps previous versions unchanged
    """

    _validate_feature(feature_id)

    try:
        return await architecture_agent.revise(
            feature_id=feature_id,
            request=request
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Architecture Agent revision failed: {str(error)}"
        )


    # ----------------------------------------------------
    # Ui/UX  Agent
    # ----------------------------------------------------
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