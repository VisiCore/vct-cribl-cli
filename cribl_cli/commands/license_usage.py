"""License usage commands — daily throughput metrics."""
from __future__ import annotations

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.license_usage import get_license_usage
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error


@click.group("license-usage", help="Daily license usage metrics (up to 90 days).")
def license_usage_group():
    pass


@license_usage_group.command("get", help="Get daily license usage metrics.")
@click.option("--start", default=None, help="Start date (ISO 8601, e.g. 2025-01-01).")
@click.option("--end", default=None, help="End date (ISO 8601).")
@click.option("--table", "use_table", is_flag=True, help="Table output.")
def license_usage_get(start, end, use_table):
    try:
        client = get_client()
        data = get_license_usage(client, start=start, end=end)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)
