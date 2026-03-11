"""Health check command — surfaces Red/Yellow sources and destinations."""
from __future__ import annotations

import click

from cribl_cli.api.client import get_client
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
