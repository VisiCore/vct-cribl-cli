"""Raw API escape hatch: call any Cribl REST path with the CLI's auth and profile."""
from __future__ import annotations

import json

import click

from cribl_cli.api.client import get_client
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.validation import parse_json

_METHODS = click.Choice(["GET", "POST", "PUT", "PATCH", "DELETE"], case_sensitive=False)


@click.command("api", help="Call an arbitrary Cribl API path (e.g. `api GET /api/v1/apps`).")
@click.argument("method", type=_METHODS)
@click.argument("path")
@click.option("-d", "--data", "body", default=None, help="JSON request body.")
@click.option("-q", "--query", multiple=True, help="Query parameter as key=value (repeatable).")
@click.option("-H", "--header", "headers", multiple=True, help="Extra header as Name: value (repeatable).")
@click.option("--raw", is_flag=True, help="Print the raw response body instead of pretty JSON.")
@click.option("--status", "show_status", is_flag=True, help="Print the HTTP status line to stderr.")
def api_cmd(method, path, body, query, headers, raw, show_status):
    """Send one request and print the response. Paths must start with /api/."""
    try:
        if not path.startswith("/"):
            raise click.BadParameter("path must start with '/'", param_hint="PATH")
        client = get_client()
        params = {}
        for item in query:
            if "=" not in item:
                raise click.BadParameter(f"expected key=value, got {item!r}", param_hint="--query")
            k, v = item.split("=", 1)
            params[k] = v
        hdrs = {}
        for item in headers:
            if ":" not in item:
                raise click.BadParameter(f"expected Name: value, got {item!r}", param_hint="--header")
            k, v = item.split(":", 1)
            hdrs[k.strip()] = v.strip()
        parsed_body = parse_json(body, "body") if body else None
        resp = client.request(method.upper(), path, json=parsed_body, params=params or None, headers=hdrs or None)
        if show_status:
            click.echo(f"HTTP {resp.status_code}", err=True)
        if raw:
            click.echo(resp.text)
        else:
            try:
                click.echo(format_output(resp.json()))
            except json.JSONDecodeError:
                click.echo(resp.text)
        if resp.status_code >= 400:
            raise SystemExit(1)
    except SystemExit:
        raise
    except Exception as e:
        handle_error(e)
