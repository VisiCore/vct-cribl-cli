"""Pipeline management endpoints."""
from __future__ import annotations

from typing import Any

import httpx


def _base(group: str, pack: str | None = None) -> str:
    if pack:
        return f"/api/v1/m/{group}/p/{pack}/pipelines"
    return f"/api/v1/m/{group}/pipelines"


def list_pipelines(client: httpx.Client, group: str, pack: str | None = None) -> Any:
    """List all pipelines in a worker group (or pack)."""
    resp = client.get(_base(group, pack))
    resp.raise_for_status()
    return resp.json()


def get_pipeline(
    client: httpx.Client, group: str, pipeline_id: str, pack: str | None = None
) -> Any:
    """Get a specific pipeline by ID."""
    resp = client.get(f"{_base(group, pack)}/{pipeline_id}")
    resp.raise_for_status()
    return resp.json()


def create_pipeline(
    client: httpx.Client,
    group: str,
    data: dict[str, Any],
    pack: str | None = None,
) -> Any:
    """Create a new pipeline."""
    resp = client.post(_base(group, pack), json=data)
    resp.raise_for_status()
    return resp.json()


def update_pipeline(
    client: httpx.Client,
    group: str,
    pipeline_id: str,
    data: dict[str, Any],
    pack: str | None = None,
) -> Any:
    """Update an existing pipeline."""
    resp = client.patch(f"{_base(group, pack)}/{pipeline_id}", json=data)
    resp.raise_for_status()
    return resp.json()


def delete_pipeline(
    client: httpx.Client, group: str, pipeline_id: str, pack: str | None = None
) -> Any:
    """Delete a pipeline by ID."""
    resp = client.delete(f"{_base(group, pack)}/{pipeline_id}")
    resp.raise_for_status()
    return resp.json()
