"""Metrics commands: aggregated queries, one node's history, and the raw store."""
from __future__ import annotations

import re
from pathlib import Path

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.metrics import build_metrics_query, get_metrics, query_metrics
from cribl_cli.commands.edge import edge_metrics
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error

_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_window(value: str) -> int:
    """'15m', '1h', '900s', '1d' or a bare number of seconds -> seconds."""
    match = re.fullmatch(r"-?(\d+)([smhd]?)", value.strip().lower())
    if not match or int(match.group(1)) == 0:
        raise click.BadParameter(f"expected a duration like 15m, 1h or 900s, got {value!r}")
    return int(match.group(1)) * _UNIT_SECONDS[match.group(2) or "s"]


@click.group("metrics", help="Metrics: aggregated queries (query), one node's history (node), raw store (get).")
def metrics_group():
    pass


@metrics_group.command("query")
@click.option("-a", "--agg", "aggs", multiple=True, required=True,
              help='Aggregation, e.g. \'sum("total.in_events").as("events_in")\' (repeatable). '
                   "Functions: sum, max, min, avg.")
@click.option("-w", "--where", default=None,
              help="Filter on dimensions, e.g. '__worker_group==\"default\"' or 'has_no_dimensions'.")
@click.option("-s", "--split-by", "split_by", multiple=True,
              help="Dimension to group by, e.g. input, output, __worker_group (repeatable).")
@click.option("-e", "--earliest", default="15m", show_default=True,
              help="How far back to look: 15m, 1h, 1d, 900s.")
@click.option("--window", default=None,
              help="Bucket results into time windows of this length (e.g. 5m). Default: one total per group.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def metrics_query_cmd(aggs, where, split_by, earliest, window, use_table):
    """Aggregate metrics on the leader: small, fast, and filtered server-side.

    This is the command to use for throughput and health numbers. Output is
    {"items": [...], "count": N} with one item per group (or per time window).

    \b
    Examples:
      # events in per source over the last hour, one worker group
      cribl metrics query -a 'sum("total.in_events").as("events_in")' \\
          -w '__worker_group=="default"' -s input -e 1h
      # total bytes out in 5-minute buckets
      cribl metrics query -a 'sum("total.out_bytes").as("bytes_out")' \\
          -w has_no_dimensions -e 1h --window 5m
      # worst health value per destination (0 green, 1 yellow, 2 red)
      cribl metrics query -a 'max("health.outputs").as("health")' -s output

    For CPU, memory, disk and load on one node use `cribl metrics node`.
    """
    try:
        payload = build_metrics_query(
            list(aggs), where=where, split_by=list(split_by),
            earliest_seconds=parse_window(earliest),
            window_seconds=parse_window(window) if window else None,
        )
        data = query_metrics(get_client(), payload)
        rows = data.get("results", []) if isinstance(data, dict) else data
        click.echo(format_output({"items": rows, "count": len(rows)}, table=use_table))
    except click.ClickException:
        raise
    except Exception as e:
        handle_error(e)


@metrics_group.command("get")
@click.option("--name", default=None, help="Metric name or regular expression (metricNameFilter).")
@click.option("--filter", "filter_expr", default=None,
              help="Dimension filter expression (filterExpr), e.g. \"__input=='syslog:in_syslog:udp'\".")
@click.option("-e", "--earliest", default=None, help="Start of the range: relative (-15m) or Unix ms.")
@click.option("--latest", default=None, help="End of the range: relative (now) or Unix ms.")
@click.option("--buckets", default=None, type=click.IntRange(min=1), help="Number of time buckets (numBuckets).")
@click.option("-o", "--output", "output", default=None, type=click.Path(dir_okay=False),
              help="Save the response to this file instead of printing it (recommended).")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def metrics_get(name, filter_expr, earliest, latest, buckets, output, use_table):
    """Dump the leader's raw metrics store.

    WARNING: this returns every series and can be hundreds of megabytes and
    take minutes on a busy workspace; raise the global --timeout and save it
    with -o. For a specific number use `cribl metrics query` instead, which
    aggregates on the server and answers in about a second.
    """
    try:
        resp = get_metrics(get_client(), name=name, filter_expr=filter_expr,
                           earliest=earliest, latest=latest, buckets=buckets)
        if output:
            Path(output).write_bytes(resp.content)
            click.echo(format_output({"saved": output, "bytes": len(resp.content)}))
        else:
            click.echo(format_output(resp.json(), table=use_table))
    except Exception as e:
        handle_error(e)


# The same command as `edge metrics`: it works for any connected node, and
# Stream users do not look for it under `edge`.
metrics_group.add_command(edge_metrics, name="node")
