"""Health check command — surfaces Red/Yellow sources and destinations."""
from __future__ import annotations

import json as _json
import time as _time
from datetime import datetime, timezone

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.edge_nodes import (
    list_edge_nodes,
    list_worker_logs,
    search_worker_log,
)
from cribl_cli.api.endpoints.workers import list_worker_groups
from cribl_cli.output.formatter import format_output
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


@health_group.command("check", help="Show unhealthy sources and destinations.")
@click.option("-g", "--group", default=None, help="Worker group.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
@click.option("--all", "show_all", is_flag=True, help="Show all items, not just unhealthy.")
def health_check(group, use_table, show_all):
    """Check health of sources and destinations in a worker group."""
    try:
        client = get_client()
        g = resolve_group(client, group)

        src_url = f"/api/v1/m/{g}/system/inputs"
        dst_url = f"/api/v1/m/{g}/system/outputs"

        if show_all:
            resp_s = client.get(src_url)
            resp_s.raise_for_status()
            resp_d = client.get(dst_url)
            resp_d.raise_for_status()
            all_sources = resp_s.json().get("items", [])
            all_dests = resp_d.json().get("items", [])
            sources = []
            for s in all_sources:
                if s.get("disabled"):
                    continue
                status = s.get("status", {})
                health = status.get("health", "?") if isinstance(status, dict) else "?"
                sources.append({
                    "kind": "source",
                    "id": s.get("id", "?"),
                    "type": s.get("type", "?"),
                    "health": health,
                })
            dests = []
            for d in all_dests:
                if d.get("disabled"):
                    continue
                status = d.get("status", {})
                health = status.get("health", "?") if isinstance(status, dict) else "?"
                dests.append({
                    "kind": "destination",
                    "id": d.get("id", "?"),
                    "type": d.get("type", "?"),
                    "health": health,
                })
            combined = sources + dests
            click.echo(format_output(combined, table=use_table))
            return

        src_problems = _check_items(client, src_url, "source")
        dst_problems = _check_items(client, dst_url, "destination")

        if not src_problems and not dst_problems:
            click.echo(f"All sources and destinations in group '{g}' are healthy.")
            return

        results = []
        for p in src_problems:
            p["kind"] = "source"
            results.append(p)
        for p in dst_problems:
            p["kind"] = "destination"
            results.append(p)

        if use_table:
            table_data = [
                {
                    "kind": r["kind"],
                    "id": r["id"],
                    "type": r["type"],
                    "health": r["health"],
                    "message": r.get("message", ""),
                }
                for r in results
            ]
            click.echo(format_output(table_data, table=True))
        else:
            click.echo(format_output(results))
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


def _fetch_all_nodes(client, group=None) -> list[dict]:
    """Fetch all nodes (edge + stream workers) with enriched health data."""
    now = _time.time()
    all_nodes = []

    for product in ("edge", None):
        params = {"product": product} if product else {}
        try:
            resp = client.get("/api/v1/master/workers", params=params)
            resp.raise_for_status()
        except Exception:
            continue
        items = resp.json().get("items", [])
        seen_ids = {n["id"] for n in all_nodes}
        for w in items:
            wid = w.get("id", "")
            if wid in seen_ids:
                continue
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
            if free_mem is None or free_mem == 0:
                # freemem not reported — don't assume 100% used
                mem_pct = None
                free_mem = 0
            else:
                mem_pct = ((total_mem - free_mem) / total_mem * 100) if total_mem > 0 else None

            all_nodes.append({
                "id": wid,
                "hostname": hostname,
                "group": grp,
                "status": w.get("status", "?"),
                "version": cribl.get("version", "?"),
                "cpus": info.get("cpus", 0),
                "total_mem": total_mem,
                "free_mem": free_mem,
                "mem_pct": round(mem_pct, 1) if mem_pct is not None else None,
                "total_disk": total_disk,
                "free_disk": free_disk,
                "disk_pct": round(disk_pct, 1) if disk_pct is not None else None,
                "heartbeat": hb_status,
                "disconnected": disconnected,
                "platform": info.get("platform", ""),
            })
    return all_nodes


def _fetch_unhealthy_io(client, groups) -> list[dict]:
    """Fetch unhealthy sources and destinations across groups."""
    results = []
    for g in groups:
        gid = g.get("id", "")
        gtype = g.get("type", "")
        if gtype in ("search", "outpost"):
            continue
        for kind, path in [("source", "system/inputs"), ("destination", "system/outputs")]:
            try:
                problems = _check_items(client, f"/api/v1/m/{gid}/{path}", kind)
                for p in problems:
                    p["group"] = gid
                    p["kind"] = kind
                    results.append(p)
            except Exception:
                continue
    return results


def _fetch_error_summary(client, nodes, limit_per_node) -> list[dict]:
    """Scan internal logs for errors across nodes."""
    all_errors: list[dict] = []
    for node in nodes:
        node_id = node["id"]
        hostname = node["hostname"] or node_id
        try:
            logs_data = list_worker_logs(client, node_id)
            log_items = logs_data.get("items", []) if isinstance(logs_data, dict) else []

            log_id = "cribl.log"
            for log in log_items:
                lid = log.get("id", "") if isinstance(log, dict) else str(log)
                if lid == "worker/0/cribl.log":
                    log_id = lid
                    break

            data = search_worker_log(client, node_id, log_id, "error", limit_per_node * 3)
            items = data.get("items", []) if isinstance(data, dict) else []
            count = 0
            for result in items:
                events = result.get("events", []) if isinstance(result, dict) else []
                for ev in events:
                    level = ev.get("level", ev.get("severity", ""))
                    if level not in ("error", "warn", "crit", "fatal"):
                        continue
                    if count >= limit_per_node:
                        break
                    all_errors.append({
                        "node": hostname,
                        "group": node["group"],
                        "level": level,
                        "channel": ev.get("channel", ""),
                        "time": ev.get("time", ev.get("_time", "")),
                        "message": (ev.get("message", "") or "")[:200],
                    })
                    count += 1
        except Exception as err:
            all_errors.append({
                "node": hostname,
                "group": node["group"],
                "level": "fetch_error",
                "channel": "",
                "time": "",
                "message": str(err)[:200],
            })
    return all_errors


def _build_version_summary(nodes) -> dict:
    """Group nodes by version and flag mismatches."""
    by_version: dict[str, list[str]] = {}
    for n in nodes:
        v = n.get("version", "?")
        by_version.setdefault(v, []).append(n["hostname"])
    versions_sorted = sorted(by_version.keys(), reverse=True)
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

        # 2. Fetch all nodes
        nodes = _fetch_all_nodes(client, group)
        healthy_nodes = sum(1 for n in nodes if n["status"] == "healthy" and n["heartbeat"] == "OK")

        # 3. Unhealthy sources & destinations
        unhealthy_io = _fetch_unhealthy_io(client, groups)
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

        report = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "summary": {
                "total_groups": len(groups),
                "total_nodes": len(nodes),
                "healthy_nodes": healthy_nodes,
                "unhealthy_sources": unhealthy_sources,
                "unhealthy_destinations": unhealthy_dests,
                "capacity_alerts": len(capacity_alerts),
                "version_mismatch": version_summary["mismatch"],
            },
            "nodes": nodes,
            "capacity_alerts": capacity_alerts,
            "version_summary": version_summary,
            "unhealthy_io": unhealthy_io,
        }
        if errors is not None:
            report["errors"] = errors

        if as_json:
            click.echo(_json.dumps(report, indent=2))
        else:
            click.echo(_format_text_report(report))
    except Exception as e:
        handle_error(e)
