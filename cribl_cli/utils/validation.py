"""Input validation helpers."""

from __future__ import annotations

import json as json_mod


def parse_port(value: str, label: str = "port") -> int:
    try:
        port = int(value)
    except ValueError:
        raise ValueError(f"Invalid {label}: {value!r} is not a number")
    if port < 1 or port > 65535:
        raise ValueError(f"Invalid {label}: {port} must be between 1 and 65535")
    return port


def parse_json(value: str, label: str = "JSON") -> dict:
    try:
        return json_mod.loads(value)
    except json_mod.JSONDecodeError as e:
        raise ValueError(f"Invalid {label}: {e}")


def deep_merge(base: dict, updates: dict) -> dict:
    """Recursively merge *updates* into *base*, returning a new dict.

    For nested dicts, values are merged rather than replaced.
    All other types (lists, scalars) are taken from *updates*.
    """
    merged = dict(base)
    for key, value in updates.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
