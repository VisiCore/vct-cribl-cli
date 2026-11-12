"""Search job commands."""
from __future__ import annotations

import sys
import time

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.search import (
    get_search_diag,
    get_search_field_summary,
    get_search_logs,
    get_search_metrics,
    get_search_results,
    get_search_status,
    get_search_timeline,
    run_search,
)
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error


# Job states after which polling can stop. Only "completed" has results.
_TERMINAL_STATES = frozenset({"completed", "failed", "canceled", "cancelled"})


@click.group("search", help="Manage search jobs.")
def search_group():
    pass


@search_group.command("run")
@click.option("-q", "--query", required=True, help="Search query string (Kusto/KQL syntax, e.g. 'dataset=\"logs\" | where level == \"error\" | summarize count() by channel').")
@click.option("--earliest", default=None, help="Start of the time range: relative (-15m, -1h, -7d) or epoch seconds. Example: --earliest -15m")
@click.option("--latest", default=None, help="End of the time range: now, relative (-5m) or epoch seconds. Example: --latest now")
@click.option("-g", "--group", default="default_search", help="Search group.")
@click.option(
    "--poll",
    is_flag=True,
    help="Poll until the search completes, then output results.",
)
@click.option(
    "--timeout",
    default=0,
    type=int,
    help="With --poll, give up after this many seconds (default: 0 = wait indefinitely).",
)
def search_run(query, earliest, latest, group, poll, timeout):
    """Submit a new search job.

    With --poll, waits until the job is completed or failed, then fetches
    and displays the results.
    """
    try:
        client = get_client()
        g = group
        payload: dict = {"query": query}
        if earliest is not None:
            payload["earliest"] = earliest
        if latest is not None:
            payload["latest"] = latest

        data = run_search(client, g, payload)

        if not poll:
            click.echo(format_output(data))
            return

        # Extract job id from response
        job_id = data.get("id") if isinstance(data, dict) else None
        if isinstance(data, dict) and "items" in data:
            items = data["items"]
            if items:
                job_id = items[0].get("id")
        if not job_id:
            click.echo(format_output(data))
            return

        click.echo(f"Search job {job_id} submitted. Polling for completion...", err=True)

        deadline = time.monotonic() + timeout if timeout > 0 else None
        while True:
            if deadline is not None and time.monotonic() >= deadline:
                click.echo(
                    f"Timed out after {timeout}s; job {job_id} is still running. "
                    f"Fetch results later with `cribl search results {job_id} -g {g}`.",
                    err=True,
                )
                sys.exit(1)
            time.sleep(2)
            status_data = get_search_status(client, g, job_id)
            state = None
            if isinstance(status_data, dict):
                # Status may be nested in items[0]
                items = status_data.get("items", [])
                if items and isinstance(items[0], dict):
                    state = items[0].get("status") or items[0].get("state")
                else:
                    state = status_data.get("status") or status_data.get("state")
            click.echo(f"  Status: {state}", err=True)
            if state in _TERMINAL_STATES:
                break

        if state != "completed":
            # failed / canceled: there are no results to fetch
            click.echo(format_output(status_data))
            sys.exit(1)

        results = get_search_results(client, g, job_id)
        click.echo(format_output(results))
    except Exception as e:
        handle_error(e)


# Fields kept in the default `search jobs` listing. The raw job object also
# carries `stages` (~10 KB per job), which makes an unfiltered listing tens of MB.
_JOB_SUMMARY_FIELDS = (
    "id", "status", "type", "user", "displayUsername", "appId",
    "timeCreated", "timeStarted", "timeCompleted", "earliest", "latest", "query",
)


def _job_time(job: dict) -> int:
    return job.get("timeCreated") or job.get("timeStarted") or 0


@search_group.command("jobs")
@click.option("-g", "--group", default="default_search", help="Search group.")
@click.option("-l", "--limit", default=50, type=click.IntRange(min=0), show_default=True,
              help="Max jobs to return, newest first (0 = all).")
@click.option("--status", "status_filter", default=None,
              help="Only jobs in this state (e.g. running, completed, failed).")
@click.option("--full", is_flag=True, help="Return complete job objects instead of a summary.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def search_jobs(group, limit, status_filter, full, use_table):
    """List search jobs, newest first.

    By default returns a summary of the 50 most recent jobs. Use --limit 0 for
    all of them and --full for the complete job objects (large).
    """
    try:
        client = get_client()
        g = group
        resp = client.get(f"/api/v1/m/{g}/search/jobs")
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("items", []) if isinstance(data, dict) else []
        jobs = [j for j in jobs if isinstance(j, dict)]
        if status_filter:
            jobs = [j for j in jobs if j.get("status") == status_filter]
        matched = len(jobs)
        jobs = sorted(jobs, key=_job_time, reverse=True)
        if limit:
            jobs = jobs[:limit]
        if not full:
            jobs = [{k: j[k] for k in _JOB_SUMMARY_FIELDS if k in j} for j in jobs]

        # "total" is what matched; "count" is what is shown after --limit.
        click.echo(format_output({"items": jobs, "count": len(jobs), "total": matched}, table=use_table))
        if len(jobs) < matched:
            click.echo(
                f"Showing the {len(jobs)} most recent of {matched} job(s). Use --limit 0 for all.",
                err=True,
            )
    except Exception as e:
        handle_error(e)


@search_group.command("results")
@click.argument("job_id")
@click.option("-g", "--group", default="default_search", help="Search group.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def search_results(job_id, group, use_table):
    """Get results for a completed search job."""
    try:
        client = get_client()
        g = group
        data = get_search_results(client, g, job_id)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@search_group.command("timeline")
@click.argument("job_id")
@click.option("-g", "--group", default="default_search", help="Search group.")
def search_timeline(job_id, group):
    """Get timeline for a search job."""
    try:
        client = get_client()
        g = group
        data = get_search_timeline(client, g, job_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@search_group.command("field-summary")
@click.argument("job_id")
@click.option("-g", "--group", default="default_search", help="Search group.")
def search_field_summary(job_id, group):
    """Get field summary for a search job."""
    try:
        client = get_client()
        g = group
        data = get_search_field_summary(client, g, job_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@search_group.command("job-logs")
@click.argument("job_id")
@click.option("-g", "--group", default="default_search", help="Search group.")
def search_job_logs(job_id, group):
    """Get logs for a search job."""
    try:
        client = get_client()
        g = group
        data = get_search_logs(client, g, job_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@search_group.command("job-metrics")
@click.argument("job_id")
@click.option("-g", "--group", default="default_search", help="Search group.")
def search_job_metrics(job_id, group):
    """Get metrics for a search job."""
    try:
        client = get_client()
        g = group
        data = get_search_metrics(client, g, job_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@search_group.command("job-diag")
@click.argument("job_id")
@click.option("-g", "--group", default="default_search", help="Search group.")
def search_job_diag(job_id, group):
    """Get diagnostics for a search job."""
    try:
        client = get_client()
        g = group
        data = get_search_diag(client, g, job_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)
