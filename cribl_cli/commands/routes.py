"""Route table management commands.

CRITICAL: Routes are stored in a single route table document. The route table
has a ``routes`` (actually ``items``) array. When creating a new route, it must
be inserted BEFORE the catch-all route so the catch-all always remains last.
"""
from __future__ import annotations

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.routes import (
    create_route,
    delete_route,
    get_route,
    list_routes,
    update_route,
)
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.group_resolver import resolve_group
from cribl_cli.utils.validation import parse_json


@click.group("routes", help="Manage the route table.")
def routes_group():
    pass


@routes_group.command("list")
@click.option("-g", "--group", default=None, help="Worker group.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def routes_list(group, use_table):
    """List the full route table."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = list_routes(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@routes_group.command("get")
@click.argument("route_id")
@click.option("-g", "--group", default=None, help="Worker group.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def routes_get(route_id, group, use_table):
    """Get a single route by ID from the route table."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = get_route(client, g, route_id)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@routes_group.command("create")
@click.argument("json_config", required=False, default=None)
@click.option("--id", "route_id", default=None, help="Route ID.")
@click.option("--input", "input_id", default=None, help="Source input ID (builds __inputId filter automatically).")
@click.option("--pipeline", default=None, help="Pipeline ID.")
@click.option("--output", default=None, help="Destination output ID.")
@click.option("--filter", "filter_expr", default=None, help="Route filter expression (overrides --input).")
@click.option("--description", default=None, help="Route description.")
@click.option("-g", "--group", default=None, help="Worker group.")
def routes_create(json_config, route_id, input_id, pipeline, output, filter_expr, description, group):
    """Create a new route, inserting before the catch-all.

    Can be called with a full JSON_CONFIG string, or with individual flags.
    When --input is provided, the filter is built as __inputId=='<type>:<id>'.
    The source type prefix is resolved automatically from the Cribl API.

    Examples:

      cribl routes create --id my-route --input my_source --pipeline my_pipe --output my_dest -g default

      cribl routes create '{"id":"r1","filter":"true","pipeline":"main","output":"default"}' -g default
    """
    try:
        client = get_client()
        g = resolve_group(client, group)

        if json_config:
            new_route = parse_json(json_config, "route config")
        else:
            new_route = {}

        # Apply flag overrides
        if route_id:
            new_route["id"] = route_id
        if pipeline:
            new_route["pipeline"] = pipeline
        if output:
            new_route["output"] = output
        if description:
            new_route["description"] = description

        # Build filter from --input (resolve source type from API)
        if input_id and not filter_expr:
            from cribl_cli.api.endpoints.sources import get_source
            from cribl_cli.utils.unwrap import unwrap_item
            try:
                src = get_source(client, g, input_id)
                src = unwrap_item(src)
                src_type = src.get("type", "") if isinstance(src, dict) else ""
            except Exception:
                src_type = ""
            if src_type:
                new_route["filter"] = f"__inputId=='{src_type}:{input_id}'"
            else:
                new_route["filter"] = f"__inputId=='{input_id}'"
                click.echo(
                    f"Warning: could not resolve source type for '{input_id}'. "
                    f"Filter set to __inputId=='{input_id}' — you may need to prefix the type.",
                    err=True,
                )
        elif filter_expr:
            new_route["filter"] = filter_expr

        # Default final to False for new routes (catch-all is the only final route)
        new_route.setdefault("final", False)
        # API requires 'name' — default to the route ID
        new_route.setdefault("name", new_route.get("id", ""))

        if not new_route.get("id"):
            raise ValueError("Route ID is required (--id or in JSON)")
        if not new_route.get("filter"):
            raise ValueError("Route filter is required (--input, --filter, or in JSON)")
        if not new_route.get("pipeline"):
            raise ValueError("Pipeline is required (--pipeline or in JSON)")

        data = create_route(client, g, new_route)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@routes_group.command("update")
@click.argument("route_id")
@click.argument("json_config")
@click.option("-g", "--group", default=None, help="Worker group.")
def routes_update(route_id, json_config, group):
    """Update an existing route by merging fields.

    ROUTE_ID is the id of the route to update.
    JSON_CONFIG is a JSON string of fields to merge into the existing route.
    """
    try:
        client = get_client()
        g = resolve_group(client, group)
        updates = parse_json(json_config, "route config")
        data = update_route(client, g, route_id, updates)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@routes_group.command("delete")
@click.argument("route_id")
@click.option("-g", "--group", default=None, help="Worker group.")
def routes_delete(route_id, group):
    """Remove a route by ID from the route table."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = delete_route(client, g, route_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)
