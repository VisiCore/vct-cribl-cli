"""System information, health, and management operations."""
from __future__ import annotations

from typing import Any

import httpx


def get_system_info(client: httpx.Client) -> Any:
    """Get system information."""
    resp = client.get("/api/v1/system/info")
    resp.raise_for_status()
    return resp.json()


def get_system_settings(client: httpx.Client) -> Any:
    """Get system settings."""
    resp = client.get("/api/v1/system/settings")
    resp.raise_for_status()
    return resp.json()


def get_system_health(client: httpx.Client) -> Any:
    """Get overall system health status."""
    resp = client.get("/api/v1/health")
    resp.raise_for_status()
    return resp.json()


def get_instance_info(client: httpx.Client) -> Any:
    """Get instance information."""
    resp = client.get("/api/v1/system/instance")
    resp.raise_for_status()
    return resp.json()


def get_worker_health(client: httpx.Client, group: str) -> Any:
    """Get health status for workers, optionally filtered by group."""
    resp = client.get("/api/v1/master/workers")
    resp.raise_for_status()
    data = resp.json()
    if group:
        items = [w for w in data.get("items", []) if w.get("group") == group]
        data = {**data, "items": items, "count": len(items)}
    return data


def get_system_logs(client: httpx.Client, limit: int | None = None) -> Any:
    """Get system logs, optionally limited."""
    params: dict[str, Any] = {}
    if limit is not None:
        params["limit"] = limit
    resp = client.get("/api/v1/system/logs", params=params)
    resp.raise_for_status()
    return resp.json()


def get_system_log(client: httpx.Client, log_type: str) -> Any:
    """Get a specific system log by type."""
    resp = client.get(f"/api/v1/system/logs/{log_type}")
    resp.raise_for_status()
    return resp.json()


def get_system_diag(client: httpx.Client) -> Any:
    """Get system diagnostics."""
    resp = client.get("/api/v1/system/diag")
    resp.raise_for_status()
    return resp.json()


def send_system_diag(client: httpx.Client) -> Any:
    """Send system diagnostics to Cribl support."""
    resp = client.post("/api/v1/system/diag/send")
    resp.raise_for_status()
    return resp.json()


def restart_system(client: httpx.Client) -> Any:
    """Restart the system."""
    resp = client.post("/api/v1/system/restart")
    resp.raise_for_status()
    return resp.json()


def reload_system(client: httpx.Client) -> Any:
    """Reload system configuration."""
    resp = client.post("/api/v1/system/reload")
    resp.raise_for_status()
    return resp.json()


def upgrade_system(client: httpx.Client) -> Any:
    """Upgrade the system."""
    resp = client.post("/api/v1/system/upgrade")
    resp.raise_for_status()
    return resp.json()
