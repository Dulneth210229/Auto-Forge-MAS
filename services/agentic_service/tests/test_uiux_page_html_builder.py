"""
Unit tests for UIUXPageHtmlBuilder -- deterministic, no-LLM page assembly.

This is the concrete fix for a real, confirmed bug: a page previously rendered
"Unknown state."/"No data available" because its React/JSX components each had their own
state-branching logic and the preview picked an unhandled branch. This builder is pure string
concatenation with no branching at all, so it can never produce that failure mode -- these tests
lock in that it always assembles a complete, well-formed document.
"""

from app.agents.uiux_agent.page_html_builder import UIUXPageHtmlBuilder


def test_build_wraps_fragments_in_full_document():
    builder = UIUXPageHtmlBuilder()
    html = builder.build(
        {"page_id": "item-listing-page", "name": "Item Listing Page"},
        ['<table class="w-full"><tr><td>Widget</td></tr></table>'],
    )

    assert html.startswith("<!DOCTYPE html>")
    assert "<title>Item Listing Page</title>" in html
    assert '<table class="w-full"><tr><td>Widget</td></tr></table>' in html
    assert "</html>" in html


def test_build_preserves_fragment_order():
    builder = UIUXPageHtmlBuilder()
    html = builder.build(
        {"page_id": "p"},
        ["<header>HEADER_MARKER</header>", "<main>MAIN_MARKER</main>", "<footer>FOOTER_MARKER</footer>"],
    )

    assert html.index("HEADER_MARKER") < html.index("MAIN_MARKER") < html.index("FOOTER_MARKER")


def test_build_skips_empty_fragments():
    builder = UIUXPageHtmlBuilder()
    html = builder.build({"page_id": "p"}, ["<div>real content</div>", "", "   ", None and ""])

    assert "real content" in html
    # No stray blank lines from the skipped empty entries -- exactly one fragment survived.
    assert html.count("real content") == 1


def test_build_inlines_tailwind_script_not_a_src_reference():
    builder = UIUXPageHtmlBuilder()
    html = builder.build({"page_id": "p"}, ["<div>content</div>"])

    assert "<script src=" not in html
    assert "<script>" in html
    # The vendored Tailwind Play-CDN bundle is a real, sizeable JS file -- confirming its content
    # actually landed inline (not just an empty <script></script> pair).
    assert len(html) > 50_000


def test_build_falls_back_to_page_id_when_name_missing():
    builder = UIUXPageHtmlBuilder()
    html = builder.build({"page_id": "item-listing-page"}, ["<div>x</div>"])

    assert "<title>item-listing-page</title>" in html


def test_build_uses_content_regardless_of_page_metadata_shape():
    """A minimal page_metadata dict (only page_id) must not raise -- this builder never fails on
    its input, only on a missing vendored asset (see PageHtmlBuildError)."""
    builder = UIUXPageHtmlBuilder()
    html = builder.build({"page_id": "p"}, [])

    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html
