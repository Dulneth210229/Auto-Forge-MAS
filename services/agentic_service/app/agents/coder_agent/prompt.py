"""
Coder Agent prompt templates.

Purpose:
    Define the system prompt and user-prompt builder for the Coder Agent.

Architecture fit:
    - CODER_AGENT_SYSTEM_PROMPT is passed as the system_prompt argument
      to provider.generate() in agent.py.
    - build_coder_user_prompt() assembles the user turn from the agent input.
      It deliberately sends only the minimum required context to avoid
      overwhelming the LLM context window with irrelevant project files.

Prompt engineering principles applied here:
    1. Role clarity   — The LLM knows exactly who it is and what it must produce.
    2. Output contract — The exact JSON structure is specified, with field types.
    3. Merge rules    — Explicit instructions prevent the LLM from regenerating
                        existing features.
    4. Token control  — Only relevant existing files are included in the prompt.
    5. Safety rules   — The LLM is instructed never to invent secrets or hardcode
                        environment variables.

Author: Coder Agent (Auto-Forge MAS)
Version: 1.0.0
"""

from app.agents.coder_agent.schemas import CoderAgentInput


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

CODER_AGENT_SYSTEM_PROMPT = """
You are the Coder Agent in a Human-in-the-Loop Multi-Agent SDLC Automation System.

YOUR IDENTITY:
You are a Senior Full-Stack Software Engineer and Tech Lead.
You generate production-ready source code for ONE approved software feature at a time.
You work within an iterative SDLC: each iteration adds exactly one feature to the project.

YOUR CORE RESPONSIBILITIES:
1. Generate production-ready source code for the approved feature only.
2. Preserve all code from previous features exactly as provided.
3. Classify every file as: new, updated, or unchanged.
4. Generate requirement-to-code traceability mapping.
5. Declare all environment variables the code depends on.
6. Generate setup instructions for the human reviewer.
7. Generate a merge report summarizing what changed.

ABSOLUTE RULES — NEVER VIOLATE THESE:
- NEVER regenerate existing features. Only extend them.
- NEVER delete existing files.
- NEVER rename existing files.
- NEVER overwrite a file unless it must change to support the new feature.
- NEVER hardcode secrets, passwords, API keys, or connection strings.
- NEVER invent environment variable values. Only declare their names.
- NEVER generate placeholder implementations. Write real, working code.
- NEVER bypass the approved SRS, Enhanced SRS, and SDS requirements.
- ONLY generate files required by the current approved feature.

CODING STANDARDS:
- Write clean, readable, well-commented code.
- Every file must begin with a header comment block containing:
    Purpose, Feature, Author (Coder Agent), Version
- Use meaningful variable and function names.
- Separate concerns: routes/controllers/services/models must be distinct files.
- Handle errors gracefully. Use try/catch or equivalent error handling.
- Validate all inputs. Use Zod, Joi, Pydantic, or equivalent.
- Use environment variables for all configuration values.
- Follow the target stack's community conventions.

MERGE STRATEGY:
When you receive a list of existing project files:
- Files that DO NOT need modification: include them as "unchanged".
- Files that MUST be extended: include them as "updated" with full new content.
- Files that are COMPLETELY NEW: include them as "new".

For "updated" files: always include the COMPLETE new file content.
Do not use diff format. Do not use patch format. Return the full file.

ENVIRONMENT VARIABLES:
- Identify every configuration value the generated code depends on.
- List each one in env_vars_required with name, description, and example_value.
- Never put real secrets in example_value. Use placeholder strings like:
    "your-mongo-connection-string"
    "your-jwt-secret-key"

OUTPUT CONTRACT:
You must return a single valid JSON object. No markdown. No explanation.
No text before or after the JSON.

The JSON must have exactly these top-level keys:

{
  "generated_files": [
    {
      "file_path": "relative/path/from/project/root",
      "content": "full file content as a string",
      "change_type": "new",
      "purpose": "one-sentence purpose",
      "description": "longer description of role in feature",
      "feature_id": "feature id string",
      "version": 1
    }
  ],
  "updated_files": [
    {
      "file_path": "relative/path/from/project/root",
      "content": "full updated file content",
      "change_type": "updated",
      "purpose": "one-sentence purpose",
      "description": "what changed and why",
      "feature_id": "feature id string",
      "version": 2
    }
  ],
  "unchanged_files": [
    {
      "file_path": "relative/path/from/project/root",
      "content": "original file content unchanged",
      "change_type": "unchanged",
      "purpose": "one-sentence purpose",
      "description": "why this file was not modified",
      "feature_id": "feature id string",
      "version": 1
    }
  ],
  "env_vars_required": [
    {
      "name": "MONGO_URI",
      "description": "MongoDB connection string",
      "example_value": "mongodb://localhost:27017/myapp",
      "required": true
    }
  ],
  "run_commands": [
    "npm install",
    "npm run dev"
  ],
  "integration_notes": [
    "Add MONGO_URI to .env before running."
  ],
  "requirement_mapping": [
    {
      "requirement_id": "FR-001",
      "requirement_text": "User can login using email and password.",
      "file_paths": ["backend/routes/auth.js", "backend/services/auth.service.js"]
    }
  ],
  "setup_instructions_markdown": "# Setup\\n\\n...",
  "merge_report_markdown": "# Merge Report\\n\\n..."
}

CRITICAL: Return only the JSON object. Nothing else.
"""


# ---------------------------------------------------------------------------
# User prompt builder
# ---------------------------------------------------------------------------

def build_coder_user_prompt(agent_input: CoderAgentInput) -> str:
    """
    Build the user-turn prompt for the Coder Agent.

    This function assembles context from the agent input, keeping the
    prompt as concise as possible to stay within LLM token limits:

    - Full approved artifacts (SRS, Enhanced SRS, SDS) are included because
      the LLM needs them to understand what to generate.
    - The previous project snapshot is included as a compact file list
      (paths + purposes only), not full file content.
    - Relevant existing files whose content the LLM may need to update
      are included in full.
    - The human revision comment is appended if present.

    Args:
        agent_input: The assembled CoderAgentInput from the API route.

    Returns:
        The formatted user prompt string.
    """

    # ------------------------------------------------------------------
    # Section 1: Project + feature context
    # ------------------------------------------------------------------
    context_section = f"""
PROJECT CONTEXT:
- Project Name:  {agent_input.project_name}
- Project Type:  {agent_input.project_type}
- Project ID:    {agent_input.project_id}
- Target Stack:  {agent_input.target_stack}

CURRENT FEATURE:
- Feature Name:  {agent_input.feature_name}
- Feature ID:    {agent_input.feature_id}
"""

    # ------------------------------------------------------------------
    # Section 2: Already implemented features (to preserve)
    # ------------------------------------------------------------------
    if agent_input.previous_feature_names:
        existing_features_list = "\n".join(
            f"  - {name}" for name in agent_input.previous_feature_names
        )
        previous_features_section = f"""
ALREADY IMPLEMENTED FEATURES (DO NOT REGENERATE):
{existing_features_list}

You must preserve all code for these features.
Only extend shared files (routes, models) where necessary.
"""
    else:
        previous_features_section = """
EXISTING FEATURES: None. This is the first feature iteration.
"""

    # ------------------------------------------------------------------
    # Section 3: Existing project file inventory (paths + purposes only)
    # ------------------------------------------------------------------
    if agent_input.previous_project_snapshot:
        file_inventory_lines = []
        for f in agent_input.previous_project_snapshot:
            file_inventory_lines.append(
                f"  [{f.change_type.upper()}] {f.file_path} — {f.purpose}"
            )
        file_inventory = "\n".join(file_inventory_lines)
        snapshot_section = f"""
EXISTING PROJECT FILE INVENTORY:
(These files already exist. Classify each as unchanged or updated.)
{file_inventory}
"""
    else:
        snapshot_section = """
EXISTING PROJECT FILES: None. Start a fresh project structure.
"""

    # ------------------------------------------------------------------
    # Section 4: Approved artifact content
    # ------------------------------------------------------------------
    approved_srs_section = f"""
APPROVED SOFTWARE REQUIREMENTS SPECIFICATION (SRS):
{agent_input.approved_srs_markdown}
"""

    approved_enhanced_srs_section = f"""
APPROVED ENHANCED SOFTWARE REQUIREMENTS SPECIFICATION (Enhanced SRS):
{agent_input.approved_enhanced_srs_markdown}
"""

    approved_sds_section = f"""
APPROVED SOFTWARE DESIGN SPECIFICATION (SDS):
{agent_input.approved_sds_markdown}
"""

    ui_design_section = ""
    if agent_input.approved_ui_design_html:
        ui_design_section = f"""
APPROVED UI DESIGN (HTML):
{agent_input.approved_ui_design_html}
"""

    # ------------------------------------------------------------------
    # Section 5: Optional coding standards override
    # ------------------------------------------------------------------
    coding_standards_section = ""
    if agent_input.coding_standards:
        coding_standards_section = f"""
ADDITIONAL CODING STANDARDS FOR THIS RUN:
{agent_input.coding_standards}
"""

    # ------------------------------------------------------------------
    # Section 6: Environment variables already provided by human
    # ------------------------------------------------------------------
    if agent_input.env_vars_provided:
        env_vars_lines = "\n".join(
            f"  - {key}: [PROVIDED]"
            for key in agent_input.env_vars_provided.keys()
        )
        env_provided_section = f"""
ENVIRONMENT VARIABLES PROVIDED BY HUMAN:
(These have been supplied. Do NOT ask for them. Declare them in env_vars_required.)
{env_vars_lines}
"""
    else:
        env_provided_section = """
ENVIRONMENT VARIABLES PROVIDED: None provided yet.
Declare all required variables in env_vars_required.
"""

    # ------------------------------------------------------------------
    # Section 7: Human revision comment (only present on revision runs)
    # ------------------------------------------------------------------
    revision_section = ""
    if agent_input.human_comment:
        revision_section = f"""
HUMAN REVISION COMMENT:
(Apply this feedback carefully. Modify only affected files.)
{agent_input.human_comment}
"""

    # ------------------------------------------------------------------
    # Section 8: Task instruction
    # ------------------------------------------------------------------
    task_section = f"""
TASK:
Generate production-ready source code for the '{agent_input.feature_name}' feature.

Requirements:
1. Generate ONLY the files needed for '{agent_input.feature_name}'.
2. Classify each existing file as updated or unchanged.
3. Follow the SRS, Enhanced SRS, and SDS exactly.
4. Apply the target stack conventions for: {agent_input.target_stack}
5. Declare all environment variables in env_vars_required.
6. Generate setup_instructions_markdown with clear setup steps.
7. Generate merge_report_markdown summarizing new, updated, and unchanged files.
8. Map every requirement ID to its implementing files in requirement_mapping.
9. Return a single valid JSON object with no extra text.
"""

    # ------------------------------------------------------------------
    # Assemble the full prompt
    # ------------------------------------------------------------------
    return "\n".join([
        context_section,
        previous_features_section,
        snapshot_section,
        approved_srs_section,
        approved_enhanced_srs_section,
        approved_sds_section,
        ui_design_section,
        coding_standards_section,
        env_provided_section,
        revision_section,
        task_section,
    ])