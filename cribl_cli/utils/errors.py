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


def _extract_http_error_detail(err: Exception) -> dict | None:
    """Extract the response body from an httpx.HTTPStatusError."""
    try:
        import httpx
        if isinstance(err, httpx.HTTPStatusError) and err.response is not None:
            try:
                body = err.response.json()
                if not isinstance(body, dict):
                    return {"status": err.response.status_code, "detail": body}
                # Cribl API often nests a JSON string inside "message"
                msg = body.get("message", "")
                if isinstance(msg, str):
                    try:
                        body["message"] = json.loads(msg)
                    except (json.JSONDecodeError, TypeError):
                        pass
                return {"status": err.response.status_code, **body}
            except (json.JSONDecodeError, ValueError):
                text = err.response.text
                if text:
                    return {"status": err.response.status_code, "detail": text}
    except ImportError:
        pass
    return None


def _is_timeout(err: Exception) -> bool:
    try:
        import httpx
        return isinstance(err, httpx.TimeoutException)
    except ImportError:
        return False


def handle_error(err: Exception) -> None:
    if isinstance(err, DryRunAbort):
        sys.exit(0)

    if isinstance(err, CriblApiError):
        payload = {"error": err.message, "status": err.status}
        if err.detail:
            payload["detail"] = err.detail
    elif isinstance(err, AuthenticationError):
        payload = {"error": str(err), "type": "AuthenticationError"}
    elif _is_timeout(err):
        payload = {
            "error": str(err) or "Request timed out",
            "hint": "The API did not answer in time. Raise the limit with the global "
                    "--timeout option (cribl --timeout 120 ...) or CRIBL_TIMEOUT.",
        }
    else:
        detail = _extract_http_error_detail(err)
        if detail:
            payload = {"error": str(err), **detail}
        else:
            payload = {"error": str(err)}

    sys.stderr.write(json.dumps(payload, indent=2) + "\n")
    sys.exit(1)
