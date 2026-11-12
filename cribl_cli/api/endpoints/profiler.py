"""Profiler operations for worker groups."""
from __future__ import annotations

from typing import Any

import httpx


def get_profiler(client: httpx.Client, group: str) -> Any:
    """Get profiler status for a worker group."""
    resp = client.get(f"/api/v1/m/{group}/system/profiler")
    resp.raise_for_status()
    return resp.json()
