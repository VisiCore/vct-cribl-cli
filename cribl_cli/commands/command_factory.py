"""Factory that generates Click CRUD subcommands from endpoint configurations."""

from __future__ import annotations

from typing import Any

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoint_factory import create_endpoints, resolve_group_for_scope
from cribl_cli.commands.registry import CommandRegistration
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.unwrap import unwrap_item
from cribl_cli.utils.validation import deep_merge, parse_json


def _singular(name: str) -> str:
    if name.endswith("ies"):
        return name[:-3] + "y"
    if name.endswith("ches") or name.endswith("shes") or name.endswith("ses"):
        return name[:-2]
    if name.endswith("s"):
        return name[:-1]
    return name


def _label(name: str) -> str:
    return name.replace("-", " ")


def register_crud_command(parent: click.Group, reg: CommandRegistration) -> None:
    endpoints = create_endpoints(reg.endpoint)
    singular = _singular(reg.name)
    label = _label(reg.name)
    scope = reg.endpoint.scope
    is_singleton = reg.endpoint.singleton

    @parent.group(name=reg.name, help=f"Manage {label}.")
    def group_cmd() -> None:
        pass

    if "list" in reg.operations:
        @group_cmd.command(name="list", help=f"List all {label}.")
        @_scope_options(scope)
        @click.option("--table", "use_table", is_flag=True, help="Table output.")
        @click.pass_context
        def list_cmd(ctx: click.Context, use_table: bool, **kwargs: Any) -> None:
            try:
                client = get_client()
                group = resolve_group_for_scope(client, scope, kwargs.get("group") or kwargs.get("lake"))
                data = endpoints.list(client, group)
                click.echo(format_output(data, table=use_table))
            except Exception as e:
                handle_error(e)

    if "get" in reg.operations:
        @group_cmd.command(name="get", help=f"Get a {_label(singular)}.")
        @click.argument("id", required=not is_singleton)
        @_scope_options(scope)
        @click.option("--table", "use_table", is_flag=True, help="Table output.")
        @click.pass_context
        def get_cmd(ctx: click.Context, id: str, use_table: bool, **kwargs: Any) -> None:
            try:
                client = get_client()
                group = resolve_group_for_scope(client, scope, kwargs.get("group") or kwargs.get("lake"))
                data = endpoints.get(client, group, id)
                data = unwrap_item(data)
                click.echo(format_output(data, table=use_table))
            except Exception as e:
                handle_error(e)

    if "create" in reg.operations:
        @group_cmd.command(name="create", help=f"Create a {_label(singular)}.")
        @click.argument("json_config")
        @_scope_options(scope)
        @click.pass_context
        def create_cmd(ctx: click.Context, json_config: str, **kwargs: Any) -> None:
            try:
                client = get_client()
                group = resolve_group_for_scope(client, scope, kwargs.get("group") or kwargs.get("lake"))
                body = parse_json(json_config, label)
                data = endpoints.create(client, group, body)
                click.echo(format_output(data))
            except Exception as e:
                handle_error(e)

    if "update" in reg.operations:
        @group_cmd.command(name="update", help=f"Update a {_label(singular)}.")
        @click.argument("id", required=not is_singleton)
        @click.argument("json_config")
        @_scope_options(scope)
        @click.pass_context
        def update_cmd(ctx: click.Context, id: str, json_config: str, **kwargs: Any) -> None:
            try:
                client = get_client()
                group = resolve_group_for_scope(client, scope, kwargs.get("group") or kwargs.get("lake"))
                # Merge-on-update: fetch existing, strip server fields, merge
                existing = endpoints.get(client, group, id)
                existing = unwrap_item(existing)
                if isinstance(existing, dict):
                    existing.pop("status", None)
                    existing.pop("notifications", None)
                updates = parse_json(json_config, label)
                merged = deep_merge(existing, updates)
                data = endpoints.update(client, group, id, merged)
                click.echo(format_output(data))
            except Exception as e:
                handle_error(e)

    if "delete" in reg.operations:
        @group_cmd.command(name="delete", help=f"Delete a {_label(singular)}.")
        @click.argument("id")
        @_scope_options(scope)
        @click.pass_context
        def delete_cmd(ctx: click.Context, id: str, **kwargs: Any) -> None:
            try:
                client = get_client()
                group = resolve_group_for_scope(client, scope, kwargs.get("group") or kwargs.get("lake"))
                data = endpoints.delete(client, group, id)
                click.echo(format_output(data))
            except Exception as e:
                handle_error(e)


def _scope_options(scope: str):
    """Return a decorator that adds --group or --lake depending on scope."""

    def decorator(fn):
        if scope == "lake":
            fn = click.option("--lake", required=True, help="Lake ID.")(fn)
        elif scope != "global":
            fn = click.option("--group", "-g", default=None, help="Worker group.")(fn)
        return fn

    return decorator
