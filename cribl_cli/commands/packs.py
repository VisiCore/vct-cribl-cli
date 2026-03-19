"""Pack management commands."""
from __future__ import annotations

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.packs import (
    list_packs,
    get_pack,
    create_pack,
    update_pack,
    delete_pack,
    export_pack,
    install_pack,
    upgrade_pack,
)
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.group_resolver import resolve_group
from cribl_cli.utils.unwrap import unwrap_item
from cribl_cli.utils.validation import parse_json

_EXPORT_MODES = click.Choice(["merge", "merge_safe", "default_only"])


@click.group("packs", help="Manage packs.")
def packs_group():
    pass


@packs_group.command("list")
@click.option("-g", "--group", default=None, help="Worker group.")
@click.option("--table", "use_table", is_flag=True, help="Table output.")
def packs_list(group, use_table):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = list_packs(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@packs_group.command("get")
@click.argument("pack_id")
@click.option("-g", "--group", default=None, help="Worker group.")
@click.option("--table", "use_table", is_flag=True, help="Table output.")
def packs_get(pack_id, group, use_table):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = get_pack(client, g, pack_id)
        data = unwrap_item(data)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@packs_group.command("create")
@click.argument("json_config")
@click.option("-g", "--group", default=None, help="Worker group.")
def packs_create(json_config, group):
    try:
        client = get_client()
        g = resolve_group(client, group)
        body = parse_json(json_config, "packs")
        data = create_pack(client, g, body)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@packs_group.command("update")
@click.argument("pack_id")
@click.argument("json_config")
@click.option("-g", "--group", default=None, help="Worker group.")
def packs_update(pack_id, json_config, group):
    try:
        client = get_client()
        g = resolve_group(client, group)
        existing = get_pack(client, g, pack_id)
        existing = unwrap_item(existing)
        if isinstance(existing, dict):
            existing.pop("status", None)
            existing.pop("notifications", None)
        updates = parse_json(json_config, "packs")
        merged = {**existing, **updates}
        data = update_pack(client, g, pack_id, merged)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@packs_group.command("delete")
@click.argument("pack_id")
@click.option("-g", "--group", default=None, help="Worker group.")
def packs_delete(pack_id, group):
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = delete_pack(client, g, pack_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@packs_group.command("export")
@click.argument("pack_id")
@click.option("--mode", "-m", type=_EXPORT_MODES, default="merge_safe", help="Export mode.")
@click.option("--output", "-o", default=None, help="Output file path (default: <pack_id>.crbl).")
@click.option("-g", "--group", default=None, help="Worker group.")
def packs_export(pack_id, mode, output, group):
    """Export a pack as a .crbl file."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = export_pack(client, g, pack_id, mode)
        out_path = output or f"{pack_id}.crbl"
        with open(out_path, "wb") as f:
            f.write(data)
        click.echo(f"Exported to {out_path}")
    except Exception as e:
        handle_error(e)


@packs_group.command("install")
@click.argument("source")
@click.option("-g", "--group", default=None, help="Worker group.")
def packs_install(source, group):
    """Install a pack from a URL or .crbl path."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = install_pack(client, g, source)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@packs_group.command("upgrade")
@click.argument("pack_id")
@click.argument("source")
@click.option("--mode", "-m", type=_EXPORT_MODES, default="merge", help="Upgrade mode.")
@click.option("-g", "--group", default=None, help="Worker group.")
def packs_upgrade(pack_id, source, mode, group):
    """Upgrade a pack from a URL or .crbl path."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = upgrade_pack(client, g, pack_id, source, mode)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)
