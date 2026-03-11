"""Source (input) management endpoints."""
from __future__ import annotations

from typing import Any

import httpx


def _base(group: str) -> str:
    return f"/api/v1/m/{group}/system/inputs"


def list_sources(client: httpx.Client, group: str) -> Any:
    """List all sources in a worker group."""
    resp = client.get(_base(group))
    resp.raise_for_status()
    return resp.json()


def get_source(client: httpx.Client, group: str, source_id: str) -> Any:
    """Get a specific source by ID."""
    resp = client.get(f"{_base(group)}/{source_id}")
    resp.raise_for_status()
    return resp.json()


def create_source(client: httpx.Client, group: str, data: dict[str, Any]) -> Any:
    """Create a new source."""
    resp = client.post(_base(group), json=data)
    resp.raise_for_status()
    return resp.json()


def update_source(
    client: httpx.Client, group: str, source_id: str, data: dict[str, Any]
) -> Any:
    """Update an existing source."""
    resp = client.patch(f"{_base(group)}/{source_id}", json=data)
    resp.raise_for_status()
    return resp.json()


def delete_source(client: httpx.Client, group: str, source_id: str) -> Any:
    """Delete a source by ID."""
    resp = client.delete(f"{_base(group)}/{source_id}")
    resp.raise_for_status()
    return resp.json()
