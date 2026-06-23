"""Pipeline management commands."""
from __future__ import annotations

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.pipelines import (
    list_pipelines, get_pipeline, create_pipeline, update_pipeline, delete_pipeline,
)
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.group_resolver import resolve_group
from cribl_cli.utils.unwrap import unwrap_item
from cribl_cli.utils.validation import parse_json


_PACK_OPT = click.option(
    "--pack", "-P", default=None,
    help="Pack ID — scope the request to a pack inside the worker group.",
)


@click.group("pipelines", help="Manage pipelines.")
def pipelines_group():
    pass


@pipelines_group.command("list")
@click.option("-g", "--group", default=None)
@_PACK_OPT
@click.option("--table", "use_table", is_flag=True)
def pipelines_list(group, pack, use_table):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = list_pipelines(client, g, pack=pack)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@pipelines_group.command("get")
@click.argument("pipeline_id")
@click.option("-g", "--group", default=None)
@_PACK_OPT
@click.option("--table", "use_table", is_flag=True)
def pipelines_get(pipeline_id, group, pack, use_table):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = get_pipeline(client, g, pipeline_id, pack=pack)
        data = unwrap_item(data)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@pipelines_group.command("create")
@click.argument("json_config")
@click.option("-g", "--group", default=None)
@_PACK_OPT
def pipelines_create(json_config, group, pack):
    try:
        client = get_client()
        g = resolve_group(client, group)
        body = parse_json(json_config, "pipeline config")
        data = create_pipeline(client, g, body, pack=pack)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@pipelines_group.command("update")
@click.argument("pipeline_id")
@click.argument("json_config")
@click.option("-g", "--group", default=None)
@_PACK_OPT
def pipelines_update(pipeline_id, json_config, group, pack):
    try:
        client = get_client()
        g = resolve_group(client, group)
        existing = get_pipeline(client, g, pipeline_id, pack=pack)
        existing = unwrap_item(existing)
        updates = parse_json(json_config, "pipeline config")
        merged = {**existing, **updates}
        data = update_pipeline(client, g, pipeline_id, merged, pack=pack)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@pipelines_group.command("delete")
@click.argument("pipeline_id")
@click.option("-g", "--group", default=None)
@_PACK_OPT
def pipelines_delete(pipeline_id, group, pack):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = delete_pipeline(client, g, pipeline_id, pack=pack)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@pipelines_group.command("clone", help="Clone a pipeline from one group to another.")
@click.argument("pipeline_id")
@click.option("--source-group", required=True, help="Source worker group.")
@click.option("--dest-group", required=True, help="Destination worker group.")
@click.option("--source-pack", default=None, help="Source pack ID.")
@click.option("--dest-pack", default=None, help="Destination pack ID.")
def pipelines_clone(pipeline_id, source_group, dest_group, source_pack, dest_pack):
    try:
        client = get_client()
        src_g = resolve_group(client, source_group)
        dst_g = resolve_group(client, dest_group)
        data = get_pipeline(client, src_g, pipeline_id, pack=source_pack)
        data = unwrap_item(data)
        result = create_pipeline(client, dst_g, data, pack=dest_pack)
        click.echo(format_output(result))
    except Exception as e:
        handle_error(e)
