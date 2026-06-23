"""Pipeline preview operations."""
from __future__ import annotations

from typing import Any

import httpx


def run_preview(
    client: httpx.Client, group: str, data: dict[str, Any], pack: str | None = None
) -> Any:
    """Run a pipeline preview with the given data."""
    if pack:
        url = f"/api/v1/m/{group}/p/{pack}/preview"
    else:
        url = f"/api/v1/m/{group}/preview"
    resp = client.post(url, json=data)
    resp.raise_for_status()
    return resp.json()
