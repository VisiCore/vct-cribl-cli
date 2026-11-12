"""Cribl App Platform commands: list, inspect, install, upgrade, uninstall, and backend status."""
from __future__ import annotations

import json

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.apps import (
    get_app,
    get_backend_status,
    install_app,
    invoke_endpoint,
    list_app_policies,
    list_app_proxies,
    list_apps,
    list_backend_endpoints,
    preinstall_check,
    redeploy_backend,
    uninstall_app,
    upgrade_app,
)
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.unwrap import unwrap_item
from cribl_cli.utils.validation import parse_json

_LIST_COLUMNS = ["id", "displayName", "version", "author", "source"]


@click.group("apps", help="Manage Cribl apps (App Platform).")
def apps_group():
    pass


@apps_group.command("list")
@click.option("--table", "use_table", is_flag=True, help="Table output.")
def apps_list(use_table):
    """List installed apps."""
    try:
        client = get_client()
        data = list_apps(client)
        click.echo(format_output(data, table=use_table, columns=_LIST_COLUMNS if use_table else None))
    except Exception as e:
        handle_error(e)


@apps_group.command("get")
@click.argument("app_id")
@click.option("--table", "use_table", is_flag=True, help="Table output.")
def apps_get(app_id, use_table):
    """Show one installed app."""
    try:
        client = get_client()
        data = unwrap_item(get_app(client, app_id))
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@apps_group.command("check")
@click.argument("source")
@click.option("--spec", default=None, help="Version constraint or git ref.")
def apps_check(source, spec):
    """Preview what a package would install (policies, proxies, backend) without installing it.

    SOURCE is a local .tgz/.crbl path, an https:// URL, or git+<repo>.
    """
    try:
        client = get_client()
        data = preinstall_check(client, source, spec=spec)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@apps_group.command("install")
@click.argument("source")
@click.option("--id", "app_id", default=None, help="Override the app id from the package.")
@click.option("--spec", default=None, help="Version constraint or git ref.")
def apps_install(source, app_id, spec):
    """Install an app from a local .tgz/.crbl, an https:// URL, or git+<repo>."""
    try:
        client = get_client()
        data = install_app(client, source, app_id=app_id, spec=spec)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@apps_group.command("upgrade")
@click.argument("app_id")
@click.argument("source")
@click.option("--spec", default=None, help="Version constraint or git ref.")
@click.option("--minor", is_flag=True, help="Limit the upgrade to a minor version.")
def apps_upgrade(app_id, source, spec, minor):
    """Upgrade an installed app from a new package."""
    try:
        client = get_client()
        data = upgrade_app(client, app_id, source, spec=spec, minor=minor)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@apps_group.command("uninstall")
@click.argument("app_id")
@click.option("--yes", "-y", is_flag=True, help="Skip the confirmation prompt.")
def apps_uninstall(app_id, yes):
    """Uninstall an app. This removes its KV store data and cannot be undone."""
    try:
        if not yes:
            click.confirm(f"Uninstall app '{app_id}'? This cannot be undone.", abort=True)
        client = get_client()
        data = uninstall_app(client, app_id)
        click.echo(format_output(data))
    except click.Abort:
        click.echo("Aborted.")
    except Exception as e:
        handle_error(e)


@apps_group.command("backend-status")
@click.argument("app_id")
def apps_backend_status(app_id):
    """Show the live backend deployment state for an app."""
    try:
        client = get_client()
        data = get_backend_status(client, app_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@apps_group.command("endpoints")
@click.argument("app_id")
@click.option("--table", "use_table", is_flag=True, help="Table output.")
def apps_endpoints(app_id, use_table):
    """List the backend endpoints an app declares."""
    try:
        client = get_client()
        data = list_backend_endpoints(client, app_id)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@apps_group.command("redeploy")
@click.argument("app_id")
def apps_redeploy(app_id):
    """Re-attempt a failed backend deployment."""
    try:
        client = get_client()
        data = redeploy_backend(client, app_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@apps_group.command("proxies")
@click.argument("app_id")
def apps_proxies(app_id):
    """Show the external domains an app is allowed to reach."""
    try:
        client = get_client()
        data = list_app_proxies(client, app_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@apps_group.command("policies")
@click.argument("app_id")
def apps_policies(app_id):
    """Show the Cribl API paths an app is granted."""
    try:
        client = get_client()
        data = list_app_policies(client, app_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@apps_group.command("invoke")
@click.argument("app_id")
@click.argument("endpoint")
@click.option("-X", "--method", default="GET", show_default=True, help="HTTP method.")
@click.option("-d", "--data", "body", default=None, help="JSON request body.")
@click.option("-q", "--query", multiple=True, help="Query parameter as key=value (repeatable).")
@click.option("--raw", is_flag=True, help="Print the raw response body instead of pretty JSON.")
def apps_invoke(app_id, endpoint, method, body, query, raw):
    """Call one of an app's deployed backend endpoints and print the response."""
    try:
        client = get_client()
        parsed_body = parse_json(body, "body") if body else None
        params = []  # list of pairs: a key may repeat (e.g. two filter= params)
        for item in query:
            if "=" not in item:
                raise click.BadParameter(f"expected key=value, got {item!r}", param_hint="--query")
            k, v = item.split("=", 1)
            params.append((k, v))
        resp = invoke_endpoint(client, app_id, endpoint, method=method, body=parsed_body, query=params)
        if raw:
            click.echo(resp.text)
            return
        try:
            click.echo(format_output(resp.json()))
        except json.JSONDecodeError:
            click.echo(resp.text)
    except Exception as e:
        handle_error(e)
