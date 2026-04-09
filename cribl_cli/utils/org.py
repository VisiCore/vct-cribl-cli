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
    # Strip workspace prefix (e.g. 'main-eager-reed-t8h0f4x' -> 'eager-reed-t8h0f4x')
    # Workspace prefixes are word chars followed by a dash before the org slug.
    # Org slugs follow the pattern: <word>-<word>-<alphanum>
    if "-" in subdomain:
        # Check if this looks like a workspace-prefixed URL (e.g. main-org-slug-abc123)
        # by trying to find the org slug portion (adjective-noun-id pattern)
        import re
        match = re.match(r'^[a-zA-Z0-9]+?-(.+-[a-zA-Z0-9]{6,})$', subdomain)
        if match:
            return match.group(1)
    return subdomain
