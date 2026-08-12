"""
Trivial substring-presence tests locking in the Coder Agent system prompt's
hard rules (Next.js App Router + TypeScript). These only prove the rules are
present in the text sent to the model -- they cannot prove the model actually
follows them (that's what the real end-to-end run is for).
"""

from app.agents.coder_agent.prompt import CODE_PLANNER_SYSTEM_PROMPT, CODER_AGENT_SYSTEM_PROMPT


def test_prompt_forbids_hardcoded_fake_handlers():
    assert "hardcoded or fake logic" in CODER_AGENT_SYSTEM_PROMPT
    assert "lib/api/auth.ts" in CODER_AGENT_SYSTEM_PROMPT


def test_prompt_requires_flagging_placeholder_stubs():
    assert "in a real app, you would" in CODER_AGENT_SYSTEM_PROMPT
    assert "final plain-text summary" in CODER_AGENT_SYSTEM_PROMPT


def test_prompt_requires_request_body_validation():
    assert "validate that required fields are present" in CODER_AGENT_SYSTEM_PROMPT
    assert "status: 400" in CODER_AGENT_SYSTEM_PROMPT


def test_prompt_requires_wiring_every_prop_a_reused_component_needs():
    assert "pass every prop its logic depends on" in CODER_AGENT_SYSTEM_PROMPT


def test_prompt_requires_syntax_check_and_gap_check_tools():
    assert "check_syntax" in CODER_AGENT_SYSTEM_PROMPT
    assert "list_unimplemented_planned_files" in CODER_AGENT_SYSTEM_PROMPT


def test_prompt_requires_blanket_use_client_rule():
    assert '"use client";' in CODER_AGENT_SYSTEM_PROMPT
    assert "no exceptions" in CODER_AGENT_SYSTEM_PROMPT
    assert "Route Handlers (`route.ts`) are server-only" in CODER_AGENT_SYSTEM_PROMPT


def test_prompt_pins_next_14_synchronous_params_contract():
    assert "PLAIN OBJECT" in CODER_AGENT_SYSTEM_PROMPT
    assert "do NOT `await` them" in CODER_AGENT_SYSTEM_PROMPT
    assert "Next.js 15" in CODER_AGENT_SYSTEM_PROMPT


def test_prompt_forbids_server_actions():
    assert "Server Actions" in CODER_AGENT_SYSTEM_PROMPT
    assert "FORBIDDEN" in CODER_AGENT_SYSTEM_PROMPT


def test_prompt_requires_mongoose_model_guard():
    assert "mongoose.models.X || mongoose.model" in CODER_AGENT_SYSTEM_PROMPT
    assert "OverwriteModelError" in CODER_AGENT_SYSTEM_PROMPT


def test_prompt_forbids_build_error_suppression():
    assert "ignoreBuildErrors" in CODER_AGENT_SYSTEM_PROMPT
    assert "ignoreDuringBuilds" in CODER_AGENT_SYSTEM_PROMPT


def test_prompt_has_no_express_router_mount_step():
    # Next.js's file-based routing means there is no app.js-equivalent
    # "mount the router" step at all -- confirm the old MERN-era marker
    # doesn't leak back in.
    assert "FEATURE_ROUTES" not in CODER_AGENT_SYSTEM_PROMPT
    assert "FEATURE_ROUTES" not in CODE_PLANNER_SYSTEM_PROMPT
    assert "never needs a separate \"mount\" step" in CODER_AGENT_SYSTEM_PROMPT


def test_prompt_requires_a_link_for_every_route():
    flattened = " ".join(CODER_AGENT_SYSTEM_PROMPT.split())
    assert "FEATURE_LINKS_END" in flattened
    assert "never rewrite `HomePage`'s JSX wholesale" in flattened
    assert "an unreachable page is exactly the" in flattened


def test_planner_prompt_requires_link_and_list_page_for_parameterized_routes():
    assert "FEATURE_LINKS_START" in CODE_PLANNER_SYSTEM_PROMPT
    assert "FEATURE_LINKS_END" in CODE_PLANNER_SYSTEM_PROMPT
    assert "do NOT link" in CODE_PLANNER_SYSTEM_PROMPT
    assert "list/index page" in CODE_PLANNER_SYSTEM_PROMPT


def test_planner_prompt_requires_separate_files_for_collection_and_item_endpoints():
    assert "ALWAYS two different" in CODE_PLANNER_SYSTEM_PROMPT
    assert "app/api/<resource>/[id]/route.ts" in CODE_PLANNER_SYSTEM_PROMPT


def test_planner_prompt_distinguishes_remove_from_restore():
    assert "OPPOSITE actions" in CODE_PLANNER_SYSTEM_PROMPT
    assert "the footer has been removed" in CODE_PLANNER_SYSTEM_PROMPT
    assert "RESTORE" in CODE_PLANNER_SYSTEM_PROMPT


def test_coder_prompt_trusts_original_request_over_plan_rationale():
    assert "Original human request" in CODER_AGENT_SYSTEM_PROMPT
    assert "TRUST THE ORIGINAL REQUEST" in CODER_AGENT_SYSTEM_PROMPT
