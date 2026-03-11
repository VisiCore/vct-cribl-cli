"""Profiler commands."""
from __future__ import annotations

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.profiler import get_profiler, start_profiler, stop_profiler
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.group_resolver import resolve_group


@click.group("profiler", help="Manage the profiler.")
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


@profiler_group.command("start", help="Start the profiler.")
@click.option("-g", "--group", default=None)
def profiler_start(group):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = start_profiler(client, g)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@profiler_group.command("stop", help="Stop the profiler.")
@click.option("-g", "--group", default=None)
def profiler_stop(group):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = stop_profiler(client, g)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)
