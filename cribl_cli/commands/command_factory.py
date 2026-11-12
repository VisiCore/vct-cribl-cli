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
from cribl_cli.utils.validation import merge_update, parse_json


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
                data = endpoints.list(client, group, pack=kwargs.get("pack"))
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
                data = endpoints.get(client, group, id, pack=kwargs.get("pack"))
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
                group = resolve_group_for_scope(
                    client, scope, kwargs.get("group") or kwargs.get("lake"), write=True
                )
                body = parse_json(json_config, label)
                data = endpoints.create(client, group, body, pack=kwargs.get("pack"))
                click.echo(format_output(data))
            except Exception as e:
                handle_error(e)

    if "update" in reg.operations:
        def update_cmd(
            ctx: click.Context, json_config: str, id: str | None = None, **kwargs: Any
        ) -> None:
            try:
                client = get_client()
                group = resolve_group_for_scope(
                    client, scope, kwargs.get("group") or kwargs.get("lake"), write=True
                )
                pack = kwargs.get("pack")
                # Merge-on-update: fetch existing, strip server fields, merge
                existing = endpoints.get(client, group, id, pack=pack)
                existing = unwrap_item(existing)
                updates = parse_json(json_config, label)
                merged = merge_update(existing, updates)
                data = endpoints.update(client, group, id, merged, pack=pack)
                click.echo(format_output(data))
            except Exception as e:
                handle_error(e)

        # Decorators are applied by hand so a singleton (auth-settings,
        # git-settings) takes only JSON_CONFIG. An optional ID placed before a
        # required JSON_CONFIG would swallow the JSON and fail to parse.
        update_cmd = click.pass_context(update_cmd)
        update_cmd = _scope_options(scope)(update_cmd)
        update_cmd = click.argument("json_config")(update_cmd)
        if not is_singleton:
            update_cmd = click.argument("id")(update_cmd)
        group_cmd.command(
            name="update",
            help=f"Update a {_label(singular)} by merging JSON_CONFIG into it "
                 "(fields you do not pass are kept).",
        )(update_cmd)

    if "delete" in reg.operations:
        @group_cmd.command(name="delete", help=f"Delete a {_label(singular)}.")
        @click.argument("id")
        @_scope_options(scope)
        @click.pass_context
        def delete_cmd(ctx: click.Context, id: str, **kwargs: Any) -> None:
            try:
                client = get_client()
                group = resolve_group_for_scope(
                    client, scope, kwargs.get("group") or kwargs.get("lake"), write=True
                )
                data = endpoints.delete(client, group, id, pack=kwargs.get("pack"))
                click.echo(format_output(data))
            except Exception as e:
                handle_error(e)


def _scope_options(scope: str):
    """Return a decorator that adds --group/--lake (and --pack for group scope)."""

    def decorator(fn):
        if scope == "searchgroup":
            fn = click.option(
                "--group", "-g", default=None, help="Search group (default: default_search).",
            )(fn)
        elif scope == "lake":
            fn = click.option(
                "--lake", default="default", show_default=True,
                help="Lake ID. Cribl Cloud workspaces have a single lake named 'default'.",
            )(fn)
        elif scope != "global":
            fn = click.option(
                "--pack", "-P", default=None,
                help="Pack ID — scope the request to a pack inside the worker group.",
            )(fn)
            fn = click.option("--group", "-g", default=None, help="Worker group.")(fn)
        return fn

    return decorator
