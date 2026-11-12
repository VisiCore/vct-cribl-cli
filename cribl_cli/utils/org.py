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
    subdomain = parts[0]
    # Workspace URLs are '<workspace>-<org slug>', and an org slug is three
    # dash-separated segments ending in a random id ('acme-prod-x1y2z3a').
    # So when there are more than three segments the org id is the last three
    # ('main-acme-prod-x1y2z3a' and 'my-ws-acme-prod-x1y2z3a' both give
    # 'acme-prod-x1y2z3a'); with three or fewer the subdomain is the org id.
    segments = subdomain.split("-")
    if len(segments) > 3 and len(segments[-1]) >= 6:
        return "-".join(segments[-3:])
    return subdomain
