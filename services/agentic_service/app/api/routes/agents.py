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
    str(error) is frequently EMPTY for transport/timeout exceptions -- e.g. httpx.ReadTimeout is
    often raised by httpx's internals with no message at all. Confirmed as the real cause of a
    reported "Architecture Agent failed: " banner with nothing after the colon (a real request
    that timed out mid-repair-call). Every generic `except Exception` handler in this file that
    builds a user-facing message uses this instead of a bare str(error), so a human always sees
    something actionable (at minimum the exception's class name) instead of a blank message.
    """
    return str(error) or f"{type(error).__name__} (no further detail was provided by the error itself)"


@router.post("/requirement/run", response_model=AgentRunResponse)
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
            detail=f"Requirement Agent failed: {_readable_error(error)}"
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
            detail=f"Requirement Agent revision failed: {_readable_error(error)}"
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
                {"type": "error", "message": f"Requirement Agent revision failed: {_readable_error(error)}"}
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
            detail=f"Requirement Agent field edit failed: {_readable_error(error)}"
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
        raise HTTPException(status_code=500, detail=f"Failed to start requirement conversation: {_readable_error(error)}")


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
        raise HTTPException(status_code=500, detail=f"Failed to continue requirement conversation: {_readable_error(error)}")


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
                {"type": "error", "message": f"Failed to continue requirement conversation: {_readable_error(error)}"}
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
        raise HTTPException(status_code=500, detail=f"Failed to process attached document: {_readable_error(error)}")


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
        raise HTTPException(status_code=500, detail=f"Failed to edit requirement conversation turn: {_readable_error(error)}")


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

    async def event_stream():
        try:
            async for event in requirement_agent.edit_turn_reply_stream(
                feature_id=feature_id, turn_index=turn_index, new_reply=request.reply
            ):
                yield json.dumps(event) + "\n"
        except ValueError as error:
            yield json.dumps({"type": "error", "message": str(error)}) + "\n"
        except Exception as error:
            yield json.dumps(
                {"type": "error", "message": f"Failed to edit requirement conversation turn: {_readable_error(error)}"}
            ) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.get("/requirement/conversation", response_model=RequirementConversationState | None)
async def get_requirement_conversation(feature_id: str):
    """
    Fetch the current conversation state (for reloading the page or polling) -- null if no
    conversation has been started yet for this feature.
    """
    _validate_feature(feature_id)
    return requirement_agent.get_conversation(feature_id=feature_id)


@router.post("/requirement/conversation/reset")
async def reset_requirement_conversation(feature_id: str):
    """
    Discard the in-progress conversation for this feature and start over.
    """
    _validate_feature(feature_id)
    requirement_agent.reset_conversation(feature_id=feature_id)
    return {"feature_id": feature_id, "status": "reset"}


@router.post("/requirement/conversation/confirm", response_model=AgentRunResponse)
async def confirm_requirement_conversation(feature_id: str, request: RequirementConversationConfirmRequest):
    """
    Finalize the conversation into a real SRS -- generates and saves a normal ArtifactType.SRS
    version through the same path /requirement/run uses, so it requires human approval before
    Domain Agent can run, exactly like any other SRS.
    """
    _validate_feature(feature_id)
    stage_event_service.record(feature_id, AgentName.REQUIREMENT, "confirm", request.override_reason, request.confirmed_by)

    try:
        return await requirement_agent.confirm_conversation(feature_id=feature_id, request=request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Failed to confirm requirement conversation: {_readable_error(error)}")


@router.post("/requirement/conversation/confirm/stream")
async def confirm_requirement_conversation_stream(feature_id: str, request: RequirementConversationConfirmRequest):
    """
    Streaming variant of confirm -- same validation/generation/save logic
    (RequirementAgent.confirm_conversation_stream), but the response body is newline-delimited
    JSON events so the frontend can show the SRS "typing" live as it's generated, instead of a
    blocking wait followed by a sudden reveal. Each line is one JSON object:
        {"type": "token", "text": "..."}
        {"type": "error", "message": "..."}
        {"type": "done", "artifact_ids": [...], "message": "..."}

    A plain StreamingResponse (not SSE) is used deliberately: EventSource only supports GET with
    no request body, but confirming needs to POST override_quality_gate/override_reason -- a
    fetch() ReadableStream reader on the frontend handles a streamed POST response body just as
    well for this one-directional, single-request use case.
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
                {"type": "error", "message": f"Failed to confirm requirement conversation: {_readable_error(error)}"}
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
            detail=f"Domain Agent failed: {_readable_error(error)}"
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
            yield json.dumps({"type": "error", "message": f"Domain Agent failed: {_readable_error(error)}"}) + "\n"

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
            detail=f"Domain Agent revision failed: {_readable_error(error)}"
        )


@router.post("/domain/revise/stream")
async def revise_domain_agent_stream(feature_id: str, request: DomainAgentReviseRequest):
    """
    Streaming variant of /domain/revise -- same newline-delimited JSON event shape as
    /domain/run/stream.
        {"type": "token", "text": "..."}
        {"type": "error", "message": "..."}
        {"type": "done", "artifact_ids": [...], "message": "..."}
    """
    _validate_feature(feature_id)
    stage_event_service.record(
        feature_id, AgentName.DOMAIN, "revise", request.revision_comment, request.revised_by
    )

    async def event_stream():
        try:
            async for event in domain_agent.revise_stream(feature_id=feature_id, request=request):
                yield json.dumps(event) + "\n"
        except ValueError as error:
            yield json.dumps({"type": "error", "message": str(error)}) + "\n"
        except Exception as error:
            yield json.dumps({"type": "error", "message": f"Domain Agent revision failed: {_readable_error(error)}"}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


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
    stage_event_service.record(feature_id, AgentName.ARCHITECTURE, "run", request.human_comment)

    try:
        return await architecture_agent.run(
            feature_id=feature_id,
            request=request
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Architecture Agent failed: {_readable_error(error)}"
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
            detail=f"Architecture Agent revision failed: {_readable_error(error)}"
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

    async def event_stream():
        try:
            async for event in architecture_agent.run_stream(feature_id=feature_id, request=request):
                yield json.dumps(event) + "\n"
        except ValueError as error:
            yield json.dumps({"type": "error", "message": str(error)}) + "\n"
        except Exception as error:
            yield json.dumps({"type": "error", "message": f"Architecture Agent failed: {_readable_error(error)}"}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.post("/architecture/revise/stream")
async def revise_architecture_agent_stream(feature_id: str, request: ArchitectureAgentReviseRequest):
    """
    Streaming variant of /architecture/revise -- same newline-delimited JSON event shape as
    /architecture/run/stream.
        {"type": "token", "text": "..."}
        {"type": "phase", "phase": "...", "label": "..."}
        {"type": "error", "message": "..."}
        {"type": "done", "artifact_ids": [...], "message": "..."}
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
                {"type": "error", "message": f"Architecture Agent revision failed: {_readable_error(error)}"}
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
            detail=f"UI/UX Agent failed: {_readable_error(error)}"
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
            detail=f"Coder Agent failed: {_readable_error(error)}"
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
            detail=f"Coder Agent revision failed: {_readable_error(error)}"
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

    async def event_stream():
        try:
            async for event in coder_agent.run_stream(feature_id=feature_id, request=request):
                yield json.dumps(event) + "\n"
        except ValueError as error:
            yield json.dumps({"type": "error", "message": str(error)}) + "\n"
        except Exception as error:
            yield json.dumps({"type": "error", "message": f"Coder Agent failed: {_readable_error(error)}"}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.post("/coder/revise/stream")
async def revise_coder_agent_stream(feature_id: str, request: CoderAgentReviseRequest):
    """
    Streaming variant of /coder/revise -- same newline-delimited JSON event shape as
    /coder/run/stream.
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
                {"type": "error", "message": f"Coder Agent revision failed: {_readable_error(error)}"}
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