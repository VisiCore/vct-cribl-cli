"""Alerts commands — scheduled saved searches with notifications."""
from __future__ import annotations

import click

from cribl_cli.api.client import get_client
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error


@click.group("alerts", help="Manage alerts (scheduled saved searches).")
def alerts_group():
    pass


@alerts_group.command("list")
@click.option("-g", "--group", default="default_search", help="Search group.")
@click.option("--table", "use_table", is_flag=True)
@click.option("--all", "show_all", is_flag=True, help="Include non-scheduled saved searches.")
def alerts_list(group, use_table, show_all):
    """List alerts (saved searches with schedules enabled)."""
    try:
        client = get_client()
        resp = client.get(f"/api/v1/m/{group}/search/saved")
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])

        if not show_all:
            items = [s for s in items if s.get("schedule", {}).get("enabled")]

        click.echo(format_output({"items": items}, table=use_table))
    except Exception as e:
        handle_error(e)
