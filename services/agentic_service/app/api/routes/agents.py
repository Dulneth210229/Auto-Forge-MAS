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

import json

from fastapi import APIRouter, HTTPException, Body, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.core.enums import AgentName
from app.schemas.agent_schema import AgentRunRequest, AgentRunResponse
from app.services.in_memory_store import store
from app.agents.requirement_agent.agent import requirement_agent
from app.agents.domain_agent.agent import domain_agent
from app.agents.architecture_agent.agent import architecture_agent
from app.agents.uiux_agent.agent import uiux_agent
from app.agents.coder_agent.agent import coder_agent
from app.core.enums import AgentName, ArtifactType, ArtifactFormat
from app.schemas.agent_schema import AgentRunRequest, AgentRunResponse
from app.services.artifact_service import artifact_service
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
from app.services.stage_event_service import stage_event_service
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
    stage_event_service.record(feature_id, AgentName.REQUIREMENT, "run", request.human_comment)

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
    stage_event_service.record(
        feature_id, AgentName.REQUIREMENT, "revise", request.revision_comment, request.revised_by
    )

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


@router.post("/requirement/revise/stream")
async def revise_requirement_agent_stream(feature_id: str, request: RequirementAgentReviseRequest):
    """
    Streaming variant of /requirement/revise -- same newline-delimited JSON event shape as
    /requirement/conversation/confirm/stream and /requirement/conversation/reply/stream, so the
    frontend can show the agent's revision_summary reaction + the regenerated SRS "typing" live
    as they're generated instead of a blocking wait followed by a sudden reveal:
        {"type": "token", "text": "..."}
        {"type": "error", "message": "..."}
        {"type": "done", "artifact_ids": [...], "message": "..."}
    """
    _validate_feature(feature_id)
    stage_event_service.record(
        feature_id, AgentName.REQUIREMENT, "revise", request.revision_comment, request.revised_by
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
            yield json.dumps({"type": "error", "message": str(error)}) + "\n"
        except Exception as error:
            yield json.dumps(
                {"type": "error", "message": f"Requirement Agent revision failed: {str(error)}"}
            ) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.post("/requirement/edit", response_model=AgentRunResponse)
async def edit_requirement_agent_fields(feature_id: str, request: RequirementAgentFieldEditRequest):
    """
    Apply direct field-by-field edits to the latest SRS -- no LLM call, deterministic
    apply_revision_operations only. Backend counterpart to the field-by-field inline-edit UI
    (business_goal/a single functional requirement/etc.), as opposed to /requirement/revise's
    plain-English, LLM-mediated flow.
    """

    _validate_feature(feature_id)
    stage_event_service.record(
        feature_id,
        AgentName.REQUIREMENT,
        "edit",
        f"Manual field edit ({len(request.operations)} operation(s))",
        request.edited_by,
    )

    try:
        return await requirement_agent.edit_fields(
            feature_id=feature_id,
            operations=[op.model_dump(exclude_none=True) for op in request.operations],
            edited_by=request.edited_by,
            base_artifact_id=request.base_artifact_id,
        )

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Requirement Agent field edit failed: {str(error)}"
        )


# ----------------------------------------------------------------------
# Requirement Agent conversational gap-filling loop -- fully additive, alongside (not replacing)
# /requirement/run and /requirement/revise above. See RequirementAgent.start_conversation/
# reply_to_conversation/get_conversation/reset_conversation/confirm_conversation for the actual
# logic; these routes only validate the feature exists and record the stage_event "ask" half of
# the activity timeline, matching the existing route pattern.
# ----------------------------------------------------------------------

@router.post("/requirement/conversation/start", response_model=RequirementConversationState)
async def start_requirement_conversation(feature_id: str):
    """
    Begin (or resume) a requirement-gathering conversation for this feature, seeded from its
    rough feature_description.
    """
    _validate_feature(feature_id)
    stage_event_service.record(feature_id, AgentName.REQUIREMENT, "clarify_start", None)

    try:
        return await requirement_agent.start_conversation(feature_id=feature_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Failed to start requirement conversation: {str(error)}")


@router.post("/requirement/conversation/reply", response_model=RequirementConversationState)
async def reply_to_requirement_conversation(feature_id: str, request: RequirementConversationReplyRequest):
    """
    Answer the current batch of clarifying questions (or add free-form additional information).
    """
    _validate_feature(feature_id)
    stage_event_service.record(feature_id, AgentName.REQUIREMENT, "clarify", request.reply)

    try:
        return await requirement_agent.reply_to_conversation(feature_id=feature_id, request=request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Failed to continue requirement conversation: {str(error)}")


@router.post("/requirement/conversation/reply/stream")
async def reply_to_requirement_conversation_stream(feature_id: str, request: RequirementConversationReplyRequest):
    """
    Streaming variant of /requirement/conversation/reply -- same newline-delimited JSON event
    shape as /requirement/conversation/confirm/stream, so the frontend can show the agent's
    reaction+questions "typing" live as they're generated instead of a blocking wait followed by
    a sudden reveal:
        {"type": "token", "text": "..."}
        {"type": "error", "message": "..."}
        {"type": "done", "state": {...}}
    """
    _validate_feature(feature_id)
    stage_event_service.record(feature_id, AgentName.REQUIREMENT, "clarify", request.reply)

    async def event_stream():
        try:
            async for event in requirement_agent.reply_to_conversation_stream(
                feature_id=feature_id, reply_text=request.reply
            ):
                yield json.dumps(event) + "\n"
        except ValueError as error:
            yield json.dumps({"type": "error", "message": str(error)}) + "\n"
        except Exception as error:
            yield json.dumps(
                {"type": "error", "message": f"Failed to continue requirement conversation: {str(error)}"}
            ) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.post("/requirement/conversation/reply/upload", response_model=RequirementConversationState)
async def reply_to_requirement_conversation_with_document(
    feature_id: str,
    file: UploadFile = File(...),
    reply: str | None = Form(None),
):
    """
    Same as /requirement/conversation/reply, but the human's answer is (also) an attached
    text/PDF/DOCX/MD document -- its full text is extracted and handed to the same gap-analysis
    call, so the agent can scrape requirements directly out of an existing brief instead of the
    human retyping it by hand.
    """
    _validate_feature(feature_id)
    file_bytes = await file.read()
    stage_event_service.record(
        feature_id,
        AgentName.REQUIREMENT,
        "clarify",
        f"{reply or ''}\n\n[Attached file: {file.filename}]".strip(),
    )

    try:
        return await requirement_agent.reply_to_conversation_with_document(
            feature_id=feature_id, file_bytes=file_bytes, filename=file.filename, reply_text=reply
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Failed to process attached document: {str(error)}")


@router.post("/requirement/conversation/turns/{turn_index}/edit", response_model=RequirementConversationState)
async def edit_requirement_conversation_turn(
    feature_id: str, turn_index: int, request: RequirementConversationReplyRequest
):
    """
    Edit an already-submitted reply and regenerate the conversation from that point forward --
    mirrors ChatGPT/Claude's "edit message" flow. Discards the edited turn and everything built
    on top of it.
    """
    _validate_feature(feature_id)
    stage_event_service.record(feature_id, AgentName.REQUIREMENT, "clarify", request.reply)

    try:
        return await requirement_agent.edit_turn_reply(
            feature_id=feature_id, turn_index=turn_index, new_reply=request.reply
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Failed to edit requirement conversation turn: {str(error)}")


@router.post("/requirement/conversation/turns/{turn_index}/edit/stream")
async def edit_requirement_conversation_turn_stream(
    feature_id: str, turn_index: int, request: RequirementConversationReplyRequest
):
    """
    Streaming variant of /requirement/conversation/turns/{turn_index}/edit -- same
    newline-delimited JSON event shape as /requirement/conversation/reply/stream, so an edited
    message's regenerated reaction+questions "type" in live instead of sitting behind a plain
    spinner for however long the real LLM call takes (a real reported gap: editing was the one
    reply-shaped action in this conversation that didn't stream, making it look stalled/broken on
    a slow model even though it was quietly still working):
        {"type": "token", "text": "..."}
        {"type": "error", "message": "..."}
        {"type": "done", "state": {...}}
    """
    _validate_feature(feature_id)
    stage_event_service.record(feature_id, AgentName.REQUIREMENT, "clarify", request.reply)

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
                {"type": "error", "message": f"Failed to edit requirement conversation turn: {str(error)}"}
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
        raise HTTPException(status_code=500, detail=f"Failed to confirm requirement conversation: {str(error)}")


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
        feature_id, AgentName.REQUIREMENT, "confirm", request.override_reason, request.confirmed_by
    )

    async def event_stream():
        try:
            async for event in requirement_agent.confirm_conversation_stream(feature_id=feature_id, request=request):
                yield json.dumps(event) + "\n"
        except ValueError as error:
            yield json.dumps({"type": "error", "message": str(error)}) + "\n"
        except Exception as error:
            yield json.dumps(
                {"type": "error", "message": f"Failed to confirm requirement conversation: {str(error)}"}
            ) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


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
    stage_event_service.record(feature_id, AgentName.DOMAIN, "run", request.human_comment)

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


@router.post("/domain/run/stream")
async def run_domain_agent_stream(feature_id: str, request: DomainAgentRunRequest):
    """
    Streaming variant of /domain/run -- same newline-delimited JSON event shape as the
    Requirement Agent's streaming endpoints, so the frontend can show the enrichment plan
    "typing" live instead of a blocking wait followed by a sudden reveal:
        {"type": "token", "text": "..."}
        {"type": "error", "message": "..."}
        {"type": "done", "artifact_ids": [...], "message": "..."}
    """
    _validate_feature(feature_id)
    stage_event_service.record(feature_id, AgentName.DOMAIN, "run", request.human_comment)

    async def event_stream():
        try:
            async for event in domain_agent.run_stream(feature_id=feature_id, request=request):
                yield json.dumps(event) + "\n"
        except ValueError as error:
            yield json.dumps({"type": "error", "message": str(error)}) + "\n"
        except Exception as error:
            yield json.dumps({"type": "error", "message": f"Domain Agent failed: {str(error)}"}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


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
    stage_event_service.record(
        feature_id, AgentName.DOMAIN, "revise", request.revision_comment, request.revised_by
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
            detail=f"Domain Agent revision failed: {str(error)}"
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
            yield json.dumps({"type": "error", "message": f"Domain Agent revision failed: {str(error)}"}) + "\n"

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
    stage_event_service.record(
        feature_id, AgentName.ARCHITECTURE, "revise", request.revision_comment, request.revised_by
    )

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


@router.post("/architecture/run/stream")
async def run_architecture_agent_stream(feature_id: str, request: ArchitectureAgentRunRequest):
    """
    Streaming variant of /architecture/run -- same newline-delimited JSON event shape as Domain
    Agent's streaming endpoints, plus a "phase" event during the non-streamable tail (use case
    model, diagram generation, PlantUML rendering) so the frontend can show real progress instead
    of a bare loader once the plan text itself has finished streaming:
        {"type": "token", "text": "..."}
        {"type": "phase", "phase": "...", "label": "..."}
        {"type": "error", "message": "..."}
        {"type": "done", "artifact_ids": [...], "message": "..."}
    """
    _validate_feature(feature_id)
    stage_event_service.record(feature_id, AgentName.ARCHITECTURE, "run", request.human_comment)

    async def event_stream():
        try:
            async for event in architecture_agent.run_stream(feature_id=feature_id, request=request):
                yield json.dumps(event) + "\n"
        except ValueError as error:
            yield json.dumps({"type": "error", "message": str(error)}) + "\n"
        except Exception as error:
            yield json.dumps({"type": "error", "message": f"Architecture Agent failed: {str(error)}"}) + "\n"

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
        feature_id, AgentName.ARCHITECTURE, "revise", request.revision_comment, request.revised_by
    )

    async def event_stream():
        try:
            async for event in architecture_agent.revise_stream(feature_id=feature_id, request=request):
                yield json.dumps(event) + "\n"
        except ValueError as error:
            yield json.dumps({"type": "error", "message": str(error)}) + "\n"
        except Exception as error:
            yield json.dumps(
                {"type": "error", "message": f"Architecture Agent revision failed: {str(error)}"}
            ) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


    # ----------------------------------------------------
    # Ui/UX  Agent
    # ----------------------------------------------------
@router.post("/uiux/run", response_model=AgentRunResponse)
async def run_uiux_agent(feature_id: str, request: UIUXAgentRunRequest):
    """
    Run the UI/UX Agent.

    This endpoint:
    - requires an approved SRS JSON artifact and an approved Architecture Plan JSON artifact
    - optionally uses an approved Enhanced SRS JSON if available
    - generates ui_metadata, per-component code, and per-page preview screenshots

    Human approval is required after this -- both for the ui_metadata as a whole and for each
    individual component (see StageOutputPanel/GovernancePanel's separate component approval UI).
    """
    _validate_feature(feature_id)
    stage_event_service.record(feature_id, AgentName.UIUX, "run", request.human_comment)

    try:
        output = await uiux_agent.run(feature_id=feature_id, request=request)

        return AgentRunResponse(
            feature_id=feature_id,
            agent_name=AgentName.UIUX,
            status="completed",
            message="UI/UX Agent completed. Metadata and components require human approval.",
            artifact_ids=output.artifact_ids,
        )

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        print("========== UI/UX AGENT ERROR ==========")
        print(traceback.format_exc())
        print("========================================")

        raise HTTPException(
            status_code=500,
            detail=f"UI/UX Agent failed: {str(error)}"
        )


@router.post("/coder/run", response_model=AgentRunResponse)
async def run_coder_agent(feature_id: str, request: CoderAgentRunRequest):
    """
    Run the Coder Agent.

    This endpoint calls the same CoderAgent.run() the LangGraph coder_node uses internally --
    it lets a human trigger an initial Coder Agent run directly (e.g. from the chat UI) instead
    of only ever reaching it by advancing the graph. This can take several minutes (planning +
    the agentic coding loop + sandboxed build/lint/test verification), same as /coder/revise.

    Human approval is required after this, same as after a revision.
    """
    _validate_feature(feature_id)
    stage_event_service.record(feature_id, AgentName.CODER, "run", request.human_comment)

    try:
        output = await coder_agent.run(feature_id=feature_id, request=request)

        return AgentRunResponse(
            feature_id=feature_id,
            agent_name=AgentName.CODER,
            status="completed" if output.verification_passed else "completed_with_verification_failures",
            message=(
                "Coder Agent completed and verification passed. Requires human approval."
                if output.verification_passed
                else "Coder Agent completed but verification failed. Requires human review before approval."
            ),
            artifact_ids=output.artifact_ids,
        )

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        print("========== CODER AGENT ERROR ==========")
        print(traceback.format_exc())
        print("========================================")

        raise HTTPException(
            status_code=500,
            detail=f"Coder Agent failed: {str(error)}"
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
    stage_event_service.record(
        feature_id, AgentName.CODER, "revise", request.revision_comment, request.revised_by
    )

    try:
        output = await coder_agent.revise(feature_id=feature_id, request=request)

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

@router.post("/qa/run", response_model=AgentRunResponse)
async def run_qa_agent(
    feature_id: str,
    request: TestingRunRequest,
):
    """
    Run the QA Agent.

    This endpoint:
    - loads the generated project workspace
    - generates functional test cases
    - generates QA Markdown and JSON reports
    - saves all QA artifacts
    """

    _validate_feature(feature_id)

    try:
        return await qa_agent.run(
            feature_id=feature_id,
            request=request,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        print("========== QA AGENT ERROR ==========")
        print(traceback.format_exc())
        print("====================================")

        raise HTTPException(
            status_code=500,
            detail=f"QA Agent failed: {str(error)}",
        )