"""Whole-group config export/import for worker groups and edge fleets."""
from __future__ import annotations

import json
import sys

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.version import commit_version
from cribl_cli.api.endpoints.workers import deploy_group
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.group_resolver import resolve_group
from cribl_cli.utils.group_transfer import (
    apply,
    collect,
    format_caveat,
    read_input,
    write_dir,
)


@click.group("groups", help="Export and import all config for a worker group or edge fleet.")
def groups_group():
    pass


@groups_group.command("export", help="Pull all config for one worker group or edge fleet.")
@click.argument("group")
@click.option("--out-dir", default=None, help="Write one file per resource type under <out-dir>/<group>/.")
@click.option("--include-sensitive", is_flag=True, help="Include secrets, credentials, and certificates.")
@click.option("--include-packs", is_flag=True, help="Include pack configurations (definitions only).")
@click.option("--include-lookups", is_flag=True, help="Include lookup configurations (definitions only).")
@click.option("--table", "use_table", is_flag=True, help="Table output (stdout mode only).")
def groups_export(group, out_dir, include_sensitive, include_packs, include_lookups, use_table):
    """Export every group-scoped resource for GROUP (a worker group or edge fleet).

    Outputs one aggregated JSON object to stdout, or use --out-dir to write a
    file per resource type. Sensitive resources are excluded unless
    --include-sensitive is passed; a caveat of everything skipped or failed is
    always printed to stderr.
    """
    try:
        client = get_client()
        g = resolve_group(client, group)
        result = collect(
            client, g, include_sensitive=include_sensitive,
            include_packs=include_packs, include_lookups=include_lookups
        )

        if out_dir:
            base = write_dir(result, out_dir)
            click.echo(format_output({"written": str(base), "resource_types": len(result["resources"])}))
        else:
            click.echo(format_output(result, table=use_table))

        click.echo(format_caveat(result), err=True)
    except Exception as e:
        handle_error(e)


@groups_group.command("import", help="Push exported config into a worker group or edge fleet.")
@click.argument("group")
@click.option("--in", "in_path", default=None, help="Read payload from a JSON file or an --out-dir directory.")
@click.option("--with-routes", is_flag=True, help="Also replace the route table (wholesale; off by default).")
@click.option("--with-packs", is_flag=True, help="Also import packs (off by default).")
@click.option("--with-lookups", is_flag=True, help="Also import lookups (off by default).")
@click.option("--commit", "commit_message", default=None, help="Commit staged changes with this message.")
@click.option("--deploy", is_flag=True, help="Commit and deploy to live workers (requires --yes).")
@click.option("--yes", is_flag=True, help="Confirm deployment.")
def groups_import(group, in_path, with_routes, with_packs, with_lookups, commit_message, deploy, yes):
    """Import config into GROUP (a worker group or edge fleet).

    Reads an export payload from --in (a file or an --out-dir directory) or from
    stdin, then upserts each resource. The route table is left untouched unless
    --with-routes is passed. Nothing is deployed: changes stay staged until you
    review them and deploy explicitly, or pass --deploy --yes.
    """
    try:
        if in_path:
            payload = read_input(in_path)
        else:
            raw = sys.stdin.read()
            if not raw.strip():
                raise ValueError("No input. Pass --in FILE|DIR or pipe an export JSON on stdin.")
            payload = json.loads(raw)

        client = get_client()
        target = resolve_group(client, group)

        if deploy and not yes:
            click.echo(
                "WARNING: --deploy commits and pushes config to live workers. Pass --yes to confirm.",
                err=True,
            )
            sys.exit(1)

        report = apply(
            client, target, payload,
            with_routes=with_routes, with_packs=with_packs, with_lookups=with_lookups
        )
        click.echo(format_output(report))

        if commit_message or deploy:
            message = commit_message or "Import group config"
            commit_version(client, target, message)
            click.echo(f"Committed: {message}", err=True)

        if deploy:
            deploy_group(client, target)
            click.echo(f"Deployed to {target}.", err=True)
        else:
            click.echo(
                f"Config staged (not deployed). Review with "
                f"`cribl version status -g {target}` / `cribl version diff -g {target}`, "
                f"then `cribl version deploy -g {target} --yes`.",
                err=True,
            )
    except Exception as e:
        handle_error(e)
