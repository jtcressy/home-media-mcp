"""Name-to-ID resolution utilities for human-friendly tool parameters."""

from __future__ import annotations

from typing import Any

from fastmcp.exceptions import ToolError


def resolve_quality_profile(
    name_or_id: str | int,
    profiles: list[Any],
) -> int:
    """Resolve a quality profile name or ID to a numeric ID.

    Args:
        name_or_id: Either a numeric ID (int or digit string) or a
            quality profile name (case-insensitive match).
        profiles: List of quality profile objects with 'id' and 'name'
            attributes (from devopsarr API).

    Returns:
        The numeric quality profile ID.

    Raises:
        ToolError: If no match found or multiple matches found.
    """
    return _resolve_by_name_or_id(
        name_or_id=name_or_id,
        items=profiles,
        name_attr="name",
        entity_type="quality profile",
    )


def resolve_root_folder(
    path_or_id: str | int,
    folders: list[Any],
) -> int:
    """Resolve a root folder path or ID to a numeric ID.

    The path match is a case-insensitive substring match, so passing
    '/tv' will match '/mnt/media/tv'.

    Args:
        path_or_id: Either a numeric ID (int or digit string) or a
            path substring (case-insensitive).
        folders: List of root folder objects with 'id' and 'path'
            attributes (from devopsarr API).

    Returns:
        The numeric root folder ID.

    Raises:
        ToolError: If no match found or multiple matches found.
    """
    # If it's an ID, handle directly
    if isinstance(path_or_id, int) or (
        isinstance(path_or_id, str) and path_or_id.isdigit()
    ):
        target_id = int(path_or_id)
        for folder in folders:
            if folder.id == target_id:
                return target_id
        raise ToolError(f"Root folder with ID {target_id} not found.")

    # Path substring match
    path_lower = str(path_or_id).lower()
    matches = [f for f in folders if path_lower in (f.path or "").lower()]

    if len(matches) == 0:
        available = [f"{f.id}: {f.path}" for f in folders]
        raise ToolError(
            f"No root folder matching '{path_or_id}'. Available: {', '.join(available)}"
        )
    if len(matches) > 1:
        ambiguous = [f"{f.id}: {f.path}" for f in matches]
        raise ToolError(
            f"Ambiguous root folder '{path_or_id}' matches multiple: "
            f"{', '.join(ambiguous)}. Use the numeric ID instead."
        )

    return matches[0].id


def resolve_tag(
    name_or_id: str | int,
    tags: list[Any],
) -> int:
    """Resolve a tag name or ID to a numeric ID.

    Args:
        name_or_id: Either a numeric ID (int or digit string) or a
            tag label (case-insensitive exact match).
        tags: List of tag objects with 'id' and 'label' attributes
            (from devopsarr API).

    Returns:
        The numeric tag ID.

    Raises:
        ToolError: If no match found or multiple matches found.
    """
    return _resolve_by_name_or_id(
        name_or_id=name_or_id,
        items=tags,
        name_attr="label",
        entity_type="tag",
    )


def _resolve_by_name_or_id(
    name_or_id: str | int,
    items: list[Any],
    name_attr: str,
    entity_type: str,
) -> int:
    """Generic name-or-ID resolution.

    Args:
        name_or_id: Either a numeric ID or a name string.
        items: List of objects with 'id' and the specified name attribute.
        name_attr: The attribute name to match against (e.g., 'name', 'label').
        entity_type: Human-readable entity type for error messages.

    Returns:
        The resolved numeric ID.

    Raises:
        ToolError: If resolution fails.
    """
    # Numeric ID passthrough
    if isinstance(name_or_id, int) or (
        isinstance(name_or_id, str) and name_or_id.isdigit()
    ):
        target_id = int(name_or_id)
        for item in items:
            if item.id == target_id:
                return target_id
        raise ToolError(f"{entity_type.title()} with ID {target_id} not found.")

    # Name match (case-insensitive)
    name_lower = str(name_or_id).lower()
    matches = [
        item
        for item in items
        if (getattr(item, name_attr, None) or "").lower() == name_lower
    ]

    if len(matches) == 0:
        available = [f"{item.id}: {getattr(item, name_attr, '?')}" for item in items]
        raise ToolError(
            f"No {entity_type} matching '{name_or_id}'. "
            f"Available: {', '.join(available)}"
        )
    if len(matches) > 1:
        ambiguous = [f"{item.id}: {getattr(item, name_attr, '?')}" for item in matches]
        raise ToolError(
            f"Ambiguous {entity_type} '{name_or_id}' matches multiple: "
            f"{', '.join(ambiguous)}. Use the numeric ID instead."
        )

    return matches[0].id
