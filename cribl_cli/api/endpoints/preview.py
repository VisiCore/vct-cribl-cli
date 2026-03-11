"""Pipeline preview operations."""
from __future__ import annotations

from typing import Any

import httpx


def run_preview(client: httpx.Client, group: str, data: dict[str, Any]) -> Any:
    """Run a pipeline preview with the given data."""
    resp = client.post(f"/api/v1/m/{group}/preview", json=data)
    resp.raise_for_status()
    return resp.json()
