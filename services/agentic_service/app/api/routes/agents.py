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
from app.agents.domain_agent.agent import domain_agent
from app.agents.architecture_agent.agent import architecture_agent
from app.agents.coder_agent.agent import coder_agent
from app.core.enums import AgentName, ArtifactType, ArtifactFormat
from app.schemas.agent_schema import AgentRunRequest, AgentRunResponse
from app.services.artifact_service import artifact_service
from app.schemas.requirement_schema import (
    RequirementAgentRunRequest,
    RequirementAgentReviseRequest,
)
from app.schemas.domain_schema import (
    DomainAgentRunRequest,
    DomainAgentReviseRequest,
)
from app.schemas.architecture_schema import (
    ArchitectureAgentRunRequest,
    ArchitectureAgentReviseRequest,
)
from app.schemas.coder_schema import CoderAgentReviseRequest
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
async def run_domain_agent(
    feature_id: str,
    request: DomainAgentRunRequest
):
    """
    Run the Domain Agent.

    This endpoint:
    - requires an approved SRS JSON artifact
    - retrieves relevant domain knowledge (RAG) from the vector store
    - generates Enhanced SRS Markdown, Enhanced SRS JSON, and Domain Improvements JSON

    Human approval is required after this before Architecture Agent can use the Enhanced SRS.
    """
    _validate_feature(feature_id)

    try:
        return await domain_agent.run(
            feature_id=feature_id,
            request=request
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        print("========== DOMAIN AGENT ERROR ==========")
        print(traceback.format_exc())
        print("=========================================")

        raise HTTPException(
            status_code=500,
            detail=f"Domain Agent failed: {str(error)}"
        )


@router.post("/domain/revise", response_model=AgentRunResponse)
async def revise_domain_agent(
    feature_id: str,
    request: DomainAgentReviseRequest
):
    """
    Revise the latest Domain Agent Enhanced SRS.

    This endpoint:
    - loads the latest Enhanced SRS JSON artifact
    - applies the human revision comment
    - creates a new Enhanced SRS version
    - keeps previous versions unchanged
    """

    _validate_feature(feature_id)

    try:
        return await domain_agent.revise(
            feature_id=feature_id,
            request=request
        )

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        print("========== DOMAIN AGENT REVISION ERROR ==========")
        print(traceback.format_exc())
        print("===================================================")

        raise HTTPException(
            status_code=500,
            detail=f"Domain Agent revision failed: {str(error)}"
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

    The real invocation path for an initial Coder Agent run is the
    LangGraph coder_node (see graph_orchestrator_service.py) -- this HTTP
    endpoint stays a placeholder since the graph already exercises the real
    CoderAgent.run(). /coder/revise below is real, for iterating on an
    existing run by human prompt.
    """
    _validate_feature(feature_id)

    return AgentRunResponse(
        feature_id=feature_id,
        agent_name=AgentName.CODER,
        status="not_implemented_yet",
        message="Coder Agent endpoint is ready. Real logic will be added later.",
        artifact_ids=[]
    )


@router.post("/coder/revise", response_model=AgentRunResponse)
async def revise_coder_agent(feature_id: str, request: CoderAgentReviseRequest):
    """
    Revise the latest Coder Agent output for this feature.

    This endpoint:
    - requires a prior Coder Agent run (a CODE_PLAN artifact and feature
      branch must already exist for this feature)
    - re-plans with the existing plan plus the human's revision comment
    - resumes the EXISTING feature branch (never resets it) so the
      revision builds on already-verified work instead of starting over
    - re-codes, re-verifies, and saves a new version of all Coder Agent
      artifacts -- the previous version stays intact and inspectable

    Human approval is required again after this, same as after a normal run.
    """
    _validate_feature(feature_id)

    try:
        output = await coder_agent.revise(feature_id=feature_id, request=request)

        return AgentRunResponse(
            feature_id=feature_id,
            agent_name=AgentName.CODER,
            status="revised" if output.verification_passed else "revised_with_verification_failures",
            message=(
                "Coder Agent revision completed and verification passed. "
                "A new version was created and requires human approval."
                if output.verification_passed
                else "Coder Agent revision completed but verification failed. "
                "A new version was created and requires human review before approval."
            ),
            artifact_ids=output.artifact_ids,
        )

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        print("========== CODER AGENT REVISION ERROR ==========")
        print(traceback.format_exc())
        print("==================================================")

        raise HTTPException(
            status_code=500,
            detail=f"Coder Agent revision failed: {str(error)}"
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