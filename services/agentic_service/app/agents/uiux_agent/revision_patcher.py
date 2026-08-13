"""
Deterministic UI/UX metadata revision patcher.

Why this exists:
Mirrors the same "small ops plan + deterministic patcher" pattern already proven for the
Requirement Agent's SRS (app/agents/requirement_agent/revision_patcher.py) and the Architecture
Agent's plan (app/agents/architecture_agent/revision_patcher.py): asking the LLM to retype an
entire structured document for every revision is unreliable on this project's local models, and
a deterministic Python apply step means a requested change either genuinely happens or is
reported as unmatched -- it can never silently no-op inside an otherwise-plausible full retype.

ui_metadata_json's shape is much shallower than the SRS/Architecture Plan (a list of pages, each
with a list of components), so the patcher here only needs to handle one kind of item: a
component entry, matched by (page_id, component_name).
"""

from __future__ import annotations

import copy
import re
from typing import Any


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip().lower())


def _find_page(pages: list[dict], page_id: str | None) -> dict | None:
    if not page_id:
        return None

    target = _normalize(page_id)
    for page in pages:
        if _normalize(page.get("page_id", "")) == target:
            return page

    return None


def _find_component(pages: list[dict], page_id: str | None, component_name: str) -> tuple[dict, int] | None:
    """
    Find (page, index_within_that_page's_components) for the component matching
    component_name, scoped to page_id if given, otherwise searched across every page.
    Exact-name match only (component names are short, deliberate identifiers, not prose --
    unlike the SRS/Architecture Plan patchers, there is no long-text substring case to support
    here).
    """

    target_name = _normalize(component_name)
    if not target_name:
        return None

    candidate_pages = [_find_page(pages, page_id)] if page_id else pages
    candidate_pages = [page for page in candidate_pages if page]

    for page in candidate_pages:
        components = page.get("components") or []
        for index, component in enumerate(components):
            if _normalize(component.get("name", "")) == target_name:
                return page, index

    return None


def apply_uiux_revision_operations(
    ui_metadata_json: dict, operations: list[dict]
) -> tuple[dict, list[str], list[str]]:
    """
    Apply a small list of component-level revision operations to a copy of ui_metadata_json.

    Each operation is a dict with:
        "action": "add" | "remove" | "modify"
        "page_id": the page's page_id (required for "add"; used to disambiguate for
            "remove"/"modify" when the same component name could exist on more than one page,
            optional otherwise)
        "component_name": the component's "name"
        "content_elements": list[str] (required for "add"/"modify")
        "new_component_justification": str (only meaningful for "add" of a genuinely new
            component)
        "covers_ui_expectations": list[str] (optional, for "add")

    Returns (patched_metadata, applied, unmatched) -- `applied`/`unmatched` are human-readable
    notes, never raised as exceptions: an operation this function can't confidently apply is
    reported, not guessed at.
    """

    patched = copy.deepcopy(ui_metadata_json)
    patched.setdefault("pages", [])
    pages: list[dict] = patched["pages"]

    applied: list[str] = []
    unmatched: list[str] = []

    for operation in operations:
        if not isinstance(operation, dict):
            unmatched.append(f"Skipped malformed operation: {operation!r}")
            continue

        action = str(operation.get("action", "")).strip().lower()
        component_name = str(operation.get("component_name", "")).strip()
        page_id = operation.get("page_id")

        try:
            if action == "add":
                _apply_add(pages, page_id, component_name, operation, applied, unmatched)
            elif action == "remove":
                _apply_remove(pages, page_id, component_name, applied, unmatched)
            elif action == "modify":
                _apply_modify(pages, page_id, component_name, operation, applied, unmatched)
            else:
                unmatched.append(
                    f"Skipped operation with unsupported action '{action}' on '{component_name}'."
                )
        except Exception as error:  # noqa: BLE001 -- one bad operation must never break the rest
            unmatched.append(
                f"Skipped operation on '{component_name}' (action={action}) due to error: {error}"
            )

    return patched, applied, unmatched


def _apply_add(
    pages: list[dict],
    page_id: Any,
    component_name: str,
    operation: dict,
    applied: list[str],
    unmatched: list[str],
) -> None:
    if not component_name:
        unmatched.append("Skipped 'add' operation -- no component_name provided.")
        return

    page = _find_page(pages, page_id)
    if page is None:
        unmatched.append(
            f"Could not add '{component_name}' -- page_id {page_id!r} does not match any "
            "existing page."
        )
        return

    content_elements = operation.get("content_elements")
    if not content_elements or not isinstance(content_elements, list):
        unmatched.append(f"Skipped 'add {component_name}' -- no content_elements provided.")
        return

    existing = _find_component(pages, page.get("page_id"), component_name)
    if existing is not None:
        unmatched.append(
            f"Skipped 'add {component_name}' -- a component with that name already exists on "
            f"page '{page.get('page_id')}'. Use 'modify' instead."
        )
        return

    new_component = {
        "name": component_name,
        "reused_from_design_system": False,
        "new_component_justification": operation.get("new_component_justification", "Requested by human revision."),
        "covers_ui_expectations": operation.get("covers_ui_expectations") or [],
        "content_elements": content_elements,
        # Transient marker, stripped by the caller (UIUXAgent) after collecting which
        # components need fresh HTML generation -- never persisted to a saved artifact.
        "_revision_touched": True,
    }

    page.setdefault("components", []).append(new_component)
    applied.append(f"Added component '{component_name}' to page '{page.get('page_id')}'.")


def _apply_remove(
    pages: list[dict],
    page_id: Any,
    component_name: str,
    applied: list[str],
    unmatched: list[str],
) -> None:
    if not component_name:
        unmatched.append("Skipped 'remove' operation -- no component_name provided.")
        return

    match = _find_component(pages, page_id, component_name)
    if match is None:
        unmatched.append(
            f"Could not find a component named '{component_name}' "
            + (f"on page '{page_id}' " if page_id else "")
            + "to remove."
        )
        return

    page, index = match
    removed = page["components"].pop(index)
    applied.append(f"Removed component '{removed.get('name', component_name)}' from page '{page.get('page_id')}'.")


def _apply_modify(
    pages: list[dict],
    page_id: Any,
    component_name: str,
    operation: dict,
    applied: list[str],
    unmatched: list[str],
) -> None:
    if not component_name:
        unmatched.append("Skipped 'modify' operation -- no component_name provided.")
        return

    match = _find_component(pages, page_id, component_name)
    if match is None:
        unmatched.append(
            f"Could not find a component named '{component_name}' "
            + (f"on page '{page_id}' " if page_id else "")
            + "to modify."
        )
        return

    page, index = match
    component = dict(page["components"][index])

    content_elements = operation.get("content_elements")
    changed_parts = []

    if content_elements and isinstance(content_elements, list):
        component["content_elements"] = content_elements
        changed_parts.append("content_elements")

    covers_ui_expectations = operation.get("covers_ui_expectations")
    if covers_ui_expectations and isinstance(covers_ui_expectations, list):
        component["covers_ui_expectations"] = covers_ui_expectations
        changed_parts.append("covers_ui_expectations")

    if not changed_parts:
        unmatched.append(
            f"Skipped 'modify {component_name}' -- no content_elements/covers_ui_expectations "
            "provided to change."
        )
        return

    component["_revision_touched"] = True
    page["components"][index] = component
    applied.append(
        f"Modified component '{component_name}' on page '{page.get('page_id')}' ({', '.join(changed_parts)})."
    )
