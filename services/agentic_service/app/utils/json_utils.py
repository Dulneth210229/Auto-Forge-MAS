"""
JSON utility helpers.

This file helps extract valid JSON from LLM responses.

LLMs may return:
1. Raw JSON
2. JSON inside markdown code blocks
3. JSON mixed with normal explanation text

Architecture Agent uses this function to parse the LLM output.
"""

import json
import re
from typing import Any


def extract_json_from_text(text: str) -> dict[str, Any]:
    """
    Extract the first valid JSON object from text.

    Args:
        text: Raw text returned by the LLM.

    Returns:
        Parsed JSON as a Python dictionary.

    Raises:
        ValueError: If no valid JSON object is found.
    """

    # 1. Try direct JSON parsing first.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Try JSON inside markdown code block.
    code_block_match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        text,
        re.DOTALL
    )

    if code_block_match:
        possible_json = code_block_match.group(1)

        try:
            return json.loads(possible_json)
        except json.JSONDecodeError:
            pass

    # 3. Try to find any JSON-looking object in the text.
    object_match = re.search(r"(\{.*\})", text, re.DOTALL)

    if object_match:
        possible_json = object_match.group(1)

        try:
            return json.loads(possible_json)
        except json.JSONDecodeError:
            pass

    # 4. If nothing works, raise a clear error.
    raise ValueError("No valid JSON object found in LLM response.")