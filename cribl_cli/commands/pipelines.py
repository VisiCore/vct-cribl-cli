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


@click.group("pipelines", help="Manage pipelines.")
def pipelines_group():
    pass


@pipelines_group.command("list")
@click.option("-g", "--group", default=None)
@click.option("--table", "use_table", is_flag=True)
def pipelines_list(group, use_table):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = list_pipelines(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@pipelines_group.command("get")
@click.argument("pipeline_id")
@click.option("-g", "--group", default=None)
@click.option("--table", "use_table", is_flag=True)
def pipelines_get(pipeline_id, group, use_table):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = get_pipeline(client, g, pipeline_id)
        data = unwrap_item(data)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@pipelines_group.command("create")
@click.argument("json_config")
@click.option("-g", "--group", default=None)
def pipelines_create(json_config, group):
    try:
        client = get_client()
        g = resolve_group(client, group)
        body = parse_json(json_config, "pipeline config")
        data = create_pipeline(client, g, body)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@pipelines_group.command("update")
@click.argument("pipeline_id")
@click.argument("json_config")
@click.option("-g", "--group", default=None)
def pipelines_update(pipeline_id, json_config, group):
    try:
        client = get_client()
        g = resolve_group(client, group)
        existing = get_pipeline(client, g, pipeline_id)
        existing = unwrap_item(existing)
        updates = parse_json(json_config, "pipeline config")
        merged = {**existing, **updates}
        data = update_pipeline(client, g, pipeline_id, merged)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@pipelines_group.command("delete")
@click.argument("pipeline_id")
@click.option("-g", "--group", default=None)
def pipelines_delete(pipeline_id, group):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = delete_pipeline(client, g, pipeline_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@pipelines_group.command("clone", help="Clone a pipeline from one group to another.")
@click.argument("pipeline_id")
@click.option("--source-group", required=True, help="Source worker group.")
@click.option("--dest-group", required=True, help="Destination worker group.")
def pipelines_clone(pipeline_id, source_group, dest_group):
    try:
        client = get_client()
        src_g = resolve_group(client, source_group)
        dst_g = resolve_group(client, dest_group)
        data = get_pipeline(client, src_g, pipeline_id)
        data = unwrap_item(data)
        result = create_pipeline(client, dst_g, data)
        click.echo(format_output(result))
    except Exception as e:
        handle_error(e)
