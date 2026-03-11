"""Pipeline management endpoints."""
from __future__ import annotations

from typing import Any

import httpx


def _base(group: str) -> str:
    return f"/api/v1/m/{group}/pipelines"


def list_pipelines(client: httpx.Client, group: str) -> Any:
    """List all pipelines in a worker group."""
    resp = client.get(_base(group))
    resp.raise_for_status()
    return resp.json()


def get_pipeline(client: httpx.Client, group: str, pipeline_id: str) -> Any:
    """Get a specific pipeline by ID."""
    resp = client.get(f"{_base(group)}/{pipeline_id}")
    resp.raise_for_status()
    return resp.json()


def create_pipeline(
    client: httpx.Client, group: str, data: dict[str, Any]
) -> Any:
    """Create a new pipeline."""
    resp = client.post(_base(group), json=data)
    resp.raise_for_status()
    return resp.json()


def update_pipeline(
    client: httpx.Client, group: str, pipeline_id: str, data: dict[str, Any]
) -> Any:
    """Update an existing pipeline."""
    resp = client.patch(f"{_base(group)}/{pipeline_id}", json=data)
    resp.raise_for_status()
    return resp.json()


def delete_pipeline(client: httpx.Client, group: str, pipeline_id: str) -> Any:
    """Delete a pipeline by ID."""
    resp = client.delete(f"{_base(group)}/{pipeline_id}")
    resp.raise_for_status()
    return resp.json()
