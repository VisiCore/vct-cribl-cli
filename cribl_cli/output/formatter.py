"""Output formatting: JSON (default) and table mode."""

from __future__ import annotations

import json
from typing import Any

import click


def _get_fields_from_context() -> list[str] | None:
    """Read --fields from the Click context if available."""
    try:
        ctx = click.get_current_context(silent=True)
        if ctx:
            obj = ctx.find_root().params.get("fields") or (ctx.obj or {}).get("fields")
            if obj:
                return [f.strip() for f in obj.split(",")]
    except RuntimeError:
        pass
    return None


def _filter_fields(data: Any, fields: list[str]) -> Any:
    """Filter data to only include the specified fields."""
    if isinstance(data, dict) and "items" in data:
        return {
            "items": [_filter_dict(item, fields) for item in data["items"] if isinstance(item, dict)],
            "count": data.get("count", len(data["items"])),
        }
    if isinstance(data, list):
        return [_filter_dict(item, fields) if isinstance(item, dict) else item for item in data]
    if isinstance(data, dict):
        return _filter_dict(data, fields)
    return data


def _filter_dict(d: dict, fields: list[str]) -> dict:
    return {k: v for k, v in d.items() if k in fields}


def format_output(data: Any, *, table: bool = False, columns: list[str] | None = None) -> str:
    fields = _get_fields_from_context()
    if fields:
        data = _filter_fields(data, fields)
        if not columns:
            columns = fields
    if not table:
        return json.dumps(data, indent=2)
    return format_table(data, columns)


def format_table(data: Any, columns: list[str] | None = None) -> str:
    from tabulate import tabulate

    if isinstance(data, dict) and "items" in data:
        data = data["items"]

    if isinstance(data, list):
        if not data:
            return "(no results)"
        if isinstance(data[0], dict):
            cols = columns or list(data[0].keys())
            rows = []
            for item in data:
                rows.append([_truncate(_format_value(item.get(c))) for c in cols])
            return tabulate(rows, headers=cols, tablefmt="grid")
        return tabulate([[_truncate(str(v))] for v in data], tablefmt="grid")

    if isinstance(data, dict):
        rows = [[k, _truncate(_format_value(v))] for k, v in data.items()]
        return tabulate(rows, headers=["Key", "Value"], tablefmt="grid")

    return str(data)


def _format_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    if value is None:
        return ""
    return str(value)


def _truncate(s: str, max_len: int = 60) -> str:
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s
