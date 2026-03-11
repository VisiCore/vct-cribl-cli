"""System information, health, and management commands."""
from __future__ import annotations

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.system import (
    get_instance_info,
    get_system_diag,
    get_system_health,
    get_system_info,
    get_system_log,
    get_system_logs,
    get_system_settings,
    get_worker_health,
    reload_system,
    restart_system,
    send_system_diag,
    upgrade_system,
)
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.group_resolver import resolve_group


@click.group("system", help="System information and management.")
def system_group():
    pass


@system_group.command("info")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def system_info_cmd(use_table):
    """Get system information."""
    try:
        client = get_client()
        data = get_system_info(client)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@system_group.command("settings")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def system_settings_cmd(use_table):
    """Get system settings."""
    try:
        client = get_client()
        data = get_system_settings(client)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@system_group.command("health")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def system_health_cmd(use_table):
    """Get overall system health status."""
    try:
        client = get_client()
        data = get_system_health(client)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@system_group.command("instance")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def system_instance_cmd(use_table):
    """Get instance information."""
    try:
        client = get_client()
        data = get_instance_info(client)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@system_group.command("worker-health")
@click.option("-g", "--group", default=None, help="Worker group.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def system_worker_health_cmd(group, use_table):
    """Get health status for a worker group."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = get_worker_health(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@system_group.command("logs")
@click.option("--limit", default=None, type=int, help="Limit number of log entries.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def system_logs_cmd(limit, use_table):
    """Get system logs."""
    try:
        client = get_client()
        data = get_system_logs(client, limit=limit)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@system_group.command("log")
@click.argument("log_type")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def system_log_cmd(log_type, use_table):
    """Get a specific system log by type."""
    try:
        client = get_client()
        data = get_system_log(client, log_type)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@system_group.command("diag")
def system_diag_cmd():
    """Get system diagnostics."""
    try:
        client = get_client()
        data = get_system_diag(client)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@system_group.command("diag-send")
def system_diag_send_cmd():
    """Send system diagnostics to Cribl support."""
    try:
        client = get_client()
        data = send_system_diag(client)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@system_group.command("restart")
def system_restart_cmd():
    """Restart the system."""
    try:
        client = get_client()
        data = restart_system(client)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@system_group.command("reload")
def system_reload_cmd():
    """Reload system configuration."""
    try:
        client = get_client()
        data = reload_system(client)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@system_group.command("upgrade")
def system_upgrade_cmd():
    """Upgrade the system."""
    try:
        client = get_client()
        data = upgrade_system(client)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)
