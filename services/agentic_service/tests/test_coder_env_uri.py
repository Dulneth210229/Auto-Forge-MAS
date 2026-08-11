"""
Unit tests for env_uri.py -- MongoDB URI detection/extraction from a human's
free-text chat message. Pure functions, no LLM/Docker/git.
"""

from app.agents.coder_agent.env_uri import extract_mongodb_uri, is_uri_only, strip_uri_from_comment


def test_extract_returns_none_for_no_uri():
    assert extract_mongodb_uri("add a delete confirmation dialog") is None


def test_extract_returns_none_for_empty_or_none():
    assert extract_mongodb_uri("") is None
    assert extract_mongodb_uri(None) is None


def test_extract_finds_plain_mongodb_uri():
    text = "mongodb://user:pass@localhost:27017/mydb"
    assert extract_mongodb_uri(text) == text


def test_extract_finds_srv_uri():
    text = "mongodb+srv://user:pass@cluster0.mongodb.net/mydb"
    assert extract_mongodb_uri(text) == text


def test_extract_strips_trailing_sentence_punctuation():
    assert extract_mongodb_uri("here's my uri: mongodb://localhost:27017/db.") == "mongodb://localhost:27017/db"
    assert extract_mongodb_uri("(mongodb://localhost:27017/db)") == "mongodb://localhost:27017/db"


def test_extract_finds_uri_embedded_in_longer_message():
    text = "Here's my mongo uri: mongodb+srv://user:pass@cluster.net/db also add a delete button"
    uri = extract_mongodb_uri(text)
    assert uri == "mongodb+srv://user:pass@cluster.net/db"


def test_strip_uri_only_message_returns_none():
    # "URI-only" is intentionally literal -- the message minus the matched URI substring must be
    # empty/whitespace/plain-punctuation. A bare paste of the URI (optionally with surrounding
    # whitespace or trailing punctuation) qualifies; a sentence describing it does not (see
    # test_strip_uri_with_lead_in_text_is_not_uri_only below) -- deliberately not fuzzy-matching
    # lead-in phrases like "here's my uri:", which would be exactly the kind of brittle phrase-
    # fitting this codebase's own established checkers avoid elsewhere.
    uri = "mongodb://localhost:27017/db"
    assert strip_uri_from_comment(uri, uri) is None
    assert strip_uri_from_comment(f"  {uri}  ", uri) is None
    assert strip_uri_from_comment(f"{uri}.", uri) is None


def test_strip_uri_with_lead_in_text_is_not_uri_only():
    uri = "mongodb://localhost:27017/db"
    remainder = strip_uri_from_comment(f"here's my uri: {uri}", uri)
    assert remainder is not None
    assert "here's my uri" in remainder


def test_strip_uri_with_other_instructions_keeps_remainder():
    uri = "mongodb+srv://user:pass@cluster.net/db"
    text = f"Here's my mongo uri: {uri} also add a delete button"
    remainder = strip_uri_from_comment(text, uri)
    assert remainder is not None
    assert "delete button" in remainder
    assert uri not in remainder


def test_is_uri_only_true_and_false():
    uri = "mongodb://localhost:27017/db"
    assert is_uri_only(uri, uri) is True
    assert is_uri_only(f"  {uri}  ", uri) is True
    assert is_uri_only(f"{uri} also add a loading spinner", uri) is False
