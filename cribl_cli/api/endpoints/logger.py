"""Logger configuration operations."""
from __future__ import annotations

from typing import Any

import httpx


def get_logger(client: httpx.Client, group: str) -> Any:
    """Get logger configuration for a worker group."""
    resp = client.get(f"/api/v1/m/{group}/system/logger")
    resp.raise_for_status()
    return resp.json()


def set_logger(client: httpx.Client, group: str, data: dict[str, Any]) -> Any:
    """Update logger configuration for a worker group."""
    resp = client.patch(f"/api/v1/m/{group}/system/logger", json=data)
    resp.raise_for_status()
    return resp.json()
