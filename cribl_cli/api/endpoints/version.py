"""Version control operations for Cribl configuration."""
from __future__ import annotations

from typing import Any

import httpx


def get_version_info(client: httpx.Client, group: str) -> Any:
    """Get version control info for a worker group."""
    resp = client.get(f"/api/v1/m/{group}/version")
    resp.raise_for_status()
    return resp.json()


def get_version_status(client: httpx.Client, group: str) -> Any:
    """Get uncommitted changes status."""
    resp = client.get(f"/api/v1/m/{group}/version/status")
    resp.raise_for_status()
    return resp.json()


def get_version_diff(client: httpx.Client, group: str) -> Any:
    """Get diff of uncommitted changes."""
    resp = client.get(f"/api/v1/m/{group}/version/diff")
    resp.raise_for_status()
    return resp.json()


def commit_version(client: httpx.Client, group: str, message: str) -> Any:
    """Commit pending configuration changes."""
    resp = client.post(f"/api/v1/m/{group}/version/commit", json={"message": message})
    resp.raise_for_status()
    return resp.json()


def push_version(client: httpx.Client, group: str) -> Any:
    """Push committed changes to deploy."""
    resp = client.post(f"/api/v1/m/{group}/version/push")
    resp.raise_for_status()
    return resp.json()


def sync_version(client: httpx.Client, group: str) -> Any:
    """Sync version control state."""
    resp = client.post(f"/api/v1/m/{group}/version/sync")
    resp.raise_for_status()
    return resp.json()


def list_branches(client: httpx.Client, group: str) -> Any:
    """List available branches."""
    resp = client.get(f"/api/v1/m/{group}/version/branches")
    resp.raise_for_status()
    return resp.json()


def get_current_branch(client: httpx.Client, group: str) -> Any:
    """Get the current active branch."""
    resp = client.get(f"/api/v1/m/{group}/version/current-branch")
    resp.raise_for_status()
    return resp.json()
