"""Grep-based filtering for list tool responses."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any

from fastmcp.exceptions import ToolError
from pydantic import BaseModel


class _DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime/date objects from devopsarr models."""

    def default(self, o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, date):
            return o.isoformat()
        return super().default(o)


_encoder = _DateTimeEncoder()


def grep_filter(
    items: list[BaseModel],
    pattern: str | None,
) -> list[BaseModel]:
    """Filter items by regex matching against their JSON representation.

    Each item is serialized to JSON (with datetime handling), and the
    pattern is matched case-insensitively against the full JSON string.
    Only items with at least one match are retained.

    Args:
        items: List of Pydantic model instances to filter.
        pattern: A regex pattern string, or None to skip filtering.

    Returns:
        Filtered list of items (same type as input).

    Raises:
        ToolError: If the regex pattern is invalid.
    """
    if pattern is None:
        return items

    try:
        compiled = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        raise ToolError(f"Invalid grep pattern '{pattern}': {e}") from e

    return [item for item in items if compiled.search(_encoder.encode(item.to_dict()))]
