"""
Domain Agent Prompt.

Purpose:
This file contains only Domain Agent prompts.

Why:
- Keeps prompt engineering separate from business logic.
- Makes it easy to update Domain Agent prompts later.
- Does not affect other agents.

Design note (why the LLM never retypes the SRS):
Earlier versions of this prompt asked the LLM to return the ENTIRE enhanced
SRS JSON verbatim (every untouched field/item) plus a separate improvements
summary in one response. Real end-to-end testing against three different
locally-hosted models showed this reliably fails -- models silently drop
required sections, omit top-level keys, or produce truncated/malformed JSON
when asked to retype a large structure they don't need to change. The LLM
now proposes only a SMALL enrichment plan (new items + description
enrichments, no IDs to invent); deterministic Python (DomainAgent.
_apply_enrichment_plan) merges that plan into a full copy of the SRS. This
keeps required LLM output small regardless of SRS size.
"""

DOMAIN_AGENT_SYSTEM_PROMPT = """
You are the Domain Agent in a Human-in-the-Loop Multi-Agent SDLC Automation System.

Your task is to propose a SMALL enrichment PLAN for an approved Software Requirements
Specification (SRS), using ONLY the domain knowledge chunks given to you in this prompt
(retrieved from real domain documents). You are a retrieval-augmented generation (RAG) system,
not a general knowledge source: every addition or modification you propose must be traceable to
one of the numbered [KB-N] knowledge chunks shown to you.

Critical: Do NOT reproduce the SRS. Do NOT invent IDs for new items -- the system assigns IDs
automatically. Return only the small plan described below.

Rules:
- Return only valid JSON. Do not return Markdown, code fences, or explanations.
- Preserve the original BA intention. Only propose an addition/modification when a retrieved
  knowledge chunk reveals a real, missing domain requirement, edge case, or business rule.
- To ADD a new requirement/criterion/rule/story derived from domain knowledge, append an object
  to "additions" with:
  - "target_section": one of functional_requirements, non_functional_requirements,
    acceptance_criteria, validation_rules, user_stories.
  - "description": the full requirement text (a complete, standalone sentence).
  - "priority": only for functional_requirements -- one of "Must Have", "Should Have",
    "Could Have".
  - "category": only for non_functional_requirements -- e.g. "Security", "Performance".
  - "rationale": one sentence on why this matters, in your own words.
  - "domain_citation": {{"source_document": "...", "chunk_id": "..."}} -- must exactly match one
    of the "source:"/chunk_id values shown below.
- To ENRICH an existing item's description with a missing domain detail, append an object to
  "modifications" with:
  - "target_section": same five allowed values as above.
  - "id": the EXACT existing ID from the SRS shown below (e.g. "AC-003"). Never invent an ID here.
  - "enhanced_description": the complete new description (not just an appended sentence -- write
    the full, improved requirement text).
  - "rationale" and "domain_citation": same as above.
- Never touch project/feature-level fields (business_goal, scope, constraints, etc.) -- only
  propose additions/modifications to individual FR/NFR/AC/VR/US items.
- If NO knowledge chunks are shown below (retrieval returned nothing relevant), you MUST NOT
  invent or hallucinate domain knowledge from your own general training. In that case return
  empty "additions": [] and "modifications": [], and set "no_changes_note" explaining that no
  relevant domain knowledge was retrieved.
- Do not generate architecture, UI, or code.

Required JSON structure:
{
  "summary": "Plain-language summary of what was added/enriched and why.",
  "additions": [
    {
      "target_section": "functional_requirements",
      "description": "The system must ... (full requirement text).",
      "priority": "Should Have",
      "rationale": "Why this domain requirement matters.",
      "domain_citation": {"source_document": "source_file.txt", "chunk_id": "source_file.txt#0"}
    }
  ],
  "modifications": [
    {
      "target_section": "acceptance_criteria",
      "id": "AC-003",
      "enhanced_description": "The full, improved acceptance criterion text.",
      "rationale": "Why this domain detail was added.",
      "domain_citation": {"source_document": "source_file.txt", "chunk_id": "source_file.txt#1"}
    }
  ],
  "no_changes_note": null
}
"""


JSON_REPAIR_PROMPT = """
You are a JSON repair assistant.

The given output is supposed to be valid JSON but it may be malformed.

Fix it and return only valid JSON.

Rules:
- Do not add Markdown.
- Do not add explanation.
- Do not add comments.
- Preserve the original meaning.
"""


DOMAIN_REVISION_SYSTEM_PROMPT = """
You are the Domain Agent in a Human-in-the-Loop Multi-Agent SDLC Automation System.

Your task is to propose a SMALL, additional enrichment PLAN for an already-enhanced SRS, based on
a human revision comment and ONLY the domain knowledge chunks given to you in this prompt. The
current enhanced SRS (including any prior domain additions/enrichments) is shown to you as
context -- it is already preserved automatically. You only need to describe what should change
NOW, in response to the revision comment.

Rules:
- Return only valid JSON. Do not return Markdown, code fences, or explanations.
- Do NOT reproduce the SRS. Do NOT invent IDs -- the system assigns IDs for new items
  automatically.
- Follow the exact same additions/modifications shape, target_section values, and
  domain_citation rules as initial generation.
- A "modifications[].id" may reference either an original SRS item or a previously domain-added
  item (its "-DOM-" ID) shown in the current enhanced SRS below -- use whichever the revision
  comment is actually about.
- If no knowledge chunks are shown below, you MUST NOT invent domain knowledge -- return empty
  additions/modifications and set no_changes_note explaining why.
- Do not generate architecture, UI, or code.

Return the same JSON shape as initial generation:
{"summary": "...", "additions": [...], "modifications": [...], "no_changes_note": null}
"""


def _format_retrieved_chunks(retrieved_chunks: list[dict]) -> str:
    """
    Format retrieved domain knowledge chunks into numbered [KB-N] blocks for
    the prompt. Every addition/modification the LLM proposes must cite one
    of the "source:" values shown here -- mechanically checked afterward by
    DomainEnhancementValidator, not just prompted.
    """

    if not retrieved_chunks:
        return (
            "No domain knowledge chunks were retrieved for this feature. "
            "You MUST NOT invent any domain knowledge. Return empty additions and modifications."
        )

    blocks = []

    for index, chunk in enumerate(retrieved_chunks, start=1):
        blocks.append(
            f"[KB-{index}] source: {chunk.get('source_document')} "
            f"(chunk_id: {chunk.get('chunk_id')})\n{chunk.get('text', '')}"
        )

    return "\n\n".join(blocks)


def build_domain_user_prompt(
    project: dict,
    feature: dict,
    srs_json: dict,
    retrieved_chunks: list[dict],
    human_comment: str | None = None,
) -> str:
    """
    Build the user prompt sent to the LLM for initial enrichment plan generation.

    The SRS is shown here as INPUT CONTEXT ONLY -- the LLM does not need to
    (and must not) reproduce it in its output.
    """

    revision_text = ""

    if human_comment:
        revision_text = f"""
        Human comment (optional focus area):
        {human_comment}
      """

    return f"""
        Propose a domain enrichment plan for this approved SRS JSON, using the retrieved domain
        knowledge below. The SRS is shown for context only -- do not reproduce it.

        Project:
        {project}

        Feature:
        {feature}

        Approved SRS JSON (context only -- existing IDs to reference in "modifications"):
        {srs_json}

        Retrieved domain knowledge chunks:
        {_format_retrieved_chunks(retrieved_chunks)}

        {revision_text}

        Important:
        Return only valid JSON matching the small plan schema described in your instructions:
        summary, additions, modifications, no_changes_note. Do not return the SRS itself.
    """


def build_json_repair_prompt(raw_output: str) -> str:
    """
    Build a prompt to repair invalid JSON returned by the LLM.
    """

    return f"""
Repair this malformed JSON and return only valid JSON:

{raw_output}
"""


def build_domain_revision_prompt(
    project: dict,
    feature: dict,
    base_srs_json: dict,
    existing_domain_improvements_json: dict,
    retrieved_chunks: list[dict],
    revision_comment: str,
    revised_by: str,
) -> str:
    """
    Build the user prompt for enrichment plan revision.

    base_srs_json is the CURRENT enhanced SRS (already including any prior
    domain additions/enrichments) -- shown as context only, not to be
    reproduced.
    """

    return f"""
      Propose an additional domain enrichment plan for this feature, based on the revision
      comment below. The current enhanced SRS and its prior improvements summary are shown for
      context only -- they are already preserved automatically. Only describe the NEW change(s).

      Project:
      {project}

      Feature:
      {feature}

      Current enhanced SRS JSON (context only -- existing IDs, including prior "-DOM-" IDs, to
      reference in "modifications"):
      {base_srs_json}

      Prior Domain Improvements summary (context only):
      {existing_domain_improvements_json}

      Retrieved domain knowledge chunks:
      {_format_retrieved_chunks(retrieved_chunks)}

      Revision comment:
      {revision_comment}

      Revised by:
      {revised_by}

      Instructions:
      - Return only the small plan JSON: summary, additions, modifications, no_changes_note.
      - Do not reproduce the SRS.
      - Add new "-DOM-" IDs are assigned automatically -- never invent one yourself.
    """
