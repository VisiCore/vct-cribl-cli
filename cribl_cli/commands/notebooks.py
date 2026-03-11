"""Notebook management commands."""
from __future__ import annotations

import base64
import json as _json
import uuid

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.notebooks import (
    list_notebooks, get_notebook, create_notebook, add_notebook_query, delete_notebook,
)
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.unwrap import unwrap_item
from cribl_cli.utils.validation import parse_json


def _get_token_identity() -> tuple[str, str]:
    """Extract user identity (sub, display name) from the current JWT token.

    Returns (subject_id, display_name). Falls back to empty strings on failure.
    """
    try:
        from cribl_cli.config.loader import load_config
        from cribl_cli.auth.oauth import get_access_token
        cfg = load_config()
        token = get_access_token(cfg)
        parts = token.split(".")
        if len(parts) < 2:
            return "", ""
        payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
        claims = _json.loads(base64.b64decode(payload))
        sub = claims.get("sub", "")
        display = (
            claims.get("https://cribl.cloud/name", "")
            or claims.get("https://cribl.cloud/email", "")
            or sub
        )
        return sub, display
    except Exception:
        return "", ""


@click.group("notebooks", help="Manage notebooks.")
def notebooks_group():
    pass


@notebooks_group.command("list")
@click.option("-g", "--group", default="default_search")
@click.option("--table", "use_table", is_flag=True)
def notebooks_list(group, use_table):
    try:
        client = get_client()
        g = group
        data = list_notebooks(client, g)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@notebooks_group.command("get")
@click.argument("notebook_id")
@click.option("-g", "--group", default="default_search")
@click.option("--table", "use_table", is_flag=True)
def notebooks_get(notebook_id, group, use_table):
    try:
        client = get_client()
        g = group
        data = get_notebook(client, g, notebook_id)
        data = unwrap_item(data)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@notebooks_group.command("create")
@click.option("--name", required=True, help="Notebook name.")
@click.option("--description", default=None, help="Notebook description.")
@click.option("--markdown", default=None, help="Initial markdown content for the notebook.")
@click.option("-g", "--group", default="default_search")
def notebooks_create(name, description, markdown, group):
    try:
        import time as _time
        client = get_client()
        g = group  # Notebooks live in search groups, don't resolve to a stream group
        now = int(_time.time() * 1000)
        sub, display = _get_token_identity()
        nb_id = f"notebook-{uuid.uuid4()}"

        info_block = {
            "created": now,
            "modified": now,
            "name": name,
        }
        if sub:
            info_block.update({
                "createdBy": sub,
                "modifiedBy": sub,
                "displayCreatedBy": display,
                "displayModifiedBy": display,
            })

        body = {
            "id": nb_id,
            "info": info_block,
            "sections": [],
        }
        if description:
            body["description"] = description
        if markdown:
            section_info = {"created": now, "modified": now}
            if sub:
                section_info.update({
                    "createdBy": sub,
                    "modifiedBy": sub,
                    "displayCreatedBy": display,
                    "displayModifiedBy": display,
                })
            body["sections"].append({
                "id": f"section-{uuid.uuid4()}",
                "type": "markdown.default",
                "variant": "markdown",
                "info": section_info,
                "config": {"markdown": markdown},
            })
        data = create_notebook(client, g, body)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@notebooks_group.command("add", help="Add a section to a notebook.")
@click.argument("notebook_id")
@click.argument("query_json")
@click.option("-g", "--group", default="default_search")
def notebooks_add(notebook_id, query_json, group):
    try:
        client = get_client()
        g = group
        query = parse_json(query_json, "query config")
        data = add_notebook_query(client, g, notebook_id, query)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@notebooks_group.command("delete")
@click.argument("notebook_id")
@click.option("-g", "--group", default="default_search")
def notebooks_delete(notebook_id, group):
    try:
        client = get_client()
        g = group
        data = delete_notebook(client, g, notebook_id)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)
