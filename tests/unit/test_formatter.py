"""Tests for output formatting (JSON and table modes)."""

from __future__ import annotations

import json

from cribl_cli.output.formatter import _truncate, format_output


# ---------------------------------------------------------------------------
# JSON output (default)
# ---------------------------------------------------------------------------


def test_format_output_json_default():
    """Default output is pretty-printed JSON."""
    data = {"id": "src1", "type": "syslog"}

    result = format_output(data)

    parsed = json.loads(result)
    assert parsed == data
    # Verify it is indented (pretty-printed)
    assert "\n" in result


# ---------------------------------------------------------------------------
# Table output
# ---------------------------------------------------------------------------


def test_format_output_table_list():
    """Table mode renders a list of dicts as a grid table."""
    data = [
        {"id": "p1", "name": "Pipeline A"},
        {"id": "p2", "name": "Pipeline B"},
    ]

    result = format_output(data, table=True)

    assert "p1" in result
    assert "Pipeline A" in result
    assert "p2" in result
    assert "Pipeline B" in result
    # Grid table format has "+" characters
    assert "+" in result


def test_format_output_table_dict():
    """Table mode renders a single dict as key/value rows."""
    data = {"id": "src1", "type": "syslog", "port": 514}

    result = format_output(data, table=True)

    assert "Key" in result
    assert "Value" in result
    assert "id" in result
    assert "src1" in result
    assert "syslog" in result


def test_format_output_table_empty_list():
    """Table mode with empty list shows '(no results)'."""
    result = format_output([], table=True)

    assert "(no results)" in result


def test_format_output_table_unwraps_items():
    """Table mode unwraps {"items": [...]} wrappers."""
    data = {"items": [{"id": "a"}, {"id": "b"}]}

    result = format_output(data, table=True)

    assert "a" in result
    assert "b" in result


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------


def test_truncate_long_values():
    """Values longer than max_len are truncated with '...'."""
    short = "hello"
    assert _truncate(short) == "hello"

    long_val = "x" * 100
    truncated = _truncate(long_val, max_len=60)
    assert len(truncated) == 60
    assert truncated.endswith("...")


def test_truncate_exact_boundary():
    """A string exactly at max_len is not truncated."""
    val = "a" * 60
    assert _truncate(val, max_len=60) == val
