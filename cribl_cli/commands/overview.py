"""Environment overview command — summarises groups, nodes, sources, destinations."""
from __future__ import annotations

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.edge_nodes import list_edge_nodes
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error


def _format_bytes(n: int | float) -> str:
    if n == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(min(len(units) - 1, math.log(abs(n), 1024)))
    return f"{n / (1024 ** i):.1f} {units[i]}"


def _count_by_type(items: list[dict], type_key: str = "type", disabled_key: str = "disabled") -> dict:
    active: dict[str, int] = {}
    disabled_count = 0
    for item in items:
        if item.get(disabled_key):
            disabled_count += 1
            continue
        t = item.get(type_key, "unknown")
        active[t] = active.get(t, 0) + 1
    return {"active": active, "disabled": disabled_count, "total": len(items)}


@click.group("overview", help="Environment overview and summaries.")
def overview_group():
    pass


@overview_group.command("summary", help="Summarise all groups, nodes, sources, and destinations.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON instead of text.")
def overview_summary(as_json):
    """Print a high-level summary of the entire Cribl environment."""
    try:
        client = get_client()

        # Worker groups
        wg_resp = client.get("/api/v1/master/groups")
        wg_resp.raise_for_status()
        groups = wg_resp.json().get("items", [])

        # All nodes
        nodes = list_edge_nodes(client)

        # Build per-group detail
        group_details = []
        total_sources = 0
        total_dests = 0
        for g in groups:
            gid = g.get("id", "?")
            gtype = g.get("type", "stream")
            desc = g.get("description", "")
            is_fleet = g.get("isFleet", False)
            is_search = g.get("isSearch", False)

            # Count nodes in this group
            group_nodes = [n for n in nodes if n["group"] == gid]

            # Fetch sources & destinations (skip search/outpost groups)
            src_summary = None
            dst_summary = None
            if gtype not in ("search", "outpost"):
                try:
                    src_resp = client.get(f"/api/v1/m/{gid}/system/inputs")
                    src_resp.raise_for_status()
                    src_items = src_resp.json().get("items", [])
                    src_summary = _count_by_type(src_items)
                    total_sources += src_summary["total"]
                except Exception:
                    src_summary = {"error": "could not fetch"}

                try:
                    dst_resp = client.get(f"/api/v1/m/{gid}/system/outputs")
                    dst_resp.raise_for_status()
                    dst_items = dst_resp.json().get("items", [])
                    dst_summary = _count_by_type(dst_items)
                    total_dests += dst_summary["total"]
                except Exception:
                    dst_summary = {"error": "could not fetch"}

            # Health of sources/dests
            src_red = 0
            dst_red = 0
            if src_summary and "error" not in src_summary:
                for s in src_items:
                    if not s.get("disabled"):
                        st = s.get("status", {})
                        if isinstance(st, dict) and st.get("health") == "Red":
                            src_red += 1
            if dst_summary and "error" not in dst_summary:
                for d in dst_items:
                    if not d.get("disabled"):
                        st = d.get("status", {})
                        if isinstance(st, dict) and st.get("health") == "Red":
                            dst_red += 1

            detail: dict = {
                "group": gid,
                "type": gtype,
                "description": desc,
                "nodes": len(group_nodes),
                "healthy_nodes": sum(1 for n in group_nodes if n["status"] == "healthy"),
            }
            if src_summary and "error" not in src_summary:
                active_count = sum(src_summary["active"].values())
                detail["sources"] = f"{active_count} active, {src_summary['disabled']} disabled"
                top = sorted(src_summary["active"].items(), key=lambda x: -x[1])[:3]
                detail["top_source_types"] = ", ".join(f"{c} {t}" for t, c in top)
                if src_red:
                    detail["sources_red"] = src_red
            if dst_summary and "error" not in dst_summary:
                active_count = sum(dst_summary["active"].values())
                detail["destinations"] = f"{active_count} active, {dst_summary['disabled']} disabled"
                if dst_red:
                    detail["destinations_red"] = dst_red

            group_details.append(detail)

        if as_json:
            click.echo(format_output({
                "groups": len(groups),
                "total_nodes": len(nodes),
                "healthy_nodes": sum(1 for n in nodes if n["status"] == "healthy"),
                "total_sources": total_sources,
                "total_destinations": total_dests,
                "details": group_details,
            }))
            return

        # Text output
        click.echo(f"Cribl Environment Summary")
        click.echo(f"{'=' * 70}")
        click.echo(f"Groups: {len(groups)}  |  Nodes: {len(nodes)} ({sum(1 for n in nodes if n['status'] == 'healthy')} healthy)  |  Sources: {total_sources}  |  Destinations: {total_dests}")
        click.echo()

        for d in group_details:
            node_str = f"{d['healthy_nodes']}/{d['nodes']} healthy" if d["nodes"] else "no nodes"
            header = f"  {d['group']:<30s}  [{d['type']}]  {node_str}"
            if d.get("description"):
                header += f"  — {d['description']}"
            click.echo(header)

            if d.get("sources"):
                line = f"    Sources:      {d['sources']}"
                if d.get("sources_red"):
                    line += f"  ({d['sources_red']} RED)"
                click.echo(line)
                if d.get("top_source_types"):
                    click.echo(f"    Top types:    {d['top_source_types']}")

            if d.get("destinations"):
                line = f"    Destinations: {d['destinations']}"
                if d.get("destinations_red"):
                    line += f"  ({d['destinations_red']} RED)"
                click.echo(line)

            click.echo()

    except Exception as e:
        handle_error(e)


@overview_group.command("sources", help="Summarise sources by type for a group.")
@click.option("-g", "--group", default=None, help="Worker group.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def overview_sources(group, use_table):
    """Show source count breakdown by type."""
    try:
        client = get_client()
        from cribl_cli.utils.group_resolver import resolve_group
        g = resolve_group(client, group)

        resp = client.get(f"/api/v1/m/{g}/system/inputs")
        resp.raise_for_status()
        items = resp.json().get("items", [])

        by_type: dict[str, dict] = {}
        for s in items:
            t = s.get("type", "unknown")
            if t not in by_type:
                by_type[t] = {"type": t, "active": 0, "disabled": 0, "red": 0, "green": 0}
            if s.get("disabled"):
                by_type[t]["disabled"] += 1
            else:
                by_type[t]["active"] += 1
                status = s.get("status", {})
                health = status.get("health", "") if isinstance(status, dict) else ""
                if health == "Red":
                    by_type[t]["red"] += 1
                elif health == "Green":
                    by_type[t]["green"] += 1

        rows = sorted(by_type.values(), key=lambda r: -(r["active"] + r["disabled"]))
        total_active = sum(r["active"] for r in rows)
        total_disabled = sum(r["disabled"] for r in rows)
        total_red = sum(r["red"] for r in rows)

        if use_table:
            click.echo(format_output(rows, table=True))
        else:
            click.echo(format_output(rows))

        click.echo(
            f"\nTotal: {total_active} active, {total_disabled} disabled, {total_red} red",
            err=True,
        )
    except Exception as e:
        handle_error(e)


@overview_group.command("destinations", help="Summarise destinations by type for a group.")
@click.option("-g", "--group", default=None, help="Worker group.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def overview_destinations(group, use_table):
    """Show destination count breakdown by type."""
    try:
        client = get_client()
        from cribl_cli.utils.group_resolver import resolve_group
        g = resolve_group(client, group)

        resp = client.get(f"/api/v1/m/{g}/system/outputs")
        resp.raise_for_status()
        items = resp.json().get("items", [])

        by_type: dict[str, dict] = {}
        for d in items:
            t = d.get("type", "unknown")
            if t not in by_type:
                by_type[t] = {"type": t, "active": 0, "disabled": 0, "red": 0, "green": 0}
            if d.get("disabled"):
                by_type[t]["disabled"] += 1
            else:
                by_type[t]["active"] += 1
                status = d.get("status", {})
                health = status.get("health", "") if isinstance(status, dict) else ""
                if health == "Red":
                    by_type[t]["red"] += 1
                elif health == "Green":
                    by_type[t]["green"] += 1

        rows = sorted(by_type.values(), key=lambda r: -(r["active"] + r["disabled"]))
        total_active = sum(r["active"] for r in rows)
        total_disabled = sum(r["disabled"] for r in rows)
        total_red = sum(r["red"] for r in rows)

        if use_table:
            click.echo(format_output(rows, table=True))
        else:
            click.echo(format_output(rows))

        click.echo(
            f"\nTotal: {total_active} active, {total_disabled} disabled, {total_red} red",
            err=True,
        )
    except Exception as e:
        handle_error(e)
