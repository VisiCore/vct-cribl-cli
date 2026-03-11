"""Destination management commands."""
from __future__ import annotations

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.destinations import (
    list_destinations, get_destination, create_destination, update_destination, delete_destination,
)
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.group_resolver import resolve_group
from cribl_cli.utils.unwrap import unwrap_item
from cribl_cli.utils.validation import parse_json, parse_port


@click.group("destinations", help="Manage destinations (outputs).")
def destinations_group():
    pass


@destinations_group.command("list")
@click.option("-g", "--group", default=None)
@click.option("--table", "use_table", is_flag=True)
def destinations_list(group, use_table):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = list_destinations(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@destinations_group.command("get")
@click.argument("destination_id")
@click.option("-g", "--group", default=None)
@click.option("--table", "use_table", is_flag=True)
def destinations_get(destination_id, group, use_table):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = get_destination(client, g, destination_id)
        data = unwrap_item(data)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@destinations_group.command("create")
@click.option("-t", "--type", "dest_type", required=False, help="Destination type.")
@click.option("--id", "dest_id", default=None, help="Destination ID.")
@click.option("--port", default=None, help="Port number.")
@click.option("--json-config", default=None, help="Full JSON config.")
@click.option("-g", "--group", default=None)
def destinations_create(dest_type, dest_id, port, json_config, group):
    try:
        client = get_client()
        g = resolve_group(client, group)
        if json_config:
            body = parse_json(json_config, "destination config")
        else:
            if not dest_type:
                raise ValueError("Either --type or --json-config is required")
            body = {"type": dest_type}
            if dest_id:
                body["id"] = dest_id
            if port:
                body["port"] = parse_port(port)
        data = create_destination(client, g, body)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@destinations_group.command("update")
@click.argument("destination_id")
@click.argument("json_config")
@click.option("-g", "--group", default=None)
def destinations_update(destination_id, json_config, group):
    try:
        client = get_client()
        g = resolve_group(client, group)
        existing = get_destination(client, g, destination_id)
        existing = unwrap_item(existing)
        if isinstance(existing, dict):
            existing.pop("status", None)
            existing.pop("notifications", None)
        updates = parse_json(json_config, "destination config")
        merged = {**existing, **updates}
        data = update_destination(client, g, destination_id, merged)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@destinations_group.command("delete")
@click.argument("destination_id")
@click.option("-g", "--group", default=None)
def destinations_delete(destination_id, group):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = delete_destination(client, g, destination_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)
