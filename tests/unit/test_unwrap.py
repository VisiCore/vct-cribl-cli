"""Tests for single-item response unwrapping."""

from __future__ import annotations

from cribl_cli.utils.unwrap import unwrap_item


def test_unwrap_single_item():
    """A dict with items containing exactly one element returns that element."""
    data = {"items": [{"id": "abc", "name": "Thing"}]}

    result = unwrap_item(data)

    assert result == {"id": "abc", "name": "Thing"}


def test_unwrap_multiple_items_returns_raw():
    """A dict with multiple items is returned unchanged."""
    data = {"items": [{"id": "a"}, {"id": "b"}]}

    result = unwrap_item(data)

    assert result is data


def test_unwrap_non_dict_returns_raw():
    """Non-dict values are returned unchanged."""
    assert unwrap_item("hello") == "hello"
    assert unwrap_item(42) == 42
    assert unwrap_item([1, 2, 3]) == [1, 2, 3]


def test_unwrap_dict_without_items_returns_raw():
    """A dict without an 'items' key is returned unchanged."""
    data = {"id": "abc", "name": "Thing"}

    result = unwrap_item(data)

    assert result is data


def test_unwrap_empty_items_returns_raw():
    """A dict with an empty items list is returned unchanged."""
    data = {"items": []}

    result = unwrap_item(data)

    assert result is data
