"""Tests for input validation helpers."""

from __future__ import annotations

import pytest

from cribl_cli.utils.validation import deep_merge, parse_json, parse_port


# ---------------------------------------------------------------------------
# parse_port
# ---------------------------------------------------------------------------


def test_parse_port_valid():
    """Valid port number string returns the integer."""
    assert parse_port("8080") == 8080
    assert parse_port("1") == 1
    assert parse_port("65535") == 65535


def test_parse_port_invalid_string():
    """Non-numeric string raises ValueError."""
    with pytest.raises(ValueError, match="not a number"):
        parse_port("abc")


def test_parse_port_out_of_range():
    """Port outside 1-65535 raises ValueError."""
    with pytest.raises(ValueError, match="must be between 1 and 65535"):
        parse_port("0")

    with pytest.raises(ValueError, match="must be between 1 and 65535"):
        parse_port("65536")

    with pytest.raises(ValueError, match="must be between 1 and 65535"):
        parse_port("-1")


# ---------------------------------------------------------------------------
# parse_json
# ---------------------------------------------------------------------------


def test_parse_json_valid():
    """Valid JSON string returns the parsed dict."""
    result = parse_json('{"key": "value", "num": 42}')

    assert result == {"key": "value", "num": 42}


def test_parse_json_invalid():
    """Invalid JSON string raises ValueError."""
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_json("{bad json}")


# ---------------------------------------------------------------------------
# deep_merge
# ---------------------------------------------------------------------------


def test_deep_merge_shallow_keys():
    """Top-level keys from updates overwrite base."""
    assert deep_merge({"a": 1, "b": 2}, {"b": 3}) == {"a": 1, "b": 3}


def test_deep_merge_nested_dicts():
    """Nested dicts are merged recursively, not replaced."""
    base = {"schedule": {"cronSchedule": "0 * * * *", "enabled": True, "tz": "UTC"}}
    updates = {"schedule": {"cronSchedule": "*/5 * * * *"}}
    result = deep_merge(base, updates)

    assert result["schedule"]["cronSchedule"] == "*/5 * * * *"
    assert result["schedule"]["enabled"] is True
    assert result["schedule"]["tz"] == "UTC"


def test_deep_merge_deeply_nested():
    """Merge works at multiple nesting levels."""
    base = {"a": {"b": {"c": 1, "d": 2}, "e": 3}}
    updates = {"a": {"b": {"c": 99}}}
    result = deep_merge(base, updates)

    assert result == {"a": {"b": {"c": 99, "d": 2}, "e": 3}}


def test_deep_merge_new_keys():
    """Keys in updates that don't exist in base are added."""
    assert deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_deep_merge_list_replaced():
    """Lists are replaced, not merged."""
    base = {"tags": ["a", "b"]}
    updates = {"tags": ["c"]}
    assert deep_merge(base, updates) == {"tags": ["c"]}


def test_deep_merge_does_not_mutate():
    """Original dicts are not modified."""
    base = {"a": {"b": 1}}
    updates = {"a": {"c": 2}}
    result = deep_merge(base, updates)

    assert result == {"a": {"b": 1, "c": 2}}
    assert base == {"a": {"b": 1}}
    assert updates == {"a": {"c": 2}}
