"""KMS management commands."""
from __future__ import annotations

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.kms import get_kms_config, update_kms_config, get_kms_health
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.group_resolver import resolve_group
from cribl_cli.utils.validation import parse_json


@click.group("kms", help="Key Management Service configuration.")
def kms_group():
    pass


@kms_group.command("config", help="Get KMS configuration.")
@click.option("-g", "--group", default=None)
@click.option("--table", "use_table", is_flag=True)
def kms_config(group, use_table):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = get_kms_config(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@kms_group.command("update", help="Update KMS configuration.")
@click.argument("json_config")
@click.option("-g", "--group", default=None)
def kms_update(json_config, group):
    try:
        client = get_client()
        g = resolve_group(client, group)
        body = parse_json(json_config, "KMS config")
        data = update_kms_config(client, g, body)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@kms_group.command("health", help="Get KMS health status.")
@click.option("-g", "--group", default=None)
@click.option("--table", "use_table", is_flag=True)
def kms_health(group, use_table):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = get_kms_health(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)
