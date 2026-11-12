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


# Server-computed fields that must not be sent back on an update.
SERVER_FIELDS: tuple[str, ...] = ("status", "notifications")


def merge_update(existing: object, updates: object) -> dict:
    """Build the body for a merge-on-update PATCH.

    Strips server-only fields from *existing*, then deep-merges *updates* into
    it so a partial nested update (e.g. ``{"conf": {"description": "x"}}``)
    keeps the sibling keys it did not mention.
    """
    if not isinstance(updates, dict):
        raise ValueError("Update must be a JSON object")
    if not isinstance(existing, dict):
        raise ValueError("Cannot update: the existing resource is not a JSON object")
    base = {k: v for k, v in existing.items() if k not in SERVER_FIELDS}
    return deep_merge(base, updates)


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
