"""Worker group management endpoints."""
from __future__ import annotations

from typing import Any

import httpx


def get_group_types(client: httpx.Client) -> dict[str, str]:
    """Map each worker group / edge fleet id to its product type.

    Types are ``stream``, ``edge``, ``search`` or ``outpost``. Returns an empty
    dict if the groups endpoint is unavailable; callers treat that as "don't
    filter" so a transient failure degrades to an unfiltered list rather than
    silently reporting zero nodes.
    """
    try:
        resp = client.get("/api/v1/master/groups")
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except Exception:
        return {}
    return {g["id"]: g.get("type", "stream") for g in items if g.get("id")}


def list_nodes(
    client: httpx.Client,
    group: str | None = None,
    product_types: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """List connected nodes, optionally narrowed to a group and product type.

    The leader ignores the ``?product=`` query param on ``/master/workers`` — it
    returns every node whatever value is passed — so a node's product is
    resolved from the type of the group it reports into.
    """
    resp = client.get("/api/v1/master/workers")
    resp.raise_for_status()
    items = resp.json().get("items", [])
    group_types = get_group_types(client) if product_types else {}
    nodes = []
    for w in items:
        grp = w.get("group", "")
        if group and grp != group:
            continue
        if product_types and group_types and group_types.get(grp) not in product_types:
            continue
        info = w.get("info", {})
        cribl = info.get("cribl", {})
        nodes.append({
            "id": w.get("id", ""),
            "status": w.get("status", ""),
            "group": grp,
            "hostname": info.get("hostname", ""),
            "cpus": info.get("cpus", 0),
            "totalmem": info.get("totalmem", 0),
            "platform": info.get("platform", ""),
            "version": cribl.get("version", ""),
            "distMode": cribl.get("distMode", ""),
        })
    return nodes


def list_all_nodes(
    client: httpx.Client, group: str | None = None
) -> list[dict[str, Any]]:
    """List every connected node regardless of product type."""
    return list_nodes(client, group=group)


def list_worker_nodes(
    client: httpx.Client, group: str | None = None
) -> list[dict[str, Any]]:
    """List Stream worker nodes, optionally filtered by group."""
    return list_nodes(client, group=group, product_types=("stream",))


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
