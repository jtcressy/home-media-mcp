"""Response formatting utilities for MCP tool responses."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Callable

from pydantic import BaseModel


def _make_serializable(obj: Any) -> Any:
    """Recursively convert non-JSON-serializable types to serializable ones.

    Handles datetime/date objects from devopsarr API responses that
    to_dict() returns as raw Python objects.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_serializable(v) for v in obj]
    return obj


def summarize_item(item: BaseModel, max_fields: int = 10) -> dict[str, Any]:
    """Extract a summary of an item with only the smallest scalar fields.

    Converts the item to a dict, identifies scalar fields (str, int, float,
    bool, None), sorts them by their serialized string length (ascending),
    and returns the top `max_fields`. The 'id' field is always included
    regardless of size.

    Args:
        item: A Pydantic model instance (from devopsarr libraries).
        max_fields: Maximum number of fields to include in the summary.

    Returns:
        A dict with at most max_fields scalar key-value pairs.
    """
    full = _make_serializable(item.to_dict())

    # Separate id field if present
    id_value = full.get("id")

    # Identify scalar fields (exclude id, it's handled separately)
    scalar_fields: list[tuple[str, Any]] = []
    for key, value in full.items():
        if key == "id":
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            scalar_fields.append((key, value))

    # Sort by serialized string length (ascending) - smallest first
    scalar_fields.sort(key=lambda kv: len(json.dumps(kv[1], default=str)))

    # Build result: id first (if present), then smallest scalars
    result: dict[str, Any] = {}
    if id_value is not None:
        result["id"] = id_value
        remaining = max_fields - 1
    else:
        remaining = max_fields

    for key, value in scalar_fields[:remaining]:
        result[key] = value

    return result


def summarize_list(
    items: list[BaseModel],
    max_fields: int = 10,
    summary_fn: Callable[[list[BaseModel]], dict[str, Any]] | None = None,
    preserve_fields: list[str] | None = None,
) -> dict[str, Any]:
    """Format a list of items as a summary response.

    Args:
        items: List of Pydantic model instances.
        max_fields: Maximum scalar fields per item summary.
        summary_fn: Optional callback that takes the full items list and
            returns additional aggregate stats for the summary field.
            For example: {"monitored": 32, "unmonitored": 15}
        preserve_fields: Optional list of field names that must be included
            in each item summary, even if they're large. These are added
            after the max_fields limit.

    Returns:
        A dict with:
            - "summary": {"total": N, ...additional stats from summary_fn}
            - "items": [summarized item dicts]
    """
    summary: dict[str, Any] = {"total": len(items)}

    if summary_fn is not None:
        summary.update(summary_fn(items))

    return {
        "summary": summary,
        "items": [
            _summarize_item_with_preserve(item, max_fields, preserve_fields)
            for item in items
        ],
    }


def _summarize_item_with_preserve(
    item: BaseModel, max_fields: int = 10, preserve_fields: list[str] | None = None
) -> dict[str, Any]:
    """Like summarize_item but ensures preserve_fields are always included."""
    result = summarize_item(item, max_fields=max_fields)
    if preserve_fields:
        full = _make_serializable(item.to_dict())
        for field in preserve_fields:
            if field in full and field not in result:
                result[field] = full[field]
    return result


def full_detail(item: BaseModel) -> dict[str, Any]:
    """Return the complete API response for a single item.

    Args:
        item: A Pydantic model instance.

    Returns:
        The complete dict representation including all nested objects.
    """
    return _make_serializable(item.to_dict())
