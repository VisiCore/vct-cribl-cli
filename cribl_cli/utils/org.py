"""Utility to extract organization ID from Cribl Cloud base URL."""
from __future__ import annotations

from urllib.parse import urlparse


def extract_org_id(base_url: str) -> str:
    """Extract organization ID from a Cribl Cloud base URL.

    'https://myorg.cribl.cloud' -> 'myorg'

    Raises ValueError for non-cloud URLs.
    """
    parsed = urlparse(base_url)
    hostname = parsed.hostname or ""
    if not hostname.endswith(".cribl.cloud"):
        raise ValueError(
            f"Cannot extract organization ID from '{base_url}'. "
            "Billing commands require a Cribl Cloud URL (e.g., https://myorg.cribl.cloud)."
        )
    parts = hostname.split(".")
    if len(parts) < 3 or not parts[0]:
        raise ValueError(
            f"Cannot extract organization ID from '{base_url}'. "
            "Expected format: https://<orgId>.cribl.cloud"
        )
    return parts[0]
