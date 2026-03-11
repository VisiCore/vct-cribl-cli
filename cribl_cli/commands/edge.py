"""Edge node and fleet management commands."""
from __future__ import annotations

import json

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.edge import (
    get_events,
    get_kube_logs,
    get_logs,
    get_metadata,
    list_containers,
    list_files,
    list_processes,
)
from cribl_cli.api.endpoints.edge_nodes import (
    file_inspect,
    file_ls,
    file_search,
    find_edge_node,
    get_inputs,
    get_node_metrics,
    get_outputs,
    get_system_info,
    is_edge_node,
    list_edge_nodes,
    list_worker_logs,
    search_worker_log,
)
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def format_bytes(n: int | float) -> str:
    if n == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = int(n > 0 and min(len(units) - 1, int(__import__("math").log(abs(n), 1024))))
    return f"{n / (1024 ** i):.2f} {units[i]}"


def format_uptime(seconds: int | float) -> str:
    s = int(seconds)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    parts: list[str] = []
    if d > 0:
        parts.append(f"{d}d")
    if h > 0:
        parts.append(f"{h}h")
    parts.append(f"{m}m")
    return " ".join(parts)


def _require_node(client, name_or_id: str) -> dict:
    node = find_edge_node(client, name_or_id)
    if node is None:
        all_nodes = list_edge_nodes(client)
        names = ", ".join(n["hostname"] or n["id"] for n in all_nodes)
        raise ValueError(f'Node "{name_or_id}" not found. Available nodes: {names}')
    return node


# ---------------------------------------------------------------------------
# Click group
# ---------------------------------------------------------------------------

@click.group("edge", help="Edge fleet and node operations.")
def edge_group():
    pass


# ---------------------------------------------------------------------------
# Fleet-scoped commands
# ---------------------------------------------------------------------------

@edge_group.command("containers")
@click.option("-f", "--fleet", required=True, help="Fleet/group name.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def edge_containers(fleet, use_table):
    """List containers on edge nodes."""
    try:
        client = get_client()
        data = list_containers(client, fleet, fleet)
        items = data.get("items", data) if isinstance(data, dict) else data
        click.echo(format_output(items, table=use_table))
    except Exception as e:
        handle_error(e)


@edge_group.command("processes")
@click.option("-f", "--fleet", required=True, help="Fleet/group name.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def edge_processes(fleet, use_table):
    """List processes on edge nodes."""
    try:
        client = get_client()
        data = list_processes(client, fleet, fleet)
        items = data.get("items", data) if isinstance(data, dict) else data
        click.echo(format_output(items, table=use_table))
    except Exception as e:
        handle_error(e)


@edge_group.command("logs")
@click.option("-f", "--fleet", required=True, help="Fleet/group name.")
def edge_logs(fleet):
    """Get edge node logs."""
    try:
        client = get_client()
        data = get_logs(client, fleet, fleet)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@edge_group.command("metadata")
@click.option("-f", "--fleet", required=True, help="Fleet/group name.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def edge_metadata(fleet, use_table):
    """Get edge node metadata."""
    try:
        client = get_client()
        data = get_metadata(client, fleet, fleet)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@edge_group.command("events")
@click.option("-f", "--fleet", required=True, help="Fleet/group name.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def edge_events(fleet, use_table):
    """Get edge events."""
    try:
        client = get_client()
        data = get_events(client, fleet, fleet, "")
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@edge_group.command("files")
@click.argument("path")
@click.option("-f", "--fleet", required=True, help="Fleet/group name.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def edge_files(path, fleet, use_table):
    """Browse edge files."""
    try:
        client = get_client()
        data = list_files(client, fleet, fleet, path)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@edge_group.command("kube-logs")
@click.option("-f", "--fleet", required=True, help="Fleet/group name.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def edge_kube_logs(fleet, use_table):
    """Get Kubernetes logs."""
    try:
        client = get_client()
        data = get_kube_logs(client, fleet, fleet)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


# ---------------------------------------------------------------------------
# Node-scoped commands (no --group needed, uses /api/v1/master/workers)
# ---------------------------------------------------------------------------

@edge_group.command("heartbeats")
@click.option("-f", "--fleet", default=None, help="Fleet/group name to filter by.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
@click.option("--threshold", default=300, type=int, help="Seconds before a heartbeat is considered late (default: 300).")
def edge_heartbeats(fleet, use_table, threshold):
    """Check node health: heartbeat, disk, memory, and CPU.

    Flags nodes that are late/disconnected, low on disk (>=80%),
    or have other issues.
    """
    try:
        import time as _time

        client = get_client()
        resp = client.get("/api/v1/master/workers", params={"product": "edge"})
        resp.raise_for_status()
        items = resp.json().get("items", [])

        now = _time.time()
        rows = []
        alerts = []
        for w in items:
            group = w.get("group", "")
            if fleet and group != fleet:
                continue
            info = w.get("info", {})
            hostname = info.get("hostname", w.get("id", "?"))
            status = w.get("status", "?")
            disconnected = w.get("disconnected", False)
            last_msg = w.get("lastMsgTime", 0) / 1000  # ms -> sec
            ago = now - last_msg

            if ago < 60:
                ago_str = f"{ago:.0f}s ago"
            elif ago < 3600:
                ago_str = f"{ago / 60:.0f}m ago"
            elif ago < 86400:
                ago_str = f"{ago / 3600:.1f}h ago"
            else:
                ago_str = f"{ago / 86400:.1f}d ago"

            # Heartbeat status
            if disconnected:
                hb_notes = "DISCONNECTED"
            elif ago > 86400:
                hb_notes = "MISSED (>24h)"
            elif ago > threshold:
                hb_notes = f"LATE (>{threshold}s)"
            else:
                hb_notes = "OK"

            # Disk
            total_disk = info.get("totalDiskSpace", 0)
            free_disk = info.get("freeDiskSpace", 0)
            if total_disk > 0:
                disk_pct = ((total_disk - free_disk) / total_disk) * 100
                disk_str = f"{disk_pct:.0f}% ({format_bytes(free_disk)} free)"
                if disk_pct >= 90:
                    alerts.append(f"{hostname}: disk CRITICAL at {disk_pct:.0f}%")
                elif disk_pct >= 80:
                    alerts.append(f"{hostname}: disk WARNING at {disk_pct:.0f}%")
            else:
                disk_str = "?"

            # Memory
            total_mem = info.get("totalmem", 0)
            cpus = info.get("cpus", 0)

            row = {
                "hostname": hostname,
                "group": group,
                "status": status,
                "last_hb": ago_str,
                "heartbeat": hb_notes,
                "cpus": cpus,
                "memory": format_bytes(total_mem),
                "disk": disk_str,
            }
            rows.append(row)

            if hb_notes != "OK":
                alerts.append(f"{hostname}: heartbeat {hb_notes}")

        if use_table:
            click.echo(format_output(rows, table=True))
        else:
            click.echo(format_output(rows))

        # Summary
        total = len(rows)
        if alerts:
            click.echo(f"\n{len(alerts)} alert(s):", err=True)
            for a in alerts:
                click.echo(f"  - {a}", err=True)
        else:
            click.echo(f"\nAll {total} node(s) healthy — no alerts.", err=True)
    except Exception as e:
        handle_error(e)


@edge_group.command("nodes")
@click.option("-f", "--fleet", default=None, help="Fleet/group name to filter by.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def edge_nodes(fleet, use_table):
    """List edge nodes (optionally filtered by fleet)."""
    try:
        client = get_client()
        nodes = list_edge_nodes(client, fleet)
        summary = [
            {
                "id": n["id"],
                "hostname": n["hostname"],
                "status": n["status"],
                "fleet": n["group"],
                "cpus": n["cpus"],
                "memory": format_bytes(n["totalmem"]),
                "platform": n["platform"],
                "version": n["version"],
            }
            for n in nodes
        ]
        click.echo(format_output(summary, table=use_table))
    except Exception as e:
        handle_error(e)


@edge_group.command("system-info")
@click.argument("node", metavar="NODE")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def edge_system_info(node, use_table):
    """Get system info for an edge node (CPU, memory, disk, network)."""
    try:
        client = get_client()
        found = _require_node(client, node)
        info = get_system_info(client, found["id"])

        if use_table:
            click.echo(format_output(info, table=True))
            return

        cpus = info.get("cpus", [])
        total_user = sum(c.get("times", {}).get("user", 0) for c in cpus)
        total_sys = sum(c.get("times", {}).get("sys", 0) for c in cpus)
        total_idle = sum(c.get("times", {}).get("idle", 0) for c in cpus)
        total_time = total_user + total_sys + total_idle or 1
        os_info = info.get("os", {})
        mem = info.get("memory", {})
        disk = info.get("diskUsage", {})

        summary = {
            "hostname": info.get("hostname"),
            "os": f"{os_info.get('type', '')} {os_info.get('arch', '')} {os_info.get('release', '')}",
            "uptime": format_uptime(info.get("uptime", 0)),
            "cpu": {
                "cores": len(cpus),
                "model": cpus[0].get("model", "unknown") if cpus else "unknown",
                "speed_mhz": cpus[0].get("speed", 0) if cpus else 0,
                "user_pct": f"{(total_user / total_time * 100):.2f}%",
                "sys_pct": f"{(total_sys / total_time * 100):.2f}%",
                "idle_pct": f"{(total_idle / total_time * 100):.2f}%",
            },
            "load_avg": {
                "1min": info.get("loadavg", [0])[0] if info.get("loadavg") else 0,
                "5min": info.get("loadavg", [0, 0])[1] if len(info.get("loadavg", [])) > 1 else 0,
                "15min": info.get("loadavg", [0, 0, 0])[2] if len(info.get("loadavg", [])) > 2 else 0,
            },
            "memory": {
                "total": format_bytes(mem.get("total", 0)),
                "free": format_bytes(mem.get("free", 0)),
                "used": format_bytes(mem.get("total", 0) - mem.get("free", 0)),
                "used_pct": f"{((mem.get('total', 0) - mem.get('free', 0)) / (mem.get('total', 1)) * 100):.1f}%",
            },
            "disk": {
                "path": disk.get("diskPath", ""),
                "total": format_bytes(disk.get("totalDiskSize", 0)),
                "used": format_bytes(disk.get("bytesUsed", 0)),
                "available": format_bytes(disk.get("bytesAvailable", 0)),
                "used_pct": f"{(disk.get('bytesUsed', 0) / (disk.get('totalDiskSize', 1)) * 100):.1f}%",
            },
        }
        click.echo(format_output(summary))
    except Exception as e:
        handle_error(e)


@edge_group.command("system-info-raw")
@click.argument("node", metavar="NODE")
def edge_system_info_raw(node):
    """Get raw system info JSON for an edge node."""
    try:
        client = get_client()
        found = _require_node(client, node)
        info = get_system_info(client, found["id"])
        click.echo(format_output(info))
    except Exception as e:
        handle_error(e)


@edge_group.command("inputs")
@click.argument("node", metavar="NODE")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def edge_inputs(node, use_table):
    """Get inputs/sources for an edge node."""
    try:
        client = get_client()
        found = _require_node(client, node)
        data = get_inputs(client, found["id"])
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@edge_group.command("outputs")
@click.argument("node", metavar="NODE")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def edge_outputs(node, use_table):
    """Get outputs/destinations for an edge node."""
    try:
        client = get_client()
        found = _require_node(client, node)
        data = get_outputs(client, found["id"])
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@edge_group.command("fileinspect")
@click.argument("node", metavar="NODE")
@click.argument("path")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def edge_fileinspect(node, path, use_table):
    """Inspect a file on an edge node (stat, hashes, head, hexdump).

    Only available on managed-edge nodes, not hybrid workers.
    """
    try:
        client = get_client()
        found = _require_node(client, node)
        if not is_edge_node(found):
            click.echo(
                f'fileinspect is only supported on Edge nodes. '
                f'"{found["hostname"]}" is a hybrid worker (distMode: {found["distMode"]}).\n'
                f'Use "edge file-search" to search Cribl log files on hybrid workers.',
                err=True,
            )
            raise SystemExit(1)
        data = file_inspect(client, found["id"], path)
        click.echo(format_output(data, table=use_table))
    except SystemExit:
        raise
    except Exception as e:
        handle_error(e)


@edge_group.command("node-ls")
@click.argument("node", metavar="NODE")
@click.argument("path")
@click.option("--stats", is_flag=True, help="Include file stats.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def edge_node_ls(node, path, stats, use_table):
    """List directory contents on an edge node."""
    try:
        client = get_client()
        found = _require_node(client, node)
        if not is_edge_node(found):
            click.echo(
                f'Note: "{found["hostname"]}" is a hybrid worker — only Cribl log files are available.',
                err=True,
            )
            data = list_worker_logs(client, found["id"])
            click.echo(format_output(data, table=use_table))
            return
        data = file_ls(client, found["id"], path, stats)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@edge_group.command("file-search")
@click.argument("node", metavar="NODE")
@click.argument("path")
@click.option("-q", "--query", default=None, help="Search query.")
@click.option("-l", "--limit", default=50, type=int, help="Max lines.")
@click.option("-o", "--offset", default="0", help="Offset for pagination.")
@click.option("--raw", is_flag=True, help="Print only raw lines.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def edge_file_search(node, path, query, limit, offset, raw, use_table):
    """Search or read file contents on an edge node."""
    try:
        client = get_client()
        found = _require_node(client, node)
        if not is_edge_node(found):
            # Hybrid workers: use system/logs API
            log_id = path.replace("/opt/cribl/log/", "")
            data = search_worker_log(
                client, found["id"], log_id, query,
                limit, offset if offset != "0" else None,
            )
            if raw:
                results = data.get("items", []) if isinstance(data, dict) else []
                for result in results:
                    for e in result.get("events", []):
                        click.echo(json.dumps(e))
            else:
                click.echo(format_output(data, table=use_table))
            return
        data = file_search(client, found["id"], path, query, limit, int(offset))
        if raw:
            items = data.get("items", []) if isinstance(data, dict) else []
            events = items[0].get("items", []) if items else []
            for e in events:
                click.echo(e.get("_raw", ""))
        else:
            click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@edge_group.command("errors", help="Scan internal logs for errors across all nodes.")
@click.option("-f", "--fleet", default=None, help="Fleet/group name to filter by.")
@click.option("-l", "--limit", default=20, type=int, help="Max error lines per node.")
@click.option("-q", "--query", default=None, help="Filter query (default: error).")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def edge_errors(fleet, limit, query, use_table):
    """Check all nodes for errors in their internal Cribl logs.

    Scans cribl.log on each node for error-level messages.
    """
    try:
        client = get_client()
        nodes = list_edge_nodes(client, fleet)

        if not nodes:
            click.echo("No nodes found.", err=True)
            return

        all_errors: list[dict] = []
        for node in nodes:
            node_id = node["id"]
            hostname = node["hostname"] or node_id
            try:
                # List available logs to find the best cribl.log
                logs_data = list_worker_logs(client, node_id)
                log_items = logs_data.get("items", []) if isinstance(logs_data, dict) else []

                # Prefer worker/0/cribl.log (has more detail), fall back to cribl.log
                log_id = "cribl.log"
                for log in log_items:
                    lid = log.get("id", "") if isinstance(log, dict) else str(log)
                    if lid == "worker/0/cribl.log":
                        log_id = lid
                        break

                # Search for errors — fetch more than limit to filter by level
                filter_str = query or "error"
                data = search_worker_log(client, node_id, log_id, filter_str, limit * 3)
                items = data.get("items", []) if isinstance(data, dict) else []
                count = 0
                for result in items:
                    events = result.get("events", []) if isinstance(result, dict) else []
                    for ev in events:
                        level = ev.get("level", ev.get("severity", ""))
                        # When using default filter, only keep error/warn level
                        if not query and level not in ("error", "warn", "crit", "fatal"):
                            continue
                        if count >= limit:
                            break
                        msg = ev.get("message", ev.get("_raw", ""))
                        ts = ev.get("time", ev.get("_time", ev.get("timestamp", "")))
                        channel = ev.get("channel", "")
                        all_errors.append({
                            "node": hostname,
                            "group": node["group"],
                            "level": level,
                            "channel": channel,
                            "time": ts,
                            "message": msg[:200] if msg else "",
                        })
                        count += 1
            except Exception as node_err:
                all_errors.append({
                    "node": hostname,
                    "group": node["group"],
                    "level": "fetch_error",
                    "channel": "",
                    "time": "",
                    "message": str(node_err)[:200],
                })

        if not all_errors:
            click.echo(f"No errors found across {len(nodes)} node(s).")
            return

        click.echo(format_output(all_errors, table=use_table))
        click.echo(f"\n{len(all_errors)} error(s) across {len(nodes)} node(s).", err=True)
    except Exception as e:
        handle_error(e)


DUR_MAP = {
    "5m": 300, "10m": 600, "15m": 900, "30m": 1800,
    "1h": 3600, "4h": 14400, "12h": 43200, "1d": 86400,
}


@edge_group.command("metrics")
@click.argument("node", metavar="NODE")
@click.option("-d", "--duration", default="1h", help="Time range: 5m,10m,15m,30m,1h,4h,12h,1d")
@click.option("--summary", is_flag=True, help="Show min/max/avg summary.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def edge_metrics(node, duration, summary, use_table):
    """Get historical metrics (CPU, memory, disk, load) for a node."""
    try:
        client = get_client()
        found = _require_node(client, node)
        seconds = DUR_MAP.get(duration)
        if not seconds:
            click.echo(
                f'Invalid duration "{duration}". Use: {", ".join(DUR_MAP.keys())}',
                err=True,
            )
            raise SystemExit(1)

        points = get_node_metrics(client, found["id"], seconds)
        if not points:
            click.echo("No metrics data available for this time range.", err=True)
            raise SystemExit(1)

        if summary:
            cpus = [p["cpu_perc"] for p in points if p.get("cpu_perc") is not None]
            mems = [p["mem_used_pct"] for p in points if p.get("mem_used_pct") is not None]
            loads = [p["load_avg"] for p in points if p.get("load_avg") is not None]
            disks = [p["disk_used_pct"] for p in points if p.get("disk_used_pct") is not None]
            def agg(arr):
                return {"min": f"{min(arr):.1f}%", "max": f"{max(arr):.1f}%", "avg": f"{sum(arr)/len(arr):.1f}%"}
            def agg_load(arr):
                return {"min": f"{min(arr):.2f}", "max": f"{max(arr):.2f}", "avg": f"{sum(arr)/len(arr):.2f}"}
            s = {
                "hostname": found["hostname"],
                "duration": duration,
                "data_points": len(points),
                "from": points[0]["time"],
                "to": points[-1]["time"],
                "cpu_perc": agg(cpus) if cpus else None,
                "mem_used_pct": agg(mems) if mems else None,
                "disk_used_pct": agg(disks) if disks else None,
                "load_avg": agg_load(loads) if loads else None,
            }
            click.echo(format_output(s, table=use_table))
        else:
            series = [
                {
                    "time": p["time"],
                    "cpu_pct": f"{p['cpu_perc']:.1f}%" if p.get("cpu_perc") is not None else "-",
                    "mem_used": format_bytes(p["mem_used_bytes"]) if p.get("mem_used_bytes") is not None else "-",
                    "mem_pct": f"{p['mem_used_pct']:.1f}%" if p.get("mem_used_pct") is not None else "-",
                    "disk_pct": f"{p['disk_used_pct']:.1f}%" if p.get("disk_used_pct") is not None else "-",
                    "load": f"{p['load_avg']:.2f}" if p.get("load_avg") is not None else "-",
                }
                for p in points
            ]
            click.echo(format_output(series, table=use_table))
    except SystemExit:
        raise
    except Exception as e:
        handle_error(e)
