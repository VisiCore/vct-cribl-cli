"""Logger configuration commands."""
from __future__ import annotations

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.logger import get_logger, set_logger
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.group_resolver import resolve_group
from cribl_cli.utils.validation import parse_json


@click.group("logger", help="Manage logger configuration.")
def logger_group():
    pass


@logger_group.command("get", help="Get logger configuration.")
@click.option("-g", "--group", default=None)
@click.option("--table", "use_table", is_flag=True)
def logger_get(group, use_table):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = get_logger(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@logger_group.command("set", help="Set logger configuration.")
@click.argument("json_config")
@click.option("-g", "--group", default=None)
def logger_set(json_config, group):
    try:
        client = get_client()
        g = resolve_group(client, group)
        body = parse_json(json_config, "logger config")
        data = set_logger(client, g, body)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)
