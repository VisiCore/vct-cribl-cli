"""Tests for input validation helpers."""

from __future__ import annotations

import pytest

from cribl_cli.utils.validation import parse_json, parse_port


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
