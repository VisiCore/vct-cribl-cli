"""Output formatting: JSON (default) and table mode."""

from __future__ import annotations

import json
from typing import Any


def format_output(data: Any, *, table: bool = False, columns: list[str] | None = None) -> str:
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
