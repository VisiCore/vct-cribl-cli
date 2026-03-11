"""Edge node operations including system info, file inspection, and metrics."""
from __future__ import annotations

import time as _time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx


def list_edge_nodes(
    client: httpx.Client, fleet: str | None = None
) -> list[dict[str, Any]]:
    """List all edge nodes, optionally filtered by fleet/group."""
    resp = client.get("/api/v1/master/workers", params={"product": "edge"})
    resp.raise_for_status()
    items = resp.json().get("items", [])
    nodes = []
    for w in items:
        if fleet and w.get("group") != fleet:
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
            "distMode": cribl.get("distMode", ""),
        })
    return nodes


def find_edge_node(
    client: httpx.Client, name_or_id: str
) -> dict[str, Any] | None:
    """Find an edge node by hostname or ID."""
    all_nodes = list_edge_nodes(client)
    for n in all_nodes:
        if (
            n["id"] == name_or_id
            or n["hostname"] == name_or_id
            or n["hostname"].lower() == name_or_id.lower()
        ):
            return n
    return None


def get_system_info(client: httpx.Client, node_id: str) -> Any:
    """Get system information for an edge node."""
    resp = client.get(
        f"/api/v1/w/{quote(node_id, safe='')}/system/info",
        params={"fields": "os"},
    )
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", [])
    return items[0] if items else data


def get_inputs(client: httpx.Client, node_id: str) -> Any:
    """Get inputs configured on an edge node."""
    resp = client.get(f"/api/v1/w/{quote(node_id, safe='')}/system/inputs")
    resp.raise_for_status()
    return resp.json()


def get_outputs(client: httpx.Client, node_id: str) -> Any:
    """Get outputs configured on an edge node."""
    resp = client.get(f"/api/v1/w/{quote(node_id, safe='')}/system/outputs")
    resp.raise_for_status()
    return resp.json()


def file_inspect(client: httpx.Client, node_id: str, path: str) -> Any:
    """Inspect a file on an edge node (stat, hashes, head, hexdump)."""
    resp = client.get(
        f"/api/v1/w/{quote(node_id, safe='')}/edge/fileinspect",
        params={"path": path},
    )
    resp.raise_for_status()
    return resp.json()


def file_ls(
    client: httpx.Client,
    node_id: str,
    path: str = "/",
    stats: bool = False,
) -> Any:
    """List files on an edge node."""
    params: dict[str, Any] = {}
    if stats:
        params["stats"] = True
    resp = client.get(
        f"/api/v1/w/{quote(node_id, safe='')}/edge/ls{path}",
        params=params,
    )
    resp.raise_for_status()
    return resp.json()


def file_search(
    client: httpx.Client,
    node_id: str,
    path: str,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Any:
    """Search files on an edge node."""
    resp = client.post(
        f"/api/v1/w/{quote(node_id, safe='')}/edge/search/file",
        json={
            "file": path,
            "offset": offset,
            "limit": limit,
            "et": 0,
            "query": query or "",
            "rulesets": [],
        },
    )
    resp.raise_for_status()
    return resp.json()


def list_worker_logs(client: httpx.Client, node_id: str) -> Any:
    """List Cribl log files on a worker/hybrid node."""
    resp = client.get(f"/api/v1/w/{quote(node_id, safe='')}/system/logs")
    resp.raise_for_status()
    return resp.json()


def search_worker_log(
    client: httpx.Client,
    node_id: str,
    log_id: str,
    filter_str: str | None = None,
    limit: int = 50,
    offset: str | None = None,
) -> Any:
    """Search a specific Cribl log file on a worker/hybrid node."""
    params: dict[str, Any] = {"limit": limit}
    if filter_str:
        params["filter"] = filter_str
    if offset:
        params["offset"] = offset
    resp = client.get(
        f"/api/v1/w/{quote(node_id, safe='')}/system/logs/{quote(log_id, safe='')}",
        params=params,
    )
    resp.raise_for_status()
    return resp.json()


def is_edge_node(node: dict[str, Any]) -> bool:
    """Check whether a node is a managed-edge node."""
    return node.get("distMode") == "managed-edge"


def get_node_metrics(
    client: httpx.Client, node_id: str, duration_seconds: int = 3600
) -> list[dict[str, Any]]:
    """Get historical metrics (CPU, memory, disk, load) for a node."""
    now = int(_time.time())
    earliest = now - duration_seconds
    resp = client.get(
        f"/api/v1/w/{quote(node_id, safe='')}/system/metrics",
        params={"earliest": earliest, "latest": now},
    )
    resp.raise_for_status()
    data = resp.json()
    entries = data.get("results", {}).get("metrics", [])
    points = []
    for e in entries:
        cpu = _metric_val(e, "system.cpu_perc")
        if cpu is None:
            continue
        time_arr = e.get("_time", [])
        ts = time_arr[0].get("val", 0) if time_arr else 0
        free_mem = _metric_val(e, "system.free_mem")
        total_mem = _metric_val(e, "system.total_mem")
        disk_used = _metric_val(e, "system.disk_used")
        total_disk = _metric_val(e, "system.total_disk")
        load_avg = _metric_val(e, "system.load_avg")
        mem_used = (total_mem - free_mem) if total_mem is not None and free_mem is not None else None
        points.append({
            "time": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
            "cpu_perc": cpu,
            "mem_used_bytes": mem_used,
            "mem_total_bytes": total_mem,
            "mem_used_pct": (mem_used / total_mem * 100) if mem_used is not None and total_mem and total_mem > 0 else None,
            "disk_used_bytes": disk_used,
            "disk_total_bytes": total_disk,
            "disk_used_pct": (disk_used / total_disk * 100) if disk_used is not None and total_disk and total_disk > 0 else None,
            "load_avg": load_avg,
        })
    return points


def _metric_val(entry: dict, key: str) -> float | None:
    arr = entry.get(key)
    if isinstance(arr, list) and arr:
        return arr[0].get("val")
    return None
