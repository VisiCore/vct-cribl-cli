"""Source management commands."""
from __future__ import annotations

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.sources import (
    list_sources, get_source, create_source, update_source, delete_source,
)
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.group_resolver import resolve_group
from cribl_cli.utils.unwrap import unwrap_item
from cribl_cli.utils.validation import parse_json, parse_port


@click.group("sources", help="Manage sources (inputs).")
def sources_group():
    pass


@sources_group.command("list")
@click.option("-g", "--group", default=None)
@click.option("--table", "use_table", is_flag=True)
def sources_list(group, use_table):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = list_sources(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@sources_group.command("get")
@click.argument("source_id")
@click.option("-g", "--group", default=None)
@click.option("--table", "use_table", is_flag=True)
def sources_get(source_id, group, use_table):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = get_source(client, g, source_id)
        data = unwrap_item(data)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@sources_group.command("create")
@click.option("-t", "--type", "source_type", required=False, help="Source type.")
@click.option("--id", "source_id", default=None, help="Source ID.")
@click.option("--port", default=None, help="Port number.")
@click.option("--path", default=None, help="Directory path (for file sources).")
@click.option("--filenames", default=None, help='Filename glob patterns, comma-separated (default: "*").')
@click.option("--description", default=None, help="Source description.")
@click.option("--send-to-routes/--no-send-to-routes", default=True, help="Send events to routes (default: true).")
@click.option("--json-config", default=None, help="Full JSON config.")
@click.option("-g", "--group", default=None)
def sources_create(source_type, source_id, port, path, filenames, description, send_to_routes, json_config, group):
    try:
        client = get_client()
        g = resolve_group(client, group)
        if json_config:
            body = parse_json(json_config, "source config")
        else:
            if not source_type:
                raise ValueError("Either --type or --json-config is required")
            body = {"type": source_type}
            if source_id:
                body["id"] = source_id
            if port:
                body["port"] = parse_port(port)
            if description:
                body["description"] = description
            body["sendToRoutes"] = send_to_routes

        # File source validation and defaults
        if body.get("type") == "file":
            if path:
                body["path"] = path
            if filenames:
                body["filenames"] = [f.strip() for f in filenames.split(",")]
            # Default filenames to ["*"] if path is set but no filenames given
            if body.get("path") and "filenames" not in body:
                body["filenames"] = ["*"]
            if not body.get("path") and not body.get("filenames"):
                raise ValueError("File sources require --path (directory to monitor)")

        data = create_source(client, g, body)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@sources_group.command("update")
@click.argument("source_id")
@click.argument("json_config")
@click.option("-g", "--group", default=None)
def sources_update(source_id, json_config, group):
    try:
        client = get_client()
        g = resolve_group(client, group)
        existing = get_source(client, g, source_id)
        existing = unwrap_item(existing)
        if isinstance(existing, dict):
            existing.pop("status", None)
            existing.pop("notifications", None)
        updates = parse_json(json_config, "source config")
        merged = {**existing, **updates}
        data = update_source(client, g, source_id, merged)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@sources_group.command("delete")
@click.argument("source_id")
@click.option("-g", "--group", default=None)
def sources_delete(source_id, group):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = delete_source(client, g, source_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)
