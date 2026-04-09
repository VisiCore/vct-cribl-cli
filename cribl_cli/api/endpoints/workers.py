"""Worker group management endpoints."""
from __future__ import annotations

from typing import Any

import httpx


def list_worker_nodes(
    client: httpx.Client, group: str | None = None
) -> list[dict[str, Any]]:
    """List all worker nodes, optionally filtered by group."""
    resp = client.get("/api/v1/master/workers", params={"product": "stream"})
    resp.raise_for_status()
    items = resp.json().get("items", [])
    nodes = []
    for w in items:
        if group and w.get("group") != group:
            continue
        info = w.get("info", {})
        cribl = info.get("cribl", {})
        nodes.append({
            "id": w.get("id", ""),
            "status": w.get("status", ""),
            "group": w.get("group", ""),
            "hostname": info.get("hostname", ""),
            "cpus": info.get("cpus", 0),
            "totalmem": info.get("totalmem", 0),
            "platform": info.get("platform", ""),
            "version": cribl.get("version", ""),
        })
    return nodes


def list_worker_groups(client: httpx.Client) -> Any:
    """List all worker groups."""
    resp = client.get("/api/v1/master/groups")
    resp.raise_for_status()
    return resp.json()


def get_worker_group(client: httpx.Client, group_id: str) -> Any:
    """Get a specific worker group by ID."""
    resp = client.get(f"/api/v1/master/groups/{group_id}")
    resp.raise_for_status()
    return resp.json()


def deploy_group(client: httpx.Client, group: str) -> Any:
    """Deploy configuration to a worker group.

    Resolves the current configVersion via the ``/configVersion`` endpoint
    (returns the compound ``shortcommit-hash`` form required by deploy).
    """
    cv_resp = client.get(f"/api/v1/master/groups/{group}/configVersion")
    cv_resp.raise_for_status()
    cv_items = cv_resp.json().get("items", [])
    config_version = cv_items[0] if cv_items else ""

    resp = client.patch(
        f"/api/v1/master/groups/{group}/deploy",
        json={"version": config_version},
    )
    resp.raise_for_status()
    return resp.json()
