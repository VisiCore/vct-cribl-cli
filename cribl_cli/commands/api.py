"""Raw API access: call any Cribl REST path with the CLI's auth and profile.

`cribl api` is the escape hatch for anything without a dedicated command, and
`cribl api-spec` searches the bundled index of the API to find the path.
Together they mean no task should need a hand-written HTTP script.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from cribl_cli.api.client import get_client
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.api_index import cli_endpoints, load_operations, normalize
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.validation import parse_json

_METHODS = click.Choice(["GET", "POST", "PUT", "PATCH", "DELETE"], case_sensitive=False)


def build_path(path: str, group: str | None = None) -> str:
    """Turn a path as written in the API reference into a full request path.

    The reference lists paths relative to the API root and without the group
    (``/pipelines``); the server wants ``/api/v1/m/<group>/pipelines``. A path
    that already starts with ``/api/`` (or is a static file) is left as is.
    """
    if not path.startswith("/"):
        raise click.BadParameter("path must start with '/'", param_hint="PATH")
    if path.startswith(("/api/", "/static/")):
        if group:
            raise click.BadParameter(
                "-g/--group only applies to a path relative to the API root "
                "(e.g. /pipelines), not one that already starts with /api/",
                param_hint="--group",
            )
        return path
    return f"/api/v1/m/{group}{path}" if group else f"/api/v1{path}"


def _read_body(body: str | None):
    """Parse -d/--data: inline JSON, @file, or @- for stdin."""
    if body is None:
        return None
    if body.startswith("@"):
        source = body[1:]
        text = sys.stdin.read() if source == "-" else Path(source).read_text()
        return parse_json(text, f"body from {'stdin' if source == '-' else source}")
    return parse_json(body, "body")


@click.command("api")
@click.argument("method", type=_METHODS)
@click.argument("path")
@click.option("-g", "--group", default=None,
              help="Worker group / fleet / search group: sends PATH under /m/<group>/.")
@click.option("-d", "--data", "body", default=None,
              help="JSON request body: inline, @FILE, or @- to read stdin.")
@click.option("--upload", "upload", default=None, type=click.Path(exists=True, dir_okay=False),
              help="Send this file's bytes as the request body (e.g. a lookup CSV or a .crbl pack).")
@click.option("-q", "--query", multiple=True, help="Query parameter as key=value (repeatable).")
@click.option("-H", "--header", "headers", multiple=True, help="Extra header as Name: value (repeatable).")
@click.option("-o", "--output", "output", default=None, type=click.Path(dir_okay=False),
              help="Save the response body to this file (binary-safe) instead of printing it.")
@click.option("--raw", is_flag=True, help="Print the raw response body instead of pretty JSON.")
@click.option("--status", "show_status", is_flag=True, help="Print the HTTP status line to stderr.")
def api_cmd(method, path, group, body, upload, query, headers, output, raw, show_status):
    """Call any Cribl API endpoint with the CLI's auth.

    PATH may be written as in the API reference (/system/users) or in full
    (/api/v1/system/users). For anything that lives in a worker group, fleet or
    search group, add -g: `cribl api GET /pipelines -g default` requests
    /api/v1/m/default/pipelines.

    Find endpoints with `cribl api-spec search <words>`.

    \b
    Examples:
      cribl api GET /system/users
      cribl api GET /lib/jobs -g default -q limit=5
      cribl api POST /lib/regex -g default -d @regex.json
      cribl api PUT /system/lookups -g default -q filename=hosts.csv --upload hosts.csv
      cribl api GET /packs/my-pack/export -g default -q mode=merge -o my-pack.crbl
      cribl --dry-run api DELETE /lib/regex/my-regex -g default

    Exits 1 when the server answers with an HTTP error (the body is still printed).
    """
    try:
        url = build_path(path, group)
        if body is not None and upload:
            raise click.UsageError("Use either -d/--data or --upload, not both.")
        client = get_client()
        params = []  # list of pairs: a key may repeat (e.g. two filter= params)
        for item in query:
            if "=" not in item:
                raise click.BadParameter(f"expected key=value, got {item!r}", param_hint="--query")
            k, v = item.split("=", 1)
            params.append((k, v))
        hdrs = {}
        for item in headers:
            if ":" not in item:
                raise click.BadParameter(f"expected Name: value, got {item!r}", param_hint="--header")
            k, v = item.split(":", 1)
            hdrs[k.strip()] = v.strip()

        kwargs: dict = {"params": params or None}
        if upload:
            kwargs["content"] = Path(upload).read_bytes()
            hdrs.setdefault("Content-Type", "application/octet-stream")
        else:
            kwargs["json"] = _read_body(body)
        resp = client.request(method.upper(), url, headers=hdrs or None, **kwargs)

        if show_status:
            click.echo(f"HTTP {resp.status_code}", err=True)
        if output:
            Path(output).write_bytes(resp.content)
            click.echo(format_output({"saved": output, "bytes": len(resp.content), "status": resp.status_code}))
        elif raw:
            click.echo(resp.text)
        else:
            try:
                click.echo(format_output(resp.json()))
            except json.JSONDecodeError:
                click.echo(resp.text)
        if resp.status_code >= 400:
            raise SystemExit(1)
    except (SystemExit, click.UsageError):
        raise
    except Exception as e:
        handle_error(e)


# ---------------------------------------------------------------------------
# api-spec: search the bundled index of the API
# ---------------------------------------------------------------------------

@click.group("api-spec", help="Search the Cribl API reference bundled with the CLI.")
def api_spec_group():
    pass


def _covered() -> set[tuple[str, str]]:
    return set(cli_endpoints())


def _row(op: dict, covered: set[tuple[str, str]]) -> dict:
    return {
        "method": op["method"],
        "path": op["path"],
        "tag": op["tag"],
        "summary": op["summary"],
        # True when a dedicated command already calls this endpoint.
        "has_command": (op["method"], normalize(op["path"])) in covered,
        "call": f"cribl api {op['method']} {op['path']}",
    }


@api_spec_group.command("search")
@click.argument("words", nargs=-1)
@click.option("-m", "--method", "method", type=_METHODS, default=None, help="Only this HTTP method.")
@click.option("-t", "--tag", default=None, help="Only this area (see `api-spec tags`).")
@click.option("--missing", is_flag=True, help="Only endpoints with no dedicated command.")
@click.option("-l", "--limit", default=50, type=click.IntRange(min=0), show_default=True,
              help="Max results (0 = all).")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def api_spec_search(words, method, tag, missing, limit, use_table):
    """Find API endpoints whose path, area or summary contains every WORD.

    Each result includes the `cribl api` call to make. Paths are relative to the
    API root; add `-g <group>` to that call for anything inside a worker group,
    fleet or search group.

    \b
    Examples:
      cribl api-spec search lookups
      cribl api-spec search secret reveal
      cribl api-spec search --tag search --method POST
      cribl api-spec search --missing --tag lake
    """
    try:
        covered = _covered()
        needles = [w.lower() for w in words]
        rows = []
        for op in load_operations():
            if method and op["method"] != method.upper():
                continue
            if tag and op["tag"].lower() != tag.lower():
                continue
            hay = f"{op['path']} {op['tag']} {op['summary']}".lower()
            if not all(n in hay for n in needles):
                continue
            row = _row(op, covered)
            if missing and row["has_command"]:
                continue
            rows.append(row)
        matched = len(rows)
        if limit:
            rows = rows[:limit]
        cols = ["method", "path", "tag", "has_command", "summary"] if use_table else None
        click.echo(format_output({"items": rows, "count": len(rows), "total": matched},
                                 table=use_table, columns=cols))
        if len(rows) < matched:
            click.echo(f"Showing {len(rows)} of {matched} match(es). Use --limit 0 for all.", err=True)
    except Exception as e:
        handle_error(e)


@api_spec_group.command("tags")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def api_spec_tags(use_table):
    """List the API's areas with how many endpoints each has, and how many
    already have a dedicated command."""
    try:
        covered = _covered()
        stats: dict[str, dict] = {}
        for op in load_operations():
            s = stats.setdefault(op["tag"] or "(untagged)", {"tag": op["tag"] or "(untagged)", "endpoints": 0, "with_command": 0})
            s["endpoints"] += 1
            if (op["method"], normalize(op["path"])) in covered:
                s["with_command"] += 1
        rows = sorted(stats.values(), key=lambda s: -s["endpoints"])
        click.echo(format_output(rows, table=use_table))
    except Exception as e:
        handle_error(e)
