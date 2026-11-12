"""Profiler commands."""
from __future__ import annotations

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.profiler import get_profiler
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.group_resolver import resolve_group


@click.group("profiler", help="Profiler status. Captures are managed with `profiler-captures`.")
def profiler_group():
    pass


@profiler_group.command("get", help="Get profiler status.")
@click.option("-g", "--group", default=None)
@click.option("--table", "use_table", is_flag=True)
def profiler_get(group, use_table):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = get_profiler(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)
