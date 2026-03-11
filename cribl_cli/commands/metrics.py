"""System metrics commands."""
from __future__ import annotations

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.metrics import get_metrics
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error


@click.group("metrics", help="System metrics.")
def metrics_group():
    pass


@metrics_group.command("get", help="Get system metrics.")
@click.option("--filter", "filter_expr", default=None, help="Metric filter.")
@click.option("--table", "use_table", is_flag=True)
def metrics_get(filter_expr, use_table):
    try:
        client = get_client()
        data = get_metrics(client, filter_expr)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)
