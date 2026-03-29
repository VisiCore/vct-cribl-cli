"""Tests for org ID extraction utility."""
from __future__ import annotations

import pytest

from cribl_cli.utils.org import extract_org_id


def test_standard_cloud_url():
    assert extract_org_id("https://myorg.cribl.cloud") == "myorg"


def test_trailing_slash():
    assert extract_org_id("https://myorg.cribl.cloud/") == "myorg"


def test_hyphenated_org():
    assert extract_org_id("https://test-org.cribl.cloud") == "test-org"


def test_localhost_raises():
    with pytest.raises(ValueError, match="Billing commands require a Cribl Cloud URL"):
        extract_org_id("https://localhost:9000")


def test_onprem_raises():
    with pytest.raises(ValueError, match="Billing commands require a Cribl Cloud URL"):
        extract_org_id("https://cribl.internal.company.com")


def test_bare_cribl_cloud_raises():
    with pytest.raises(ValueError, match="Billing commands require a Cribl Cloud URL"):
        extract_org_id("https://cribl.cloud")
