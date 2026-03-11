"""Profiler operations for worker groups."""
from __future__ import annotations

from typing import Any

import httpx


def get_profiler(client: httpx.Client, group: str) -> Any:
    """Get profiler status for a worker group."""
    resp = client.get(f"/api/v1/m/{group}/system/profiler")
    resp.raise_for_status()
    return resp.json()


def start_profiler(client: httpx.Client, group: str) -> Any:
    """Start the profiler for a worker group."""
    resp = client.post(f"/api/v1/m/{group}/system/profiler/start")
    resp.raise_for_status()
    return resp.json()


def stop_profiler(client: httpx.Client, group: str) -> Any:
    """Stop the profiler for a worker group."""
    resp = client.post(f"/api/v1/m/{group}/system/profiler/stop")
    resp.raise_for_status()
    return resp.json()
