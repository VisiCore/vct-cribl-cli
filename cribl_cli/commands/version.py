"""Version control commands for Cribl configuration."""
from __future__ import annotations

import sys

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.version import (
    commit_version,
    get_current_branch,
    get_version_diff,
    get_version_info,
    get_version_status,
    list_branches,
    push_version,
    sync_version,
)
from cribl_cli.api.endpoints.workers import deploy_group
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.group_resolver import resolve_group


@click.group("version", help="Version control operations.")
def version_group():
    pass


@version_group.command("info")
@click.option("-g", "--group", default=None, help="Worker group.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def version_info(group, use_table):
    """Get version control info for a worker group."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = get_version_info(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@version_group.command("status")
@click.option("-g", "--group", default=None, help="Worker group.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def version_status(group, use_table):
    """Get uncommitted changes status."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = get_version_status(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@version_group.command("diff")
@click.option("-g", "--group", default=None, help="Worker group.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def version_diff(group, use_table):
    """Get diff of uncommitted changes."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = get_version_diff(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@version_group.command("commit")
@click.option("-m", "--message", required=True, help="Commit message.")
@click.option("-g", "--group", default=None, help="Worker group.")
def version_commit(message, group):
    """Commit pending configuration changes."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = commit_version(client, g, message)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@version_group.command("push")
@click.option("-g", "--group", default=None, help="Worker group.")
def version_push(group):
    """Push committed changes."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = push_version(client, g)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@version_group.command("sync")
@click.option("-g", "--group", default=None, help="Worker group.")
def version_sync(group):
    """Sync version control state."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = sync_version(client, g)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@version_group.command("branches")
@click.option("-g", "--group", default=None, help="Worker group.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def version_branches(group, use_table):
    """List available branches."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = list_branches(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@version_group.command("current-branch")
@click.option("-g", "--group", default=None, help="Worker group.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def version_current_branch(group, use_table):
    """Get the current active branch."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = get_current_branch(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@version_group.command("deploy")
@click.option("-g", "--group", default=None, help="Worker group.")
@click.option("-m", "--message", default=None, help="Commit message for deploy.")
@click.option(
    "--yes",
    is_flag=True,
    help="Confirm deployment. Required to proceed.",
)
def version_deploy(group, message, yes):
    """Commit and deploy configuration to live workers.

    CRITICAL SAFETY: This pushes config to live workers. You MUST pass --yes
    to confirm. Without --yes the command prints a warning and exits.
    """
    if not yes:
        click.echo(
            "WARNING: This will commit and deploy configuration to live workers.\n"
            "Pass --yes to confirm deployment.",
            err=True,
        )
        sys.exit(1)

    try:
        client = get_client()
        g = resolve_group(client, group)

        # Commit first if a message was provided
        if message:
            click.echo(f"Committing changes: {message}", err=True)
            commit_version(client, g, message)

        click.echo(f"Deploying to worker group: {g}", err=True)
        data = deploy_group(client, g)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)
