"""Unwrap single-item API responses."""

from __future__ import annotations

from typing import Any


def unwrap_item(data: Any) -> Any:
    if isinstance(data, dict) and "items" in data and len(data["items"]) == 1:
        return data["items"][0]
    return data
