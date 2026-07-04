"""
Coder Agent coding loop.

This is the one non-deterministic step in the Coder Agent pipeline: an
agentic, tool-using loop that executes a pre-validated code_plan_json against
the project's real workspace. Everything around it (planning, plan
validation, workspace prep, verification, diffing) is deterministic code --
this module is intentionally small and does not try to make the loop itself
deterministic, only to scope what it's allowed to touch (via the tools it's
given) and what it's told to do (via the validated plan).

Milestone note: as of M4, this is invoked manually (see
scripts/run_coder_loop_manual.py), not from CoderAgent.run() or the graph --
that wiring happens once M5's verify/diff/merge steps exist to wrap it.
"""

from __future__ import annotations

import json
from typing import Any

from langchain.agents import create_agent
from langchain_core.runnables import Runnable

from app.agents.coder_agent.prompt import CODER_AGENT_SYSTEM_PROMPT
from app.agents.coder_agent.tools import build_coder_tools
from app.providers.agentic_model_factory import get_agentic_chat_model


def build_coder_react_agent(project_id: str, feature_id: str) -> Runnable:
    """
    Build the Coder Agent's agentic loop, with tools scoped to one project's
    workspace and one feature's approved UI/UX output.
    """
    tools = build_coder_tools(project_id, feature_id)

    return create_agent(
        model=get_agentic_chat_model(),
        tools=tools,
        system_prompt=CODER_AGENT_SYSTEM_PROMPT,
    )


def build_task_message(code_plan_json: dict[str, Any], prior_failure_output: str | None = None) -> str:
    """
    Format the validated plan (+ optional prior verification failure, for the
    retry path M5 will drive) into the initial human message for the loop.
    """
    sections = [
        "Implement the following pre-approved, pre-validated code plan.",
        "",
        json.dumps(code_plan_json, indent=2, default=str),
    ]

    if prior_failure_output:
        sections.extend(
            [
                "",
                "A previous attempt at this plan failed verification. Fix the issue below, "
                "then continue:",
                prior_failure_output,
            ]
        )

    return "\n".join(sections)
