"""Fleet-scoped edge operations for containers, processes, logs, and files."""
from __future__ import annotations

from typing import Any

import httpx


def list_containers(client: httpx.Client, group: str, fleet_id: str) -> Any:
    """List containers for an edge fleet."""
    resp = client.get(f"/api/v1/m/{group}/fleet/{fleet_id}/containers")
    resp.raise_for_status()
    return resp.json()


def list_processes(client: httpx.Client, group: str, fleet_id: str) -> Any:
    """List processes for an edge fleet."""
    resp = client.get(f"/api/v1/m/{group}/fleet/{fleet_id}/processes")
    resp.raise_for_status()
    return resp.json()


def get_logs(client: httpx.Client, group: str, fleet_id: str) -> Any:
    """Get logs for an edge fleet."""
    resp = client.get(f"/api/v1/m/{group}/fleet/{fleet_id}/logs")
    resp.raise_for_status()
    return resp.json()


def get_metadata(client: httpx.Client, group: str, fleet_id: str) -> Any:
    """Get metadata for an edge fleet."""
    resp = client.get(f"/api/v1/m/{group}/fleet/{fleet_id}/metadata")
    resp.raise_for_status()
    return resp.json()


def get_events(client: httpx.Client, group: str, fleet_id: str, source_id: str) -> Any:
    """Get events for a specific source on an edge fleet."""
    resp = client.get(f"/api/v1/m/{group}/fleet/{fleet_id}/events/{source_id}")
    resp.raise_for_status()
    return resp.json()


def list_files(client: httpx.Client, group: str, fleet_id: str, path: str = "/") -> Any:
    """List files on an edge fleet."""
    resp = client.get(f"/api/v1/m/{group}/fleet/{fleet_id}/files", params={"path": path})
    resp.raise_for_status()
    return resp.json()


def get_kube_logs(client: httpx.Client, group: str, fleet_id: str, **params: Any) -> Any:
    """Get Kubernetes logs for an edge fleet."""
    resp = client.get(f"/api/v1/m/{group}/fleet/{fleet_id}/kube-logs", params=params)
    resp.raise_for_status()
    return resp.json()
