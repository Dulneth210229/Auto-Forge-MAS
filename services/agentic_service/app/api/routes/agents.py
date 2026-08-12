"""
Agent routes.

This file exposes the API endpoints for running and revising
the agents used by the AutoForge software development pipeline.

Agents:
- RequirementAgent
- DomainAgent
- ArchitectureAgent
- UIUXAgent
- CoderAgent
- SecurityAgent
- QAAgent
- DeploymentAgent
"""

import json
import traceback

from fastapi import (
    APIRouter,
    HTTPException,
    File,
    Form,
    UploadFile,
)
from fastapi.responses import StreamingResponse

from app.core.enums import AgentName

from app.schemas.agent_schema import (
    AgentRunRequest,
    AgentRunResponse,
)

from app.services.in_memory_store import store
from app.services.stage_event_service import stage_event_service

# ----------------------------------------------------------------------
# Requirement Agent
# ----------------------------------------------------------------------

from app.agents.requirement_agent.agent import requirement_agent

from app.schemas.requirement_schema import (
    RequirementAgentRunRequest,
    RequirementAgentReviseRequest,
    RequirementAgentFieldEditRequest,
)

from app.schemas.requirement_conversation_schema import (
    RequirementConversationConfirmRequest,
    RequirementConversationReplyRequest,
    RequirementConversationState,
)

# ----------------------------------------------------------------------
# Domain Agent
# ----------------------------------------------------------------------

from app.agents.domain_agent.agent import domain_agent

from app.schemas.domain_schema import (
    DomainAgentRunRequest,
    DomainAgentReviseRequest,
)

# ----------------------------------------------------------------------
# Architecture Agent
# ----------------------------------------------------------------------

from app.agents.architecture_agent.agent import architecture_agent

from app.schemas.architecture_schema import (
    ArchitectureAgentRunRequest,
    ArchitectureAgentReviseRequest,
)

# ----------------------------------------------------------------------
# UI/UX Agent
# ----------------------------------------------------------------------

from app.agents.uiux_agent.agent import uiux_agent

from app.schemas.uiux_schema import UIUXAgentRunRequest

# ----------------------------------------------------------------------
# Coder Agent
# ----------------------------------------------------------------------

from app.agents.coder_agent.agent import coder_agent
from app.agents.coder_agent.schemas import CoderAgentEnvSaveResult

from app.schemas.coder_schema import (
    CoderAgentRunRequest,
    CoderAgentReviseRequest,
)

# ----------------------------------------------------------------------
# Security Agent
# ----------------------------------------------------------------------

from app.agents.security_agent.agent import security_agent
from app.schemas.security_schema import SecurityAgentRunRequest

# ----------------------------------------------------------------------
# QA Agent
# ----------------------------------------------------------------------

from app.agents.qa_agent.agent import qa_agent
from app.schemas.qa_schema import QAAgentRunRequest


# ----------------------------------------------------------------------
# Router
# ----------------------------------------------------------------------

router = APIRouter(
    prefix="/features/{feature_id}/agents",
    tags=["Agents"],
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _validate_feature(feature_id: str):
    """
    Check whether the requested feature exists.
    """

    feature = store.features.get(feature_id)

    if not feature:
        raise HTTPException(
            status_code=404,
            detail="Feature not found",
        )

    return feature


def _readable_error(error: Exception) -> str:
    """
    Return a useful error message even when an exception's
    string representation is empty.
    """

    return (
        str(error)
        or f"{type(error).__name__} "
           "(no further detail was provided by the error itself)"
    )


# ======================================================================
# REQUIREMENT AGENT
# ======================================================================

@router.post(
    "/requirement/run",
    response_model=AgentRunResponse,
)
async def run_requirement_agent(
    feature_id: str,
    request: RequirementAgentRunRequest,
):
    """
    Run the Requirement Agent.

    Generates:
    - SRS Markdown
    - SRS JSON

    Human approval is required after generation.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.REQUIREMENT,
        "run",
        request.human_comment,
    )

    try:
        return await requirement_agent.run(
            feature_id=feature_id,
            request=request,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        print("========== REQUIREMENT AGENT ERROR ==========")
        print(traceback.format_exc())
        print("==============================================")

        raise HTTPException(
            status_code=500,
            detail=(
                f"Requirement Agent failed: "
                f"{_readable_error(error)}"
            ),
        )


@router.post(
    "/requirement/revise",
    response_model=AgentRunResponse,
)
async def revise_requirement_agent(
    feature_id: str,
    request: RequirementAgentReviseRequest,
):
    """
    Revise the latest Requirement Agent output.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.REQUIREMENT,
        "revise",
        request.revision_comment,
        request.revised_by,
    )

    try:
        return await requirement_agent.revise(
            feature_id=feature_id,
            request=request,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Requirement Agent revision failed: "
                f"{_readable_error(error)}"
            ),
        )


@router.post("/requirement/revise/stream")
async def revise_requirement_agent_stream(
    feature_id: str,
    request: RequirementAgentReviseRequest,
):
    """
    Streaming Requirement Agent revision endpoint.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.REQUIREMENT,
        "revise",
        request.revision_comment,
        request.revised_by,
    )

    async def event_stream():
        try:
            async for event in requirement_agent.revise_stream(
                feature_id=feature_id,
                revision_comment=request.revision_comment,
                revised_by=request.revised_by,
            ):
                yield json.dumps(event) + "\n"

        except ValueError as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                }
            ) + "\n"

        except Exception as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": (
                        "Requirement Agent revision failed: "
                        f"{_readable_error(error)}"
                    ),
                }
            ) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
    )


@router.post(
    "/requirement/edit",
    response_model=AgentRunResponse,
)
async def edit_requirement_agent_fields(
    feature_id: str,
    request: RequirementAgentFieldEditRequest,
):
    """
    Apply deterministic field-level edits to the latest SRS.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.REQUIREMENT,
        "edit",
        f"Manual field edit "
        f"({len(request.operations)} operation(s))",
        request.edited_by,
    )

    try:
        return await requirement_agent.edit_fields(
            feature_id=feature_id,
            operations=[
                op.model_dump(exclude_none=True)
                for op in request.operations
            ],
            edited_by=request.edited_by,
            base_artifact_id=request.base_artifact_id,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Requirement Agent field edit failed: "
                f"{_readable_error(error)}"
            ),
        )


# ======================================================================
# REQUIREMENT CONVERSATION
# ======================================================================

@router.post(
    "/requirement/conversation/start",
    response_model=RequirementConversationState,
)
async def start_requirement_conversation(
    feature_id: str,
):
    """
    Start or resume the requirement clarification conversation.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.REQUIREMENT,
        "clarify_start",
        None,
    )

    try:
        return await requirement_agent.start_conversation(
            feature_id=feature_id,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to start requirement conversation: "
                f"{_readable_error(error)}"
            ),
        )


@router.post(
    "/requirement/conversation/reply",
    response_model=RequirementConversationState,
)
async def reply_to_requirement_conversation(
    feature_id: str,
    request: RequirementConversationReplyRequest,
):
    """
    Submit an answer to the current requirement clarification questions.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.REQUIREMENT,
        "clarify",
        request.reply,
    )

    try:
        return await requirement_agent.reply_to_conversation(
            feature_id=feature_id,
            request=request,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to continue requirement conversation: "
                f"{_readable_error(error)}"
            ),
        )


@router.post(
    "/requirement/conversation/reply/stream"
)
async def reply_to_requirement_conversation_stream(
    feature_id: str,
    request: RequirementConversationReplyRequest,
):
    """
    Streaming requirement clarification endpoint.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.REQUIREMENT,
        "clarify",
        request.reply,
    )

    async def event_stream():
        try:
            async for event in requirement_agent.reply_to_conversation_stream(
                feature_id=feature_id,
                reply_text=request.reply,
            ):
                yield json.dumps(event) + "\n"

        except ValueError as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                }
            ) + "\n"

        except Exception as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": (
                        "Failed to continue requirement conversation: "
                        f"{_readable_error(error)}"
                    ),
                }
            ) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
    )


@router.post(
    "/requirement/conversation/reply/upload",
    response_model=RequirementConversationState,
)
async def reply_to_requirement_conversation_with_document(
    feature_id: str,
    file: UploadFile = File(...),
    reply: str | None = Form(None),
):
    """
    Submit requirement clarification together with
    an uploaded document.
    """

    _validate_feature(feature_id)

    file_bytes = await file.read()

    stage_event_service.record(
        feature_id,
        AgentName.REQUIREMENT,
        "clarify",
        f"{reply or ''}\n\n"
        f"[Attached file: {file.filename}]".strip(),
    )

    try:
        return await requirement_agent.reply_to_conversation_with_document(
            feature_id=feature_id,
            file_bytes=file_bytes,
            filename=file.filename,
            reply_text=reply,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to process attached document: "
                f"{_readable_error(error)}"
            ),
        )


@router.post(
    "/requirement/conversation/turns/{turn_index}/edit",
    response_model=RequirementConversationState,
)
async def edit_requirement_conversation_turn(
    feature_id: str,
    turn_index: int,
    request: RequirementConversationReplyRequest,
):
    """
    Edit a previously submitted requirement conversation reply.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.REQUIREMENT,
        "clarify",
        request.reply,
    )

    try:
        return await requirement_agent.edit_turn_reply(
            feature_id=feature_id,
            turn_index=turn_index,
            new_reply=request.reply,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to edit requirement conversation turn: "
                f"{_readable_error(error)}"
            ),
        )


@router.post(
    "/requirement/conversation/turns/{turn_index}/edit/stream"
)
async def edit_requirement_conversation_turn_stream(
    feature_id: str,
    turn_index: int,
    request: RequirementConversationReplyRequest,
):
    """
    Streaming version of requirement conversation edit.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.REQUIREMENT,
        "clarify",
        request.reply,
    )

    async def event_stream():
        try:
            async for event in requirement_agent.edit_turn_reply_stream(
                feature_id=feature_id,
                turn_index=turn_index,
                new_reply=request.reply,
            ):
                yield json.dumps(event) + "\n"

        except ValueError as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                }
            ) + "\n"

        except Exception as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": (
                        "Failed to edit requirement conversation turn: "
                        f"{_readable_error(error)}"
                    ),
                }
            ) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
    )


@router.get(
    "/requirement/conversation",
    response_model=RequirementConversationState | None,
)
async def get_requirement_conversation(
    feature_id: str,
):
    """
    Retrieve the current requirement conversation state.
    """

    _validate_feature(feature_id)

    return requirement_agent.get_conversation(
        feature_id=feature_id,
    )


@router.post("/requirement/conversation/reset")
async def reset_requirement_conversation(
    feature_id: str,
):
    """
    Reset the current requirement clarification conversation.
    """

    _validate_feature(feature_id)

    requirement_agent.reset_conversation(
        feature_id=feature_id,
    )

    return {
        "feature_id": feature_id,
        "status": "reset",
    }


@router.post(
    "/requirement/conversation/confirm",
    response_model=AgentRunResponse,
)
async def confirm_requirement_conversation(
    feature_id: str,
    request: RequirementConversationConfirmRequest,
):
    """
    Finalize a requirement conversation into an SRS artifact.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.REQUIREMENT,
        "confirm",
        request.override_reason,
        request.confirmed_by,
    )

    try:
        return await requirement_agent.confirm_conversation(
            feature_id=feature_id,
            request=request,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to confirm requirement conversation: "
                f"{_readable_error(error)}"
            ),
        )


@router.post(
    "/requirement/conversation/confirm/stream"
)
async def confirm_requirement_conversation_stream(
    feature_id: str,
    request: RequirementConversationConfirmRequest,
):
    """
    Streaming requirement confirmation endpoint.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.REQUIREMENT,
        "confirm",
        request.override_reason,
        request.confirmed_by,
    )

    async def event_stream():
        try:
            async for event in requirement_agent.confirm_conversation_stream(
                feature_id=feature_id,
                request=request,
            ):
                yield json.dumps(event) + "\n"

        except ValueError as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                }
            ) + "\n"

        except Exception as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": (
                        "Failed to confirm requirement conversation: "
                        f"{_readable_error(error)}"
                    ),
                }
            ) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
    )


# ======================================================================
# DOMAIN AGENT
# ======================================================================

@router.post(
    "/domain/run",
    response_model=AgentRunResponse,
)
async def run_domain_agent(
    feature_id: str,
    request: DomainAgentRunRequest,
):
    """
    Run the Domain Agent.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.DOMAIN,
        "run",
        request.human_comment,
    )

    try:
        return await domain_agent.run(
            feature_id=feature_id,
            request=request,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        print("========== DOMAIN AGENT ERROR ==========")
        print(traceback.format_exc())
        print("=========================================")

        raise HTTPException(
            status_code=500,
            detail=f"Domain Agent failed: {_readable_error(error)}",
        )


@router.post("/domain/run/stream")
async def run_domain_agent_stream(
    feature_id: str,
    request: DomainAgentRunRequest,
):
    """
    Streaming Domain Agent endpoint.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.DOMAIN,
        "run",
        request.human_comment,
    )

    async def event_stream():
        try:
            async for event in domain_agent.run_stream(
                feature_id=feature_id,
                request=request,
            ):
                yield json.dumps(event) + "\n"

        except ValueError as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                }
            ) + "\n"

        except Exception as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": (
                        f"Domain Agent failed: "
                        f"{_readable_error(error)}"
                    ),
                }
            ) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
    )


@router.post(
    "/domain/revise",
    response_model=AgentRunResponse,
)
async def revise_domain_agent(
    feature_id: str,
    request: DomainAgentReviseRequest,
):
    """
    Revise the latest Domain Agent output.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.DOMAIN,
        "revise",
        request.revision_comment,
        request.revised_by,
    )

    try:
        return await domain_agent.revise(
            feature_id=feature_id,
            request=request,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Domain Agent revision failed: "
                f"{_readable_error(error)}"
            ),
        )


@router.post("/domain/revise/stream")
async def revise_domain_agent_stream(
    feature_id: str,
    request: DomainAgentReviseRequest,
):
    """
    Streaming Domain Agent revision endpoint.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.DOMAIN,
        "revise",
        request.revision_comment,
        request.revised_by,
    )

    async def event_stream():
        try:
            async for event in domain_agent.revise_stream(
                feature_id=feature_id,
                request=request,
            ):
                yield json.dumps(event) + "\n"

        except ValueError as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                }
            ) + "\n"

        except Exception as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": (
                        f"Domain Agent revision failed: "
                        f"{_readable_error(error)}"
                    ),
                }
            ) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
    )


# ======================================================================
# ARCHITECTURE AGENT
# ======================================================================

@router.post(
    "/architecture/run",
    response_model=AgentRunResponse,
)
async def run_architecture_agent(
    feature_id: str,
    request: ArchitectureAgentRunRequest,
):
    """
    Run Architecture Agent.

    Generates:
    - Architecture Plan Markdown
    - Architecture Plan JSON
    - Use Case diagrams
    - Sequence diagrams
    - Class diagrams
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.ARCHITECTURE,
        "run",
        request.human_comment,
    )

    try:
        return await architecture_agent.run(
            feature_id=feature_id,
            request=request,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Architecture Agent failed: "
                f"{_readable_error(error)}"
            ),
        )


@router.post(
    "/architecture/revise",
    response_model=AgentRunResponse,
)
async def revise_architecture_agent(
    feature_id: str,
    request: ArchitectureAgentReviseRequest,
):
    """
    Revise the latest Architecture Agent output.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.ARCHITECTURE,
        "revise",
        request.revision_comment,
        request.revised_by,
    )

    try:
        return await architecture_agent.revise(
            feature_id=feature_id,
            request=request,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Architecture Agent revision failed: "
                f"{_readable_error(error)}"
            ),
        )


@router.post("/architecture/run/stream")
async def run_architecture_agent_stream(
    feature_id: str,
    request: ArchitectureAgentRunRequest,
):
    """
    Streaming Architecture Agent endpoint.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.ARCHITECTURE,
        "run",
        request.human_comment,
    )

    async def event_stream():
        try:
            async for event in architecture_agent.run_stream(
                feature_id=feature_id,
                request=request,
            ):
                yield json.dumps(event) + "\n"

        except ValueError as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                }
            ) + "\n"

        except Exception as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": (
                        f"Architecture Agent failed: "
                        f"{_readable_error(error)}"
                    ),
                }
            ) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
    )


@router.post("/architecture/revise/stream")
async def revise_architecture_agent_stream(
    feature_id: str,
    request: ArchitectureAgentReviseRequest,
):
    """
    Streaming Architecture Agent revision endpoint.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.ARCHITECTURE,
        "revise",
        request.revision_comment,
        request.revised_by,
    )

    async def event_stream():
        try:
            async for event in architecture_agent.revise_stream(
                feature_id=feature_id,
                request=request,
            ):
                yield json.dumps(event) + "\n"

        except ValueError as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                }
            ) + "\n"

        except Exception as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": (
                        f"Architecture Agent revision failed: "
                        f"{_readable_error(error)}"
                    ),
                }
            ) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
    )


# ======================================================================
# UI/UX AGENT
# ======================================================================

@router.post(
    "/uiux/run",
    response_model=AgentRunResponse,
)
async def run_uiux_agent(
    feature_id: str,
    request: UIUXAgentRunRequest,
):
    """
    Run the UI/UX Agent.

    Generates:
    - UI metadata
    - component code
    - page previews/screenshots
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.UIUX,
        "run",
        request.human_comment,
    )

    try:
        output = await uiux_agent.run(
            feature_id=feature_id,
            request=request,
        )

        return AgentRunResponse(
            feature_id=feature_id,
            agent_name=AgentName.UIUX,
            status="completed",
            message=(
                "UI/UX Agent completed. "
                "Metadata and components require human approval."
            ),
            artifact_ids=output.artifact_ids,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        print("========== UI/UX AGENT ERROR ==========")
        print(traceback.format_exc())
        print("========================================")

        raise HTTPException(
            status_code=500,
            detail=(
                f"UI/UX Agent failed: "
                f"{_readable_error(error)}"
            ),
        )


# ======================================================================
# CODER AGENT
# ======================================================================

@router.post(
    "/coder/run",
    response_model=AgentRunResponse,
)
async def run_coder_agent(
    feature_id: str,
    request: CoderAgentRunRequest,
):
    """
    Run the Coder Agent.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.CODER,
        "run",
        request.human_comment,
    )

    try:
        output = await coder_agent.run(
            feature_id=feature_id,
            request=request,
        )

        return AgentRunResponse(
            feature_id=feature_id,
            agent_name=AgentName.CODER,
            status=(
                "completed"
                if output.verification_passed
                else "completed_with_verification_failures"
            ),
            message=(
                "Coder Agent completed and verification passed. "
                "Requires human approval."
                if output.verification_passed
                else
                "Coder Agent completed but verification failed. "
                "Requires human review before approval."
            ),
            artifact_ids=output.artifact_ids,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        print("========== CODER AGENT ERROR ==========")
        print(traceback.format_exc())
        print("========================================")

        raise HTTPException(
            status_code=500,
            detail=(
                f"Coder Agent failed: "
                f"{_readable_error(error)}"
            ),
        )


@router.post(
    "/coder/revise",
    response_model=AgentRunResponse,
)
async def revise_coder_agent(
    feature_id: str,
    request: CoderAgentReviseRequest,
):
    """
    Revise the latest Coder Agent output.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.CODER,
        "revise",
        request.revision_comment,
        request.revised_by,
    )

    try:
        output = await coder_agent.revise(
            feature_id=feature_id,
            request=request,
        )

        if isinstance(output, CoderAgentEnvSaveResult):
            return AgentRunResponse(
                feature_id=feature_id,
                agent_name=AgentName.CODER,
                status="database_connection_saved",
                message=output.message,
                artifact_ids=[],
            )

        return AgentRunResponse(
            feature_id=feature_id,
            agent_name=AgentName.CODER,
            status=(
                "revised"
                if output.verification_passed
                else "revised_with_verification_failures"
            ),
            message=(
                "Coder Agent revision completed and verification passed. "
                "A new version was created and requires human approval."
                if output.verification_passed
                else
                "Coder Agent revision completed but verification failed. "
                "A new version was created and requires human review."
            ),
            artifact_ids=output.artifact_ids,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Coder Agent revision failed: "
                f"{_readable_error(error)}"
            ),
        )


@router.post("/coder/run/stream")
async def run_coder_agent_stream(
    feature_id: str,
    request: CoderAgentRunRequest,
):
    """
    Streaming Coder Agent endpoint.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.CODER,
        "run",
        request.human_comment,
    )

    async def event_stream():
        try:
            async for event in coder_agent.run_stream(
                feature_id=feature_id,
                request=request,
            ):
                yield json.dumps(event) + "\n"

        except ValueError as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                }
            ) + "\n"

        except Exception as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": (
                        f"Coder Agent failed: "
                        f"{_readable_error(error)}"
                    ),
                }
            ) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
    )


@router.post("/coder/revise/stream")
async def revise_coder_agent_stream(
    feature_id: str,
    request: CoderAgentReviseRequest,
):
    """
    Streaming Coder Agent revision endpoint.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.CODER,
        "revise",
        request.revision_comment,
        request.revised_by,
    )

    async def event_stream():
        try:
            async for event in coder_agent.revise_stream(
                feature_id=feature_id,
                request=request,
            ):
                yield json.dumps(event) + "\n"

        except ValueError as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                }
            ) + "\n"

        except Exception as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": (
                        f"Coder Agent revision failed: "
                        f"{_readable_error(error)}"
                    ),
                }
            ) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
    )


# ======================================================================
# SECURITY AGENT
# ======================================================================

@router.post(
    "/security/run",
    response_model=AgentRunResponse,
)
async def run_security_agent(
    feature_id: str,
    request: SecurityAgentRunRequest,
):
    """
    Run the Security Agent.

    The Security Agent:

    1. Loads the project workspace.
    2. Performs deterministic security analysis.
    3. Runs AST-based security scanning.
    4. Detects hard-coded secrets.
    5. Scans project dependencies for vulnerabilities.
    6. Optionally performs LLM-assisted secure-code review.
    7. Evaluates the collected findings through the Security Gate.
    8. Generates security report artifacts.
    9. Returns the generated artifact IDs.

    Security output is intended for review before finalization.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.SECURITY,
        "run",
        request.human_comment,
    )

    try:
        output = await security_agent.run(
            feature_id=feature_id,
            request=request,
        )

        return output

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        print("========== SECURITY AGENT ERROR ==========")
        print(traceback.format_exc())
        print("===========================================")

        raise HTTPException(
            status_code=500,
            detail=(
                f"Security Agent failed: "
                f"{_readable_error(error)}"
            ),
        )


@router.post("/security/run/stream")
async def run_security_agent_stream(
    feature_id: str,
    request: SecurityAgentRunRequest,
):
    """
    Streaming Security Agent endpoint.

    The Security Agent itself performs analysis and artifact generation.
    If the Security Agent implementation exposes run_stream(), events are
    forwarded to the frontend using newline-delimited JSON.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.SECURITY,
        "run",
        request.human_comment,
    )

    async def event_stream():
        try:
            # Use streaming implementation when available.
            async for event in security_agent.run_stream(
                feature_id=feature_id,
                request=request,
            ):
                yield json.dumps(event) + "\n"

        except AttributeError:
            # Fallback for the current non-streaming SecurityAgent.
            try:
                output = await security_agent.run(
                    feature_id=feature_id,
                    request=request,
                )

                yield json.dumps(
                    {
                        "type": "done",
                        "artifact_ids": output.artifact_ids,
                        "message": output.message,
                        "status": output.status,
                    }
                ) + "\n"

            except ValueError as error:
                yield json.dumps(
                    {
                        "type": "error",
                        "message": str(error),
                    }
                ) + "\n"

            except Exception as error:
                yield json.dumps(
                    {
                        "type": "error",
                        "message": (
                            f"Security Agent failed: "
                            f"{_readable_error(error)}"
                        ),
                    }
                ) + "\n"

        except ValueError as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                }
            ) + "\n"

        except Exception as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": (
                        f"Security Agent failed: "
                        f"{_readable_error(error)}"
                    ),
                }
            ) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
    )


# ======================================================================
# QA AGENT
# ======================================================================

@router.post(
    "/qa/run",
    response_model=AgentRunResponse,
)
async def run_qa_agent(
    feature_id: str,
    request: QAAgentRunRequest,
):
    """
    Run the QA Agent.

    The QA Agent:

    1. Loads the generated project workspace.
    2. Scans supported source files.
    3. Generates automated test cases using the LLM.
    4. Creates test files in the generated_tests directory.
    5. Validates generated tests where applicable.
    6. Detects the supported test framework.
    7. Executes generated tests.
    8. Collects execution results.
    9. Evaluates the QA results.
    10. Generates QA artifacts and evaluation reports.
    11. Returns the generated artifact IDs.

    Generated tests are kept as artifacts for inspection and later
    execution/finalization steps.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.QA,
        "run",
        request.human_comment,
    )

    try:
        output = await qa_agent.run(
            feature_id=feature_id,
            request=request,
        )

        return output

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        print("========== QA AGENT ERROR ==========")
        print(traceback.format_exc())
        print("=====================================")

        raise HTTPException(
            status_code=500,
            detail=(
                f"QA Agent failed: "
                f"{_readable_error(error)}"
            ),
        )


@router.post("/qa/run/stream")
async def run_qa_agent_stream(
    feature_id: str,
    request: QAAgentRunRequest,
):
    """
    Streaming QA Agent endpoint.

    If the QA Agent exposes run_stream(), events are forwarded directly.
    Otherwise, the normal QA Agent execution is used and a final `done`
    event is returned.
    """

    _validate_feature(feature_id)

    stage_event_service.record(
        feature_id,
        AgentName.QA,
        "run",
        request.human_comment,
    )

    async def event_stream():
        try:
            # Use streaming implementation when available.
            async for event in qa_agent.run_stream(
                feature_id=feature_id,
                request=request,
            ):
                yield json.dumps(event) + "\n"

        except AttributeError:
            # Fallback to the normal QA execution path.
            try:
                output = await qa_agent.run(
                    feature_id=feature_id,
                    request=request,
                )

                yield json.dumps(
                    {
                        "type": "done",
                        "artifact_ids": output.artifact_ids,
                        "message": output.message,
                        "status": output.status,
                    }
                ) + "\n"

            except ValueError as error:
                yield json.dumps(
                    {
                        "type": "error",
                        "message": str(error),
                    }
                ) + "\n"

            except Exception as error:
                yield json.dumps(
                    {
                        "type": "error",
                        "message": (
                            f"QA Agent failed: "
                            f"{_readable_error(error)}"
                        ),
                    }
                ) + "\n"

        except ValueError as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": str(error),
                }
            ) + "\n"

        except Exception as error:
            yield json.dumps(
                {
                    "type": "error",
                    "message": (
                        f"QA Agent failed: "
                        f"{_readable_error(error)}"
                    ),
                }
            ) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
    )


# ======================================================================
# DEPLOYMENT AGENT
# ======================================================================

@router.post(
    "/deployment/run",
    response_model=AgentRunResponse,
)
def run_deployment_agent(
    feature_id: str,
    request: AgentRunRequest,
):
    """
    Placeholder endpoint for Deployment Agent.
    """

    _validate_feature(feature_id)

    return AgentRunResponse(
        feature_id=feature_id,
        agent_name=AgentName.DEPLOYMENT,
        status="not_implemented_yet",
        message=(
            "Deployment Agent endpoint is ready. "
            "Real logic will be added later."
        ),
        artifact_ids=[],
    )