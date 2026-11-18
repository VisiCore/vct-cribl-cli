"""Lookup file transfer: `lookups download` and `lookups upload`.

The `lookups` group itself (list/get/create/update/delete of the lookup
object) is generated from the registry; these two subcommands are attached to
it because moving the file's content needs more than one CRUD call.
"""
from __future__ import annotations

import sys
from pathlib import Path

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.lookups import download_lookup, upload_lookup
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.group_resolver import resolve_group

_GROUP_OPT = click.option(
    "-g", "--group", default=None,
    help="Worker group or fleet; use default_search for Cribl Search lookups.",
)


@click.command("download")
@click.argument("id")
@_GROUP_OPT
@click.option("-o", "--output", "output", default=None, type=click.Path(dir_okay=False),
              help="Save to this file. Without it the file is written to stdout.")
def lookups_download(id, group, output):
    """Download a lookup's file exactly as stored (CSV, .gz, .mmdb).

    ID is the lookup's id as shown by `lookups list`, e.g. hosts.csv.

    \b
    Examples:
      cribl lookups download hosts.csv -g default -o hosts.csv
      cribl lookups download hosts.csv -g default | head
    """
    try:
        client = get_client()
        content = download_lookup(client, resolve_group(client, group), id)
        if output:
            Path(output).write_bytes(content)
            click.echo(format_output({"id": id, "saved": output, "bytes": len(content)}))
        else:
            sys.stdout.buffer.write(content)
            sys.stdout.buffer.flush()
    except Exception as e:
        handle_error(e)


@click.command("upload")
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@_GROUP_OPT
@click.option("--id", "lookup_id", default=None,
              help="Lookup id to create or replace (default: the file's name).")
def lookups_upload(file, group, lookup_id):
    """Upload FILE as a lookup: creates it, or replaces the file if it exists.

    The change is staged in the group like any other edit — commit and deploy
    it afterwards (`version commit`, `version deploy`).

    \b
    Examples:
      cribl lookups upload hosts.csv -g default
      cribl lookups upload ./export.csv --id hosts.csv -g default
      cribl --dry-run lookups upload hosts.csv -g default
    """
    try:
        client = get_client()
        target = resolve_group(client, group, write=True)
        path = Path(file)
        result = upload_lookup(client, target, lookup_id or path.name, path.read_bytes())
        click.echo(format_output(result))
    except Exception as e:
        handle_error(e)


def attach(lookups_group: click.Group) -> None:
    """Add the file-transfer subcommands to the generated `lookups` group."""
    lookups_group.add_command(lookups_download)
    lookups_group.add_command(lookups_upload)
