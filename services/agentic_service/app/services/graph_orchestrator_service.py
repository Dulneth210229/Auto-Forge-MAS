"""
Top-level LangGraph orchestrator.

This replaces "call each agent endpoint manually, in order" with one LangGraph
StateGraph per feature, checkpointed in MongoDB, that pauses on interrupt() at
every human approval gate and resumes exactly where it left off -- even across
backend restarts -- via Command(resume=...).

Milestone 0 scope: every stage node is a pass-through no-op. This proves the
graph mechanics (interrupt/resume/checkpoint-survives-restart) independently
of any agent's real quality. Each stage's node is replaced with a call into
that agent's real logic as it is rebuilt (UI/UX, Coder), without touching the
approval-gate/routing plumbing built here.

Security and QA stages are intentionally auto-approved pass-through nodes (no
human interrupt) for now, since neither agent exists yet -- there is nothing
for a human to review. Flip these to real interrupt() gates the moment those
agents produce real output (see the doc's Milestone 7 section).
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from typing_extensions import TypedDict

from app.core.config import settings
from app.services.in_memory_store import store
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Stages that stop for a human approval gate.
GATED_STAGES = ["requirement", "domain", "architecture", "uiux", "coder"]

# Stages that run automatically with no human gate (no agent implementation yet).
AUTO_APPROVED_STAGES = ["security", "qa"]

STAGE_SEQUENCE = GATED_STAGES + AUTO_APPROVED_STAGES


class FeaturePipelineState(TypedDict, total=False):
    project_id: str
    feature_id: str
    human_comment: str | None
    last_agent: str
    last_artifact_ids: list[str]
    approval_decision: str | None


class GraphNotRunningError(Exception):
    """Raised when resume() is called for a feature with no paused graph run."""


def _make_stage_node(stage_name: str):
    def _node(state: FeaturePipelineState) -> dict[str, Any]:
        logger.info(
            "Pass-through node running: stage=%s feature_id=%s",
            stage_name,
            state.get("feature_id"),
        )
        return {
            "last_agent": stage_name,
            "last_artifact_ids": [],
            "human_comment": None,
        }

    return _node


def _make_approval_gate(stage_name: str):
    def _gate(state: FeaturePipelineState) -> dict[str, Any]:
        decision = interrupt(
            {
                "feature_id": state["feature_id"],
                "agent_name": stage_name,
                "artifact_ids": state.get("last_artifact_ids", []),
                "message": f"Review {stage_name} output before continuing.",
            }
        )
        return {"approval_decision": decision}

    return _gate


def _make_router(stage_name: str, next_node: str):
    def _route(state: FeaturePipelineState) -> str:
        if state.get("approval_decision") == "approved":
            return next_node
        # rejected / revision_requested -> loop back into the same stage's node
        return f"{stage_name}_node"

    return _route


def _build_checkpointer() -> MongoDBSaver:
    """
    Reuse the app's existing MongoDB connection (store.client) rather than
    opening a second one. Checkpoints/writes go into their own collections so
    they never collide with the app's projects/features/artifacts/approvals.
    """
    return MongoDBSaver(
        client=store.client,
        db_name=settings.MONGODB_DATABASE,
        checkpoint_collection_name="langgraph_checkpoints",
        writes_collection_name="langgraph_checkpoint_writes",
    )


def _build_graph():
    builder = StateGraph(FeaturePipelineState)

    for stage in GATED_STAGES:
        builder.add_node(f"{stage}_node", _make_stage_node(stage))
        builder.add_node(f"approve_{stage}", _make_approval_gate(stage))
        builder.add_edge(f"{stage}_node", f"approve_{stage}")

    for stage in AUTO_APPROVED_STAGES:
        builder.add_node(f"{stage}_node", _make_stage_node(stage))

    builder.add_edge(START, "requirement_node")

    for index, stage in enumerate(GATED_STAGES):
        next_stage_node = f"{STAGE_SEQUENCE[index + 1]}_node"
        same_stage_node = f"{stage}_node"

        builder.add_conditional_edges(
            f"approve_{stage}",
            _make_router(stage, next_stage_node),
            {next_stage_node: next_stage_node, same_stage_node: same_stage_node},
        )

    builder.add_edge("security_node", "qa_node")
    builder.add_edge("qa_node", END)

    return builder.compile(checkpointer=_build_checkpointer())


class GraphOrchestratorService:
    """
    Drives the per-feature pipeline graph. thread_id = feature_id for every
    invoke/resume call, so a human can approve a stage hours or days later and
    the graph picks up exactly where it paused, even after a backend restart.
    """

    def __init__(self):
        self._graph = _build_graph()

    def _config(self, feature_id: str) -> dict[str, Any]:
        return {"configurable": {"thread_id": feature_id}}

    def start(self, project_id: str, feature_id: str) -> dict[str, Any]:
        """
        Start a feature's pipeline run for the first time.
        """
        logger.info("Starting graph run for feature_id=%s", feature_id)

        return self._graph.invoke(
            {"project_id": project_id, "feature_id": feature_id},
            config=self._config(feature_id),
        )

    def resume(self, feature_id: str, resume_value: str) -> dict[str, Any]:
        """
        Resume a paused feature pipeline after a human approval decision.

        Raises GraphNotRunningError if this feature has no paused graph run
        (e.g. the artifact was approved through the legacy manual flow rather
        than a graph run started via start()).
        """
        config = self._config(feature_id)
        state = self._graph.get_state(config)

        if not state.next:
            raise GraphNotRunningError(
                f"No paused graph run found for feature_id={feature_id}"
            )

        logger.info(
            "Resuming graph run for feature_id=%s with decision=%s",
            feature_id,
            resume_value,
        )

        return self._graph.invoke(Command(resume=resume_value), config=config)

    def get_status(self, feature_id: str) -> dict[str, Any]:
        """
        Return the current pending node(s) and state values for a feature's run.
        """
        state = self._graph.get_state(self._config(feature_id))

        return {
            "next": list(state.next),
            "values": dict(state.values),
        }


graph_orchestrator_service = GraphOrchestratorService()
