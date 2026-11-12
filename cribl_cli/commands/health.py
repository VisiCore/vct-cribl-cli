"""Health check command — surfaces Red/Yellow sources and destinations."""
from __future__ import annotations

import json as _json
import re
import sys
from collections import Counter
import time as _time
from urllib.parse import quote
from datetime import datetime, timezone

import click
import httpx

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoint_factory import EndpointConfig, create_endpoints
from cribl_cli.api.endpoints.edge_nodes import (
    get_node_metrics,
    list_worker_logs,
    metrics_coverage,
    search_worker_log,
)
from cribl_cli.api.endpoints.system import get_system_info
from cribl_cli.api.endpoints.version import get_version_status
from cribl_cli.api.endpoints.workers import list_all_nodes, list_worker_groups
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.concurrency import map_concurrent
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.group_resolver import resolve_group


@click.group("health", help="Check health of sources, destinations, and system.")
def health_group():
    pass


def _check_items(client, url: str, label: str) -> list[dict]:
    resp = client.get(url)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", [])
    problems = []
    for item in items:
        if item.get("disabled"):
            continue
        status = item.get("status", {})
        if not isinstance(status, dict):
            continue
        health = status.get("health", "")
        if health in ("Red", "Yellow", "Error"):
            metrics = status.get("metrics", {})
            problems.append({
                "id": item.get("id", "?"),
                "type": item.get("type", "?"),
                "health": health,
                "message": status.get("message", ""),
                "metrics": {k: v for k, v in metrics.items() if v} if metrics else {},
            })
    return problems


UNHEALTHY = ("Red", "Yellow", "Error")
_KINDS = (("source", "system/inputs"), ("destination", "system/outputs"))
# Above this many nodes the per-node breakdown is skipped unless asked for:
# it costs two requests per node.
_NODE_DETAIL_MAX = 20


def _health_of(item: dict) -> str:
    status = item.get("status")
    return status.get("health", "") if isinstance(status, dict) else ""


_INIT_BOILERPLATE = (
    ", please check your configuration, or ensure that your Worker is on the same version as the Leader"
)


def _error_text(error) -> str:
    """Flatten a status ``error`` object into one line: message, cause, hint."""
    if not isinstance(error, dict):
        return str(error) if error else ""
    msg = str(error.get("message") or "")
    # Drop Cribl's generic advice; the cause that follows is the useful part.
    msg = msg.replace(_INIT_BOILERPLATE, "")
    details = error.get("details")
    inner = details.get("error") if isinstance(details, dict) else None
    cause = str((inner.get("message") if isinstance(inner, dict) else inner) or "")
    hint = str(inner.get("hint") or "") if isinstance(inner, dict) else ""
    # Skip a cause the message already quotes ("Initialization error: bind EACCES ...").
    text = msg if (not cause or cause in msg) else (f"{msg}: {cause}" if msg else cause)
    return f"{text} ({hint})" if hint else text


def _status_reason(status) -> str:
    """Why an input/output is unhealthy, from a node's own status.

    The reason is either on the item itself (``status.error``) or on one of its
    parts under ``status.metrics.items`` — a listener such as "UDP 0.0.0.0:514"
    or a downstream host such as "splunk.example.com:9997".
    """
    if not isinstance(status, dict):
        return ""
    reasons: list[str] = []
    own = _error_text(status.get("error"))
    if own:
        reasons.append(own)
    metrics = status.get("metrics")
    parts = metrics.get("items") if isinstance(metrics, dict) else None
    for part in parts if isinstance(parts, list) else []:
        sub = part.get("status") if isinstance(part, dict) else None
        if not isinstance(sub, dict) or sub.get("health") not in UNHEALTHY:
            continue
        name = " ".join(str(part[k]) for k in ("name", "address") if part.get(k)) or "part"
        text = _error_text(sub.get("error")) or sub["health"]
        reasons.append(f"{name}: {text}")
    if not reasons:
        # No error recorded (typical for Yellow): fall back to parts that have
        # counted send errors, e.g. one endpoint of a load-balanced destination.
        for part in parts if isinstance(parts, list) else []:
            sub = part.get("status") if isinstance(part, dict) else None
            sub_metrics = sub.get("metrics") if isinstance(sub, dict) else None
            count = sub_metrics.get("errorCount") if isinstance(sub_metrics, dict) else None
            if count:
                reasons.append(f"{part.get('name', 'part')}: {count} send error(s)")
    return "; ".join(reasons)[:300]


def _per_node_health(client, nodes: list[dict], path: str) -> tuple[dict, list[str]]:
    """Ask each node for its own view of the group's inputs or outputs.

    The leader's list reports the worst health across nodes, but not which
    nodes and not why; the node's own status has both. Returns
    ``({item_id: {hostname: {"health", "reason"}}}, [unreadable hostnames])``.
    """
    def fetch(node):
        resp = client.get(f"/api/v1/w/{quote(node['id'], safe='')}/{path}")
        resp.raise_for_status()
        return resp.json().get("items", [])

    by_item: dict[str, dict[str, str]] = {}
    unreachable: list[str] = []
    for node, items, err in map_concurrent(fetch, nodes):
        host = node["hostname"] or node["id"]
        if err is not None:
            unreachable.append(host)
            continue
        for item in items:
            if isinstance(item, dict) and not item.get("disabled"):
                by_item.setdefault(item.get("id", "?"), {})[host] = {
                    "health": _health_of(item) or "?",
                    "reason": _status_reason(item.get("status")),
                }
    return by_item, unreachable


def check_group(client, group: str, nodes: list[dict], *, node_detail: bool | None = None) -> dict:
    """Check one group's sources and destinations.

    Returns ``{group, nodes, healthy, summary, unhealthy, items, warnings}``.
    With no connected nodes nothing is running the config, so the leader's
    statuses are placeholders (the UI shows these as "No Metrics"): they are
    counted as ``no_metrics`` and ``healthy`` is None rather than True.

    ``node_detail``: None = per-node breakdown for groups up to
    ``_NODE_DETAIL_MAX`` nodes, True = always, False = never.
    """
    has_nodes = len(nodes) > 0
    warnings: list[str] = []
    if not has_nodes:
        warnings.append(
            f"Group '{group}' has no connected nodes, so nothing is running this config. "
            "Its sources and destinations have no health data (the UI shows them as "
            "\"No Metrics\"); this is not a healthy result."
        )

    summary: dict[str, dict[str, int]] = {}
    unhealthy: list[dict] = []
    all_items: list[dict] = []
    fetched: dict[str, list[dict]] = {}
    for kind, path in _KINDS:
        resp = client.get(f"/api/v1/m/{group}/{path}")
        resp.raise_for_status()
        items = [i for i in resp.json().get("items", []) if isinstance(i, dict)]
        fetched[kind] = items
        counts = {"total": len(items), "disabled": 0, "healthy": 0, "warning": 0, "critical": 0, "no_metrics": 0}
        for item in items:
            if item.get("disabled"):
                counts["disabled"] += 1
                continue
            health = _health_of(item) if has_nodes else ""
            if has_nodes and not health and item.get("type") == "default":
                # The "Default" destination is only a pointer to another one and
                # has no status of its own; the UI counts it as healthy.
                health = "Green"
            if health == "Green":
                counts["healthy"] += 1
            elif health == "Yellow":
                counts["warning"] += 1
            elif health in ("Red", "Error"):
                counts["critical"] += 1
            else:
                counts["no_metrics"] += 1
            status = item.get("status") if isinstance(item.get("status"), dict) else {}
            row = {
                "group": group,
                "kind": kind,
                "id": item.get("id", "?"),
                "type": item.get("type", "?"),
                "health": health or "No Metrics",
            }
            all_items.append(row)
            if health in UNHEALTHY:
                metrics = status.get("metrics") or {}
                unhealthy.append({
                    **row,
                    "message": status.get("message", ""),
                    "metrics": {k: v for k, v in metrics.items() if v},
                })
        summary[f"{kind}s"] = counts

    # Saved collectors: the UI lists them with sources, always as "No Metrics"
    # (they run as jobs and have no standing health).
    try:
        resp = client.get(f"/api/v1/m/{group}/lib/jobs")
        resp.raise_for_status()
        jobs = resp.json().get("items", [])
        summary["collectors"] = {"total": sum(1 for j in jobs if isinstance(j, dict) and j.get("type") == "collection")}
    except Exception:  # noqa: BLE001 -- informational only (fleets have none)
        summary["collectors"] = {"total": 0}

    # Which nodes is each problem on? (worst-of-all-nodes alone cannot say.)
    if unhealthy and has_nodes:
        if node_detail is False:
            pass
        elif node_detail is None and len(nodes) > _NODE_DETAIL_MAX:
            warnings.append(
                f"Per-node breakdown skipped: '{group}' has {len(nodes)} nodes "
                f"(limit {_NODE_DETAIL_MAX}). Pass --by-node to fetch it anyway."
            )
        else:
            _attach_node_detail(client, nodes, unhealthy, warnings)

    return {
        "group": group,
        "nodes": len(nodes),
        "healthy": (not unhealthy) if has_nodes else None,
        "summary": summary,
        "unhealthy": unhealthy,
        "items": all_items,
        "warnings": warnings,
    }


def _attach_node_detail(client, nodes: list[dict], unhealthy: list[dict], warnings: list[str]) -> None:
    unreachable: set[str] = set()
    for kind, path in _KINDS:
        rows = [r for r in unhealthy if r["kind"] == kind]
        if not rows:
            continue
        by_item, failed = _per_node_health(client, nodes, path)
        unreachable.update(failed)
        for row in rows:
            per_node = by_item.get(row["id"], {})
            affected = sorted(h for h, v in per_node.items() if v["health"] in UNHEALTHY)
            row["nodes_total"] = len(nodes)
            row["nodes_affected"] = affected
            row["node_health"] = {h: v["health"] for h, v in sorted(per_node.items())}
            reasons = [per_node[h]["reason"] for h in affected if per_node[h]["reason"]]
            if reasons and not row.get("message"):
                # Most common reason first; note when nodes disagree.
                top, n = Counter(reasons).most_common(1)[0]
                row["message"] = top + (f" (+{len(set(reasons)) - 1} other reason(s))" if len(set(reasons)) > 1 else "")
            if not affected and per_node and not unreachable:
                row["message"] = row.get("message") or (
                    f"The leader reports {row['health']}, but all {len(per_node)} node(s) "
                    "report this item healthy. Check it in the UI."
                )
    if unreachable:
        warnings.append(
            "Could not read per-node status from: " + ", ".join(sorted(unreachable))
            + " (try a higher --timeout)."
        )


def _affected(row: dict) -> str:
    if "nodes_total" not in row:
        return ""
    hosts = row.get("nodes_affected", [])
    label = f"{len(hosts)}/{row['nodes_total']}"
    if hosts and len(hosts) < row["nodes_total"]:
        label += ": " + ", ".join(hosts)
    return label


@health_group.command("check", help="Show unhealthy sources and destinations.")
@click.option("-g", "--group", default=None, help="Worker group or fleet (default: the first group listed).")
@click.option("--all-groups", is_flag=True, help="Check every group that has connected nodes.")
@click.option("--all", "show_all", is_flag=True, help="List every active item with its health, not just unhealthy ones.")
@click.option("--summary", "as_summary", is_flag=True,
              help="Output per-group counts, node count and warnings along with the unhealthy items.")
@click.option("--by-node/--no-by-node", "by_node", default=None,
              help="Show which nodes each problem is on (default: on for groups of up to "
                   f"{_NODE_DETAIL_MAX} nodes).")
@click.option("--fail-on-unhealthy", is_flag=True,
              help="Exit 2 if anything is unhealthy, 3 if a checked group has no connected nodes.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def health_check(group, all_groups, show_all, as_summary, by_node, fail_on_unhealthy, use_table):
    """Check health of sources and destinations in a worker group or fleet.

    Prints a JSON list of unhealthy items ([] when there are none); notes go
    to stderr. Each item says which nodes it is unhealthy on (nodes_affected).
    Health is the worst state across the group's nodes, the same as the
    Critical / Warning counts in the UI.

    A group with no connected nodes has no health data: that is reported as a
    warning, never as healthy. Use --summary for counts per group, and
    --fail-on-unhealthy to get a non-zero exit code for scripts.
    """
    try:
        client = get_client()
        # Like the UI, only count nodes that are currently connected.
        all_nodes = [n for n in list_all_nodes(client) if not n.get("disconnected")]

        if all_groups:
            if group:
                raise click.UsageError("Pass either -g/--group or --all-groups, not both.")
            with_nodes = {n["group"] for n in all_nodes}
            listed = [g.get("id") for g in list_worker_groups(client).get("items", [])]
            targets = [g for g in listed if g in with_nodes]
            skipped = len(listed) - len(targets)
            if skipped:
                click.echo(f"Skipping {skipped} group(s) with no connected nodes.", err=True)
        else:
            if not group:
                group = resolve_group(client, None)
                click.echo(f"No -g given; checking '{group}'.", err=True)
            targets = [group]

        results = [
            check_group(client, g, [n for n in all_nodes if n["group"] == g], node_detail=by_node)
            for g in targets
        ]

        for res in results:
            for w in res["warnings"]:
                click.echo(f"Warning: {w}", err=True)

        unhealthy = [row for res in results for row in res["unhealthy"]]

        if as_summary:
            payload = [{k: v for k, v in res.items() if k != "items"} for res in results]
            out = payload if all_groups else payload[0]
            if use_table:
                rows = [
                    {
                        "group": r["group"], "nodes": r["nodes"],
                        "healthy": {True: "yes", False: "NO", None: "no data"}[r["healthy"]],
                        **{f"{short}_{c}": r["summary"][k][c]
                           for k, short in (("sources", "src"), ("destinations", "dst"))
                           for c in ("critical", "warning", "healthy", "no_metrics", "disabled")},
                    }
                    for r in payload
                ]
                click.echo(format_output(rows, table=True))
            else:
                click.echo(format_output(out))
        elif show_all:
            rows = [row for res in results for row in res["items"]]
            click.echo(format_output(rows, table=use_table))
        elif use_table:
            # A status message is rare; show the column only when one exists.
            show_message = any(r.get("message") for r in unhealthy)
            table_data = [
                {
                    **({"group": r["group"]} if all_groups else {}),
                    "kind": r["kind"],
                    "id": r["id"],
                    "type": r["type"],
                    "health": r["health"],
                    "nodes": _affected(r),
                    **({"message": r.get("message", "")} if show_message else {}),
                }
                for r in unhealthy
            ]
            click.echo(format_output(table_data, table=True) if table_data else "(nothing unhealthy)")
        else:
            click.echo(format_output(unhealthy))

        # One-line verdict per group, on stderr so stdout stays parseable.
        for res in results:
            if res["healthy"] is None:
                continue
            s, d = res["summary"]["sources"], res["summary"]["destinations"]
            bad = len(res["unhealthy"])
            verdict = "all healthy" if not bad else f"{bad} unhealthy"
            click.echo(
                f"{res['group']}: {verdict} "
                f"({s['total'] - s['disabled']} active sources, "
                f"{d['total'] - d['disabled']} active destinations, {res['nodes']} node(s)).",
                err=True,
            )

        if fail_on_unhealthy:
            if unhealthy:
                sys.exit(2)
            if any(res["healthy"] is None for res in results):
                sys.exit(3)
    except click.UsageError:
        raise
    except Exception as e:
        handle_error(e)


# ---------------------------------------------------------------------------
# health report — comprehensive environment health snapshot
# ---------------------------------------------------------------------------

def _format_bytes(n: int | float) -> str:
    if n == 0:
        return "0 B"
    import math
    units = ["B", "KB", "MB", "GB", "TB"]
    i = int(n > 0 and min(len(units) - 1, int(math.log(abs(n), 1024))))
    return f"{n / (1024 ** i):.2f} {units[i]}"


def _node_memory(client, wid: str, total_mem: int) -> tuple[int, int, float | None]:
    """Return (total_mem, free_mem, mem_pct) for a node from its recent metrics.

    The worker list does not carry free memory, so it is read from the node's
    own metrics endpoint. Any failure degrades to "unknown" rather than raising.
    """
    try:
        metrics = get_node_metrics(client, wid, duration_seconds=300)
    except Exception:
        return total_mem, 0, None
    if not metrics:
        return total_mem, 0, None
    latest = metrics[-1]
    total_mem = latest.get("mem_total_bytes") or total_mem
    mem_used = latest.get("mem_used_bytes")
    if mem_used is None or not total_mem or total_mem <= 0:
        return total_mem, 0, None
    return total_mem, total_mem - mem_used, mem_used / total_mem * 100


def _fetch_all_nodes(client, group=None, with_memory: bool = True) -> list[dict]:
    """Fetch all nodes (edge + stream workers) with enriched health data.

    ``with_memory=False`` skips the per-node memory lookup for callers that do
    not report memory, so they never wait on a slow node for it.
    """
    now = _time.time()

    # One call covers every product: the leader ignores ?product= here.
    resp = client.get("/api/v1/master/workers")
    resp.raise_for_status()
    items = resp.json().get("items", [])

    all_nodes: list[dict] = []
    need_memory: list[dict] = []
    seen_ids: set[str] = set()
    for w in items:
        wid = w.get("id", "")
        if wid in seen_ids:
            continue
        seen_ids.add(wid)
        grp = w.get("group", "")
        if group and grp != group:
            continue
        info = w.get("info", {})
        cribl = info.get("cribl", {})
        hostname = info.get("hostname", wid)
        disconnected = w.get("disconnected", False)
        last_msg = w.get("lastMsgTime", 0) / 1000
        ago = now - last_msg if last_msg > 0 else 0

        if disconnected:
            hb_status = "DISCONNECTED"
        elif ago > 86400:
            hb_status = "MISSED"
        elif ago > 300:
            hb_status = "LATE"
        else:
            hb_status = "OK"

        total_disk = info.get("totalDiskSpace", 0)
        free_disk = info.get("freeDiskSpace", 0)
        disk_pct = ((total_disk - free_disk) / total_disk * 100) if total_disk > 0 else None

        total_mem = info.get("totalmem", 0)
        free_mem = info.get("freemem")
        mem_pct = None
        if free_mem:
            mem_pct = ((total_mem - free_mem) / total_mem * 100) if total_mem > 0 else None

        node = {
            "id": wid,
            "hostname": hostname,
            "group": grp,
            "status": w.get("status", "?"),
            "version": cribl.get("version", "?"),
            "cpus": info.get("cpus", 0),
            "total_mem": total_mem,
            "free_mem": free_mem or 0,
            "mem_pct": round(mem_pct, 1) if mem_pct is not None else None,
            "total_disk": total_disk,
            "free_disk": free_disk,
            "disk_pct": round(disk_pct, 1) if disk_pct is not None else None,
            "heartbeat": hb_status,
            "disconnected": disconnected,
            "platform": info.get("platform", ""),
        }
        all_nodes.append(node)
        if with_memory and not free_mem:
            need_memory.append(node)

    # freemem is not in the worker list — read it from each node, in parallel
    # (one slow node used to hold up every node behind it).
    for node, result, _err in map_concurrent(
        lambda n: _node_memory(client, n["id"], n["total_mem"]), need_memory
    ):
        total_mem, free_mem, mem_pct = result
        node["total_mem"] = total_mem
        node["free_mem"] = free_mem
        node["mem_pct"] = round(mem_pct, 1) if mem_pct is not None else None
    return all_nodes


def _fetch_unhealthy_io(client, groups, nodes=None) -> list[dict]:
    """Unhealthy sources and destinations across groups, with nodes and reasons.

    Uses the same check as ``health check``. Only groups with connected nodes
    are checked: a group nothing is running has no health data to report.
    """
    connected = [n for n in (nodes or []) if not n.get("disconnected")]
    results = []
    for g in groups:
        gid = g.get("id", "")
        if g.get("type", "") in ("search", "outpost"):
            continue
        group_nodes = [n for n in connected if n.get("group") == gid]
        if nodes is not None and not group_nodes:
            continue
        try:
            results.extend(check_group(client, gid, group_nodes)["unhealthy"])
        except Exception:
            continue
    return results


def _scan_node_errors(client, node: dict, limit: int, query: str | None = None) -> list[dict]:
    """Return up to *limit* error-level log entries from one node's cribl.log.

    With no *query* the search term is "error" and only error/warn/crit/fatal
    entries are kept; a custom *query* keeps every match.
    """
    node_id = node["id"]
    hostname = node["hostname"] or node_id
    logs_data = list_worker_logs(client, node_id)
    log_items = logs_data.get("items", []) if isinstance(logs_data, dict) else []

    # Prefer worker/0/cribl.log (has more detail), fall back to cribl.log
    log_id = "cribl.log"
    for log in log_items:
        lid = log.get("id", "") if isinstance(log, dict) else str(log)
        if lid == "worker/0/cribl.log":
            log_id = lid
            break

    # Fetch more than the limit so there is room to filter by level
    data = search_worker_log(client, node_id, log_id, query or "error", limit * 3)
    items = data.get("items", []) if isinstance(data, dict) else []
    found: list[dict] = []
    for result in items:
        events = result.get("events", []) if isinstance(result, dict) else []
        for ev in events:
            if len(found) >= limit:
                return found
            level = ev.get("level", ev.get("severity", ""))
            if not query and level not in ("error", "warn", "crit", "fatal"):
                continue
            msg = ev.get("message", ev.get("_raw", "")) or ""
            found.append({
                "node": hostname,
                "group": node["group"],
                "level": level,
                "channel": ev.get("channel", ""),
                "time": ev.get("time", ev.get("_time", ev.get("timestamp", ""))),
                "message": msg[:200],
            })
    return found


def scan_errors(client, nodes, limit_per_node, query: str | None = None) -> list[dict]:
    """Scan internal logs for errors across nodes, concurrently.

    A node that cannot be read contributes one ``fetch_error`` row instead of
    failing the whole scan.
    """
    all_errors: list[dict] = []
    for node, result, err in map_concurrent(
        lambda n: _scan_node_errors(client, n, limit_per_node, query), nodes
    ):
        if err is not None:
            all_errors.append({
                "node": node["hostname"] or node["id"],
                "group": node["group"],
                "level": "fetch_error",
                "channel": "",
                "time": "",
                "message": str(err)[:200],
            })
        else:
            all_errors.extend(result)
    return all_errors


def _fetch_error_summary(client, nodes, limit_per_node) -> list[dict]:
    """Scan internal logs for errors across nodes."""
    return scan_errors(client, nodes, limit_per_node)


def _version_key(version: str) -> tuple[int, ...]:
    """Numeric sort key for a Cribl version ("4.10.0-abc123" -> (4, 10, 0)).

    Plain string comparison ranks "4.9.3" above "4.10.0"; unparseable
    versions sort lowest.
    """
    m = re.match(r"\d+(?:\.\d+)*", version or "")
    return tuple(int(p) for p in m.group(0).split(".")) if m else ()


def _build_version_summary(nodes) -> dict:
    """Group nodes by version and flag mismatches."""
    by_version: dict[str, list[str]] = {}
    for n in nodes:
        v = n.get("version", "?")
        by_version.setdefault(v, []).append(n["hostname"])
    versions_sorted = sorted(by_version.keys(), key=lambda v: (_version_key(v), v), reverse=True)
    latest = versions_sorted[0] if versions_sorted else "?"
    needs_upgrade = []
    for n in nodes:
        if n.get("version", "?") != latest:
            needs_upgrade.append({
                "hostname": n["hostname"],
                "version": n["version"],
                "group": n["group"],
            })
    return {
        "versions": {v: by_version[v] for v in versions_sorted},
        "latest": latest,
        "mismatch": len(by_version) > 1,
        "nodes_needing_upgrade": needs_upgrade,
    }


def _build_capacity_alerts(nodes) -> list[dict]:
    """Flag nodes with resource issues."""
    alerts = []
    for n in nodes:
        hostname = n["hostname"]
        grp = n["group"]
        disk_pct = n.get("disk_pct")
        mem_pct = n.get("mem_pct")

        if n.get("heartbeat") in ("DISCONNECTED", "MISSED"):
            alerts.append({
                "hostname": hostname,
                "group": grp,
                "alert": n["heartbeat"].lower(),
                "severity": "CRITICAL",
                "detail": f"node {n['heartbeat'].lower()}",
            })

        if disk_pct is not None:
            if disk_pct >= 90:
                alerts.append({
                    "hostname": hostname, "group": grp, "alert": "disk",
                    "severity": "CRITICAL",
                    "detail": f"disk at {disk_pct:.0f}% ({_format_bytes(n['free_disk'])} free)",
                })
            elif disk_pct >= 80:
                alerts.append({
                    "hostname": hostname, "group": grp, "alert": "disk",
                    "severity": "WARNING",
                    "detail": f"disk at {disk_pct:.0f}% ({_format_bytes(n['free_disk'])} free)",
                })

        if mem_pct is not None:
            if mem_pct >= 90:
                alerts.append({
                    "hostname": hostname, "group": grp, "alert": "memory",
                    "severity": "CRITICAL",
                    "detail": f"memory at {mem_pct:.0f}%",
                })
            elif mem_pct >= 80:
                alerts.append({
                    "hostname": hostname, "group": grp, "alert": "memory",
                    "severity": "WARNING",
                    "detail": f"memory at {mem_pct:.0f}%",
                })
    return alerts


def _format_text_report(report: dict) -> str:
    """Format the health report as human-readable text."""
    lines: list[str] = []
    ts = report["timestamp"]
    summary = report["summary"]

    lines.append(f"Cribl Health Report — {ts}")
    lines.append("=" * 70)
    lines.append("")
    healthy = summary["healthy_nodes"]
    total = summary["total_nodes"]
    alert_count = summary["capacity_alerts"]
    lines.append(
        f"Summary: {summary['total_groups']} groups | "
        f"{total} nodes ({healthy} healthy) | "
        f"{alert_count} alert(s)"
    )

    # Node Health
    lines.append("")
    lines.append("--- Node Health " + "-" * 54)
    nodes = report["nodes"]
    if nodes:
        hdr = f"  {'HOSTNAME':<38} {'GROUP':<20} {'STATUS':<10} {'VERSION':<14} {'DISK':>5} {'MEM':>5}"
        lines.append(hdr)
        for n in nodes:
            disk_s = f"{n['disk_pct']:.0f}%" if n.get("disk_pct") is not None else "?"
            mem_s = f"{n['mem_pct']:.0f}%" if n.get("mem_pct") is not None else "?"
            flag = ""
            if n.get("disk_pct") is not None and n["disk_pct"] >= 90:
                flag = " [!!]"
            elif n.get("disk_pct") is not None and n["disk_pct"] >= 80:
                flag = " [!]"
            lines.append(
                f"  {n['hostname']:<38} {n['group']:<20} {n['status']:<10} "
                f"{n['version']:<14} {disk_s:>5} {mem_s:>5}{flag}"
            )
    else:
        lines.append("  No nodes found.")

    # Capacity Alerts
    alerts = report["capacity_alerts"]
    lines.append("")
    lines.append("--- Capacity Alerts " + "-" * 50)
    if alerts:
        for a in alerts:
            lines.append(f"  {a['severity']:<9} {a['hostname']:<38} {a['detail']} ({a['group']})")
    else:
        lines.append("  No alerts.")

    # Version Summary
    vs = report["version_summary"]
    lines.append("")
    lines.append("--- Version Summary " + "-" * 50)
    for ver, hosts in vs["versions"].items():
        label = " (latest)" if ver == vs["latest"] else " [upgrade recommended]"
        if len(hosts) <= 5:
            host_list = ", ".join(hosts)
            lines.append(f"  {ver}: {len(hosts)} node(s) — {host_list}{label}")
        else:
            lines.append(f"  {ver}: {len(hosts)} node(s){label}")

    # Unhealthy IO
    io_items = report["unhealthy_io"]
    lines.append("")
    lines.append("--- Unhealthy Sources & Destinations " + "-" * 33)
    if io_items:
        for item in io_items:
            kind_s = "source" if item["kind"] == "source" else "dest  "
            lines.append(
                f"  [{item['group']}] {kind_s} {item['id']} ({item['type']})  {item['health']}"
            )
            if item.get("message"):
                where = _affected(item)
                lines.append(f"      {where + ' — ' if where else ''}{item['message'][:110]}")
    else:
        lines.append("  All sources and destinations are healthy.")

    # Errors
    if "errors" in report:
        errors = report["errors"]
        lines.append("")
        lines.append("--- Top Errors " + "-" * 55)
        if errors:
            for e in errors:
                lines.append(
                    f"  {e['node']:<38} {e['level']:<6} {e['channel']:<40} "
                    f'"{e["message"][:80]}"'
                )
        else:
            lines.append("  No errors found.")
    else:
        lines.append("")
        lines.append("  (error scanning skipped — use without --skip-errors to include)")

    lines.append("")
    return "\n".join(lines)


def _fetch_leader_info(client) -> dict:
    """Fetch leader node system info: version, uptime, resources, notifications."""
    try:
        data = get_system_info(client)
        # API returns {items: [info_obj]} — unwrap it
        if isinstance(data, dict) and "items" in data:
            items = data.get("items", [])
            info = items[0] if items else {}
        else:
            info = data if isinstance(data, dict) else {}

        build = info.get("BUILD", info.get("build", {}))
        uptime_secs = info.get("uptime", 0)
        memory = info.get("memory", {})
        disk = info.get("diskUsage", {})

        # Extract notification messages (active alerts from the system)
        messages = info.get("messages", [])
        notifications = []
        for msg in messages:
            if isinstance(msg, dict):
                notifications.append({
                    "severity": msg.get("severity", "info"),
                    "text": (msg.get("text", msg.get("message", "")) or "")[:200],
                    "id": msg.get("id", ""),
                })

        return {
            "hostname": info.get("hostname", ""),
            "version": build.get("VERSION", build.get("version", "?")),
            "branch": build.get("BRANCH", ""),
            "build_timestamp": build.get("TIMESTAMP", ""),
            "uptime_seconds": uptime_secs,
            "uptime_days": round(uptime_secs / 86400, 1) if uptime_secs else 0,
            "total_mem": memory.get("total", 0),
            "free_mem": memory.get("free", 0),
            "mem_pct": round((1 - memory["free"] / memory["total"]) * 100, 1) if memory.get("total") else None,
            "total_disk": disk.get("totalDiskSize", 0),
            "free_disk": disk.get("bytesAvailable", 0),
            "disk_pct": round(disk["bytesUsed"] / disk["totalDiskSize"] * 100, 1) if disk.get("totalDiskSize") else None,
            "load_avg": info.get("loadavg", []),
            "cpus": len(info.get("cpus", [])),
            "worker_processes": info.get("workerProcesses", 0),
            "notifications": notifications,
        }
    except Exception:
        return {}


def _fetch_license_info(client) -> dict:
    """Fetch license quota and expiration."""
    try:
        config = EndpointConfig(scope="global", path="system/licenses")
        endpoints = create_endpoints(config)
        data = endpoints.list(client, group="_global_")
        items = data.get("items", []) if isinstance(data, dict) else []
        if not items:
            return {}
        lic = items[0] if isinstance(items[0], dict) else {}
        exp = lic.get("exp", lic.get("expiration", 0))
        exp_date = ""
        if exp:
            try:
                exp_date = datetime.fromtimestamp(exp, tz=timezone.utc).strftime("%Y-%m-%d")
            except Exception:
                pass
        return {
            "quota_gb_per_day": lic.get("quota", 0),
            "license_class": lic.get("cls", lic.get("class", "?")),
            "expiration_epoch": exp,
            "expiration_date": exp_date,
        }
    except Exception:
        return {}


def _fetch_io_summary(client, groups, node_groups) -> dict:
    """Fetch source/destination health counts per active group."""
    summary = {}
    for g in groups:
        gid = g.get("id", "")
        gtype = g.get("type", "")
        if gtype in ("search", "outpost") or gid not in node_groups:
            continue
        group_summary = {"sources": {"total": 0, "active": 0, "disabled": 0, "green": 0, "red": 0, "yellow": 0},
                         "destinations": {"total": 0, "active": 0, "disabled": 0, "green": 0, "red": 0, "yellow": 0}}
        for kind, path in [("sources", "system/inputs"), ("destinations", "system/outputs")]:
            try:
                resp = client.get(f"/api/v1/m/{gid}/{path}")
                resp.raise_for_status()
                items = resp.json().get("items", [])
                for item in items:
                    group_summary[kind]["total"] += 1
                    if item.get("disabled"):
                        group_summary[kind]["disabled"] += 1
                        continue
                    group_summary[kind]["active"] += 1
                    status = item.get("status", {})
                    health = status.get("health", "") if isinstance(status, dict) else ""
                    if health == "Green":
                        group_summary[kind]["green"] += 1
                    elif health == "Red":
                        group_summary[kind]["red"] += 1
                    elif health == "Yellow":
                        group_summary[kind]["yellow"] += 1
            except Exception:
                continue
        summary[gid] = group_summary
    return summary


def _fetch_config_status(client, groups, node_groups) -> list[dict]:
    """Check for uncommitted config changes in active groups."""
    results = []
    for g in groups:
        gid = g.get("id", "")
        gtype = g.get("type", "")
        if gtype in ("search", "outpost") or gid not in node_groups:
            continue
        try:
            data = get_version_status(client, gid)
            if not isinstance(data, dict):
                continue
            # API returns {items: [status_obj]} — unwrap
            if "items" in data:
                items = data.get("items", [])
                status = items[0] if items else {}
            else:
                status = data
            modified = status.get("modified", [])
            not_added = status.get("not_added", [])
            created = status.get("created", [])
            deleted = status.get("deleted", [])
            conflicted = status.get("conflicted", [])
            total = len(modified) + len(not_added) + len(created) + len(deleted)
            if total > 0:
                results.append({
                    "group": gid,
                    "modified": len(modified),
                    "not_added": len(not_added),
                    "created": len(created),
                    "deleted": len(deleted),
                    "conflicted": len(conflicted),
                    "total_uncommitted": total,
                })
        except Exception:
            continue
    return results


@health_group.command("report", help="Comprehensive environment health report.")
@click.option("-g", "--group", default=None, help="Scope to a specific worker group.")
@click.option("--json", "as_json", is_flag=True, help="Output as structured JSON.")
@click.option("--skip-errors", is_flag=True, help="Skip log scanning (faster).")
@click.option("--error-limit", default=10, type=int, help="Max errors per node (default: 10).")
def health_report(group, as_json, skip_errors, error_limit):
    """Generate a comprehensive health report for the Cribl environment."""
    try:
        client = get_client()

        # 1. Fetch groups
        groups_data = list_worker_groups(client)
        groups = groups_data.get("items", [])
        if group:
            groups = [g for g in groups if g.get("id") == group]

        # Build group metadata lookup (infra tier, type)
        group_meta = {}
        for g in groups:
            gid = g.get("id", "")
            on_prem = g.get("onPrem", False)
            gtype = g.get("type", "stream")
            group_meta[gid] = {
                "id": gid,
                "type": gtype,
                "infra": "on-prem" if on_prem else "cloud",
                "description": g.get("description", ""),
                "isFleet": g.get("isFleet", False),
            }

        # 2. Fetch all nodes
        nodes = _fetch_all_nodes(client, group)
        # Enrich nodes with infra tier from group metadata
        for n in nodes:
            meta = group_meta.get(n.get("group", ""), {})
            n["infra"] = meta.get("infra", "unknown")
        healthy_nodes = sum(1 for n in nodes if n["status"] == "healthy" and n["heartbeat"] == "OK")

        # 3. Unhealthy sources & destinations
        unhealthy_io = _fetch_unhealthy_io(client, groups, nodes)
        # Enrich IO entries with infra tier
        for io in unhealthy_io:
            meta = group_meta.get(io.get("group", ""), {})
            io["infra"] = meta.get("infra", "unknown")
        unhealthy_sources = sum(1 for i in unhealthy_io if i["kind"] == "source")
        unhealthy_dests = sum(1 for i in unhealthy_io if i["kind"] == "destination")

        # 4. Version summary
        version_summary = _build_version_summary(nodes)

        # 5. Capacity alerts
        capacity_alerts = _build_capacity_alerts(nodes)

        # 6. Error summary (optional)
        errors = None
        if not skip_errors:
            errors = _fetch_error_summary(client, nodes, error_limit)

        # Compute active vs inactive group counts (exclude search/outpost defaults)
        ignored_groups = {"default_search", "default_fleet", "default_outpost"}
        node_groups = {n["group"] for n in nodes}
        active_groups = [g for g in groups if g["id"] in node_groups and g["id"] not in ignored_groups]
        inactive_groups = [g for g in groups if g["id"] not in node_groups and g["id"] not in ignored_groups]

        # 7. Leader node info
        leader_info = _fetch_leader_info(client)

        # 8. License info
        license_info = _fetch_license_info(client)

        # 9. IO health summary for active groups
        io_summary = _fetch_io_summary(client, groups, node_groups)

        # 10. Config drift detection for active groups
        config_status = _fetch_config_status(client, groups, node_groups)

        report = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "summary": {
                "total_groups": len(groups),
                "active_groups": len(active_groups),
                "inactive_groups": len(inactive_groups),
                "total_nodes": len(nodes),
                "healthy_nodes": healthy_nodes,
                "unhealthy_sources": unhealthy_sources,
                "unhealthy_destinations": unhealthy_dests,
                "capacity_alerts": len(capacity_alerts),
                "version_mismatch": version_summary["mismatch"],
            },
            "leader": leader_info,
            "license": license_info,
            "group_metadata": group_meta,
            "nodes": nodes,
            "capacity_alerts": capacity_alerts,
            "version_summary": version_summary,
            "unhealthy_io": unhealthy_io,
            "io_summary": io_summary,
            "config_status": config_status,
        }
        if errors is not None:
            report["errors"] = errors

        if as_json:
            click.echo(_json.dumps(report, indent=2))
        else:
            click.echo(_format_text_report(report))
    except Exception as e:
        handle_error(e)


# ---------------------------------------------------------------------------
# health cpu — per-node CPU spike detection over a time window
# ---------------------------------------------------------------------------

def _covered(r: dict) -> str:
    """Render how much of the requested window a node's samples cover."""
    mins = r.get("covered_minutes") or 0
    span = f"{mins / 60:.1f}h" if mins >= 120 else f"{mins:g}m"
    return f"{span} (partial)" if r.get("partial_window") else span


@health_group.command("cpu", help="Show nodes with CPU spikes over a time window. Nodes keep limited "
                      "history (Stream workers ~10 min): check covered_minutes / COVERED for the span actually analysed.")
@click.option("-g", "--group", default=None, help="Scope to a specific worker group.")
@click.option("--hours", default=24, type=int, help="Lookback window in hours (default: 24).")
@click.option("--threshold", default=80, type=int, help="CPU %% threshold to flag (default: 80).")
@click.option("--json", "as_json", is_flag=True, help="Output as structured JSON.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def health_cpu(group, hours, threshold, as_json, use_table):
    """Detect nodes with CPU spikes above a threshold."""
    try:
        client = get_client()
        nodes = _fetch_all_nodes(client, group, with_memory=False)

        if not nodes:
            click.echo("No nodes found.")
            return

        duration = hours * 3600
        results = []

        # One request per node, in parallel: a slow node no longer delays the rest.
        fetched = map_concurrent(
            lambda n: get_node_metrics(client, n["id"], duration_seconds=duration), nodes
        )
        for node, points, err in fetched:
            hostname = node["hostname"] or node["id"]
            base = {
                "hostname": hostname,
                "group": node["group"],
                "threshold_pct": threshold,
                "requested_hours": hours,
                "from": None,
                "to": None,
                "samples": 0,
                "avg_cpu": None,
                "max_cpu": None,
                "spikes": 0,
                "spike_times": [],
                "covered_minutes": 0,
                "partial_window": True,
            }
            if err is not None:
                reason = str(err)[:200] or type(err).__name__
                if isinstance(err, httpx.TimeoutException):
                    reason += " (raise the limit with the global --timeout option)"
                results.append({**base, "status": "error", "error": reason})
                continue
            if not points:
                results.append({**base, "status": "no_data"})
                continue

            cpus = [p["cpu_perc"] for p in points if p.get("cpu_perc") is not None]
            spike_points = [p for p in points if (p.get("cpu_perc") or 0) >= threshold]

            avg_cpu = sum(cpus) / len(cpus) if cpus else None
            max_cpu = max(cpus) if cpus else None
            coverage = metrics_coverage(points, duration)

            results.append({
                **base,
                "status": "spike" if spike_points else "ok",
                "samples": len(cpus),
                "avg_cpu": round(avg_cpu, 1) if avg_cpu is not None else None,
                "max_cpu": round(max_cpu, 1) if max_cpu is not None else None,
                "spikes": len(spike_points),
                "spike_times": [p["time"] for p in spike_points[:10]],
                # How much of the requested window this node really reported.
                "covered_minutes": coverage["covered_minutes"],
                "partial_window": coverage["partial"],
                "from": coverage["from"],
                "to": coverage["to"],
            })

        # Nodes that answered with less history than was asked for. JSON output
        # carries this per node (covered_minutes / partial_window); the text
        # report spells it out below.
        partial = [r for r in results if r["status"] in ("ok", "spike") and r["partial_window"]]

        # Sort: spikes first (descending), then by max_cpu descending
        results.sort(key=lambda r: (r["status"] != "spike", -(r["max_cpu"] or 0)))

        if as_json:
            click.echo(_json.dumps(results, indent=2))
            return

        spiking = [r for r in results if r["status"] == "spike"]
        ok_nodes = [r for r in results if r["status"] == "ok"]
        problem_nodes = [r for r in results if r["status"] in ("error", "no_data")]

        lines: list[str] = []
        lines.append(f"CPU Report — last {hours}h | threshold: {threshold}%")
        lines.append("=" * 70)
        lines.append(
            f"  {len(spiking)} node(s) spiking | "
            f"{len(ok_nodes)} OK | "
            f"{len(problem_nodes)} no data/error"
        )

        if spiking:
            lines.append("")
            lines.append("--- Nodes Above Threshold " + "-" * 44)
            hdr = f"  {'HOSTNAME':<38} {'GROUP':<18} {'AVG':>5} {'MAX':>5} {'SPIKES':>6}  COVERED"
            lines.append(hdr)
            for r in spiking:
                avg_s = f"{r['avg_cpu']:.0f}%" if r["avg_cpu"] is not None else "?"
                max_s = f"{r['max_cpu']:.0f}%" if r["max_cpu"] is not None else "?"
                lines.append(
                    f"  {r['hostname']:<38} {r['group']:<18} {avg_s:>5} {max_s:>5} {r['spikes']:>6}"
                    f"  {_covered(r)}"
                )
                if r["spike_times"]:
                    times_str = ", ".join(t[11:19] for t in r["spike_times"][:5])
                    if r["spikes"] > 5:
                        times_str += f" (+{r['spikes'] - 5} more)"
                    lines.append(f"    spike times: {times_str}")
        else:
            lines.append("")
            lines.append(f"  No nodes exceeded {threshold}% CPU in the last {hours}h.")

        if ok_nodes and not use_table:
            lines.append("")
            lines.append("--- All Nodes " + "-" * 56)
            hdr = f"  {'HOSTNAME':<38} {'GROUP':<18} {'AVG':>5} {'MAX':>5}  COVERED"
            lines.append(hdr)
            for r in ok_nodes:
                avg_s = f"{r['avg_cpu']:.0f}%" if r["avg_cpu"] is not None else "?"
                max_s = f"{r['max_cpu']:.0f}%" if r["max_cpu"] is not None else "?"
                lines.append(
                    f"  {r['hostname']:<38} {r['group']:<18} {avg_s:>5} {max_s:>5}  {_covered(r)}"
                )

        if partial:
            lines.append("")
            lines.append(
                f"  Note: {len(partial)} of {len(results)} node(s) returned less history than the "
                f"{hours}h requested"
            )
            lines.append(
                "  (see COVERED). Nodes keep a limited metrics history, so their figures"
            )
            lines.append("  cover only that shorter span.")

        if problem_nodes:
            lines.append("")
            lines.append("--- No Data / Errors " + "-" * 49)
            for r in problem_nodes:
                reason = f": {r['error']}" if r.get("error") else ""
                lines.append(f"  {r['hostname']:<38} {r['group']:<18} ({r['status']}{reason})")

        lines.append("")
        click.echo("\n".join(lines))

    except Exception as e:
        handle_error(e)
