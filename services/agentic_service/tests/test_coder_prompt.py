"""
Trivial substring-presence tests locking in the Coder Agent system prompt's
hard rules. These only prove the rules are present in the text sent to the
model -- they cannot prove the model actually follows them (that's what the
real end-to-end run against the real e-commerce-platform project is for).
"""

from app.agents.coder_agent.prompt import CODE_PLANNER_SYSTEM_PROMPT, CODER_AGENT_SYSTEM_PROMPT


def test_prompt_forbids_hardcoded_fake_handlers():
    assert "hardcoded or fake logic" in CODER_AGENT_SYSTEM_PROMPT
    assert "authService.js" in CODER_AGENT_SYSTEM_PROMPT


def test_prompt_requires_flagging_placeholder_stubs():
    assert "in a real app, you would" in CODER_AGENT_SYSTEM_PROMPT
    assert "final plain-text summary" in CODER_AGENT_SYSTEM_PROMPT


def test_prompt_requires_request_body_validation():
    assert "req.body" in CODER_AGENT_SYSTEM_PROMPT
    assert "400-style response" in CODER_AGENT_SYSTEM_PROMPT


def test_prompt_requires_wiring_every_prop_a_reused_component_needs():
    assert "pass every prop its logic depends on" in CODER_AGENT_SYSTEM_PROMPT


def test_prompt_requires_syntax_check_and_gap_check_tools():
    assert "check_syntax" in CODER_AGENT_SYSTEM_PROMPT
    assert "list_unimplemented_planned_files" in CODER_AGENT_SYSTEM_PROMPT


def test_prompt_describes_feature_routes_marker_patch_target():
    assert "FEATURE_ROUTES_END" in CODER_AGENT_SYSTEM_PROMPT
    assert "never patch `module.exports = app;` directly" in CODER_AGENT_SYSTEM_PROMPT


def test_planner_prompt_describes_feature_routes_marker():
    assert "FEATURE_ROUTES_START" in CODE_PLANNER_SYSTEM_PROMPT
    assert "FEATURE_ROUTES_END" in CODE_PLANNER_SYSTEM_PROMPT


def test_prompt_requires_a_link_for_every_route():
    flattened = " ".join(CODER_AGENT_SYSTEM_PROMPT.split())
    assert "FEATURE_LINKS_END" in flattened
    assert "never rewrite `HomePage`'s JSX wholesale" in flattened
    assert "an unreachable page is exactly the" in flattened


def test_planner_prompt_requires_link_and_list_page_for_parameterized_routes():
    assert "FEATURE_LINKS_START" in CODE_PLANNER_SYSTEM_PROMPT
    assert "FEATURE_LINKS_END" in CODE_PLANNER_SYSTEM_PROMPT
    assert "do NOT link directly" in CODE_PLANNER_SYSTEM_PROMPT
    assert "list/index page" in CODE_PLANNER_SYSTEM_PROMPT
