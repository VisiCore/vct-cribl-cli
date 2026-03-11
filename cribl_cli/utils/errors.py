"""Error handling for Cribl CLI."""

from __future__ import annotations

import json
import sys


class CriblApiError(Exception):
    def __init__(self, status: int, message: str, detail: str | None = None) -> None:
        self.status = status
        self.message = message
        self.detail = detail
        super().__init__(message)


class AuthenticationError(Exception):
    pass


class DryRunAbort(Exception):
    pass


def handle_error(err: Exception) -> None:
    if isinstance(err, DryRunAbort):
        sys.exit(0)

    if isinstance(err, CriblApiError):
        payload = {"error": err.message, "status": err.status}
        if err.detail:
            payload["detail"] = err.detail
    elif isinstance(err, AuthenticationError):
        payload = {"error": str(err), "type": "AuthenticationError"}
    else:
        payload = {"error": str(err)}

    sys.stderr.write(json.dumps(payload, indent=2) + "\n")
    sys.exit(1)
