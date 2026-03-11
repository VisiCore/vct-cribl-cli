"""Job and collector management commands."""
from __future__ import annotations

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.jobs import (
    cancel_job,
    get_job,
    list_job_configs,
    list_jobs,
    pause_job,
    resume_job,
    run_job,
)
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.group_resolver import resolve_group


@click.group("jobs", help="Manage jobs and collectors.")
def jobs_group():
    pass


@jobs_group.command("list")
@click.option("-g", "--group", default=None, help="Worker group.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def jobs_list(group, use_table):
    """List all jobs in a worker group."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = list_jobs(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@jobs_group.command("get")
@click.argument("job_id")
@click.option("-g", "--group", default=None, help="Worker group.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def jobs_get(job_id, group, use_table):
    """Get a specific job by ID."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = get_job(client, g, job_id)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@jobs_group.command("run")
@click.argument("job_id")
@click.option("-g", "--group", default=None, help="Worker group.")
def jobs_run(job_id, group):
    """Run (trigger) an existing job by its collector config ID."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = run_job(client, g, job_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@jobs_group.command("cancel")
@click.argument("job_id")
@click.option("-g", "--group", default=None, help="Worker group.")
def jobs_cancel(job_id, group):
    """Cancel a running job."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = cancel_job(client, g, job_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@jobs_group.command("pause")
@click.argument("job_id")
@click.option("-g", "--group", default=None, help="Worker group.")
def jobs_pause(job_id, group):
    """Pause a running job."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = pause_job(client, g, job_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@jobs_group.command("resume")
@click.argument("job_id")
@click.option("-g", "--group", default=None, help="Worker group.")
def jobs_resume(job_id, group):
    """Resume a paused job."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = resume_job(client, g, job_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@jobs_group.command("list-configs")
@click.option("-g", "--group", default=None, help="Worker group.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def jobs_list_configs(group, use_table):
    """List all collector configurations (not job instances)."""
    try:
        client = get_client()
        g = resolve_group(client, group)
        data = list_job_configs(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)
