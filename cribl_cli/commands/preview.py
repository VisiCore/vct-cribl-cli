"""Preview commands."""
from __future__ import annotations

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.preview import run_preview
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.group_resolver import resolve_group
from cribl_cli.utils.validation import parse_json


@click.group("preview", help="Preview pipeline results.")
def preview_group():
    pass


@preview_group.command("run", help="Run a preview.")
@click.argument("json_config")
@click.option("-g", "--group", default=None)
@click.option(
    "--pack", "-P", default=None,
    help="Pack ID — scope the preview to a pack inside the worker group.",
)
def preview_run(json_config, group, pack):
    try:
        client = get_client()
        g = resolve_group(client, group)
        body = parse_json(json_config, "preview config")
        data = run_preview(client, g, body, pack=pack)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)
