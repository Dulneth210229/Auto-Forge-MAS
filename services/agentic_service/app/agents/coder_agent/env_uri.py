"""
MongoDB URI detection in a human's chat message.

Purpose:
A human can switch a generated app from serving seed data (see
db_fallback_checker.py / prompt.py's "Database availability fallback" rule)
to a real database by pasting a MongoDB connection string into the Coder
Agent chat -- there is no other realistic mechanism, since sandbox/preview
containers never see host env vars and Docker has no way to inject one into
an already-running container (confirmed directly: neither
sandbox_service.run_command nor start_background_service passes
`environment=`). The only real path is writing the URI into `.env.local`
(workspace_service.write_env_local) and restarting whatever container next
starts. This module is the deterministic, regex-based first step: pull the
URI (if any) out of the human's free-text comment before it ever reaches an
LLM prompt -- there is no reason to show a credential to a planner once it's
handled here.
"""

from __future__ import annotations

import re

MONGODB_URI_PATTERN = re.compile(r"mongodb(?:\+srv)?://\S+", re.IGNORECASE)
_TRAILING_PUNCTUATION = ")]}>.,;:!?'\""


def extract_mongodb_uri(text: str | None) -> str | None:
    """First `mongodb(+srv)://` URI substring in `text`, with trailing sentence
    punctuation stripped, or None if no match."""
    if not text:
        return None

    match = MONGODB_URI_PATTERN.search(text)
    if not match:
        return None

    return match.group(0).rstrip(_TRAILING_PUNCTUATION) or None


def strip_uri_from_comment(text: str, uri: str) -> str | None:
    """`text` with the first occurrence of `uri` removed and surrounding
    whitespace/punctuation trimmed. Returns None if nothing meaningful
    remains -- i.e. the message WAS the URI -- which callers use as the
    "URI-only" signal."""
    remainder = text.replace(uri, "", 1).strip(" \t\n\r.,;:!?-")
    return remainder or None


def is_uri_only(text: str, uri: str) -> bool:
    return strip_uri_from_comment(text, uri) is None
