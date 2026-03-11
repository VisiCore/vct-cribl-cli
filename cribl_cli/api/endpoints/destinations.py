"""Destination (output) management endpoints."""
from __future__ import annotations

from typing import Any

import httpx


def _base(group: str) -> str:
    return f"/api/v1/m/{group}/system/outputs"


def list_destinations(client: httpx.Client, group: str) -> Any:
    """List all destinations in a worker group."""
    resp = client.get(_base(group))
    resp.raise_for_status()
    return resp.json()


def get_destination(client: httpx.Client, group: str, dest_id: str) -> Any:
    """Get a specific destination by ID."""
    resp = client.get(f"{_base(group)}/{dest_id}")
    resp.raise_for_status()
    return resp.json()


def create_destination(
    client: httpx.Client, group: str, data: dict[str, Any]
) -> Any:
    """Create a new destination."""
    resp = client.post(_base(group), json=data)
    resp.raise_for_status()
    return resp.json()


def update_destination(
    client: httpx.Client, group: str, dest_id: str, data: dict[str, Any]
) -> Any:
    """Update an existing destination."""
    resp = client.patch(f"{_base(group)}/{dest_id}", json=data)
    resp.raise_for_status()
    return resp.json()


def delete_destination(client: httpx.Client, group: str, dest_id: str) -> Any:
    """Delete a destination by ID."""
    resp = client.delete(f"{_base(group)}/{dest_id}")
    resp.raise_for_status()
    return resp.json()
