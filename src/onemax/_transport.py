from __future__ import annotations

import json
from typing import Any

from ._version import __version__
from .errors import TransportError, error_class

API_URL = "https://api.onemax.az/v1"
SITE_URL = "https://onemax.az"
DEFAULT_TIMEOUT = 10.0
RAW_MESSAGE_LIMIT = 200


def checked_key(api_key: str) -> str:
    key = api_key.strip()
    if not key:
        raise ValueError("api_key is required")
    return key


def headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": f"onemax-python/{__version__}",
    }


def _decoded(text: str) -> Any:
    try:
        return json.loads(text)
    except ValueError:
        return None


def _failure(status: int, text: str) -> Exception:
    body = _decoded(text)
    envelope = body.get("error") if isinstance(body, dict) else None
    if not isinstance(envelope, dict):
        message = text.strip()[:RAW_MESSAGE_LIMIT] or f"HTTP {status}"
        return error_class(status)(message, status=status, code="unknown_error")
    details = envelope.get("details")
    request_id = envelope.get("request_id")
    return error_class(status)(
        str(envelope.get("message") or f"HTTP {status}"),
        status=status,
        code=str(envelope.get("code") or "unknown_error"),
        details=details if isinstance(details, dict) else None,
        request_id=str(request_id) if request_id is not None else None,
    )


def read(status: int, text: str) -> dict[str, Any]:
    if not 200 <= status < 300:
        raise _failure(status, text)
    body = _decoded(text)
    if not isinstance(body, dict):
        raise TransportError(f"unexpected response body: {text.strip()[:RAW_MESSAGE_LIMIT]!r}")
    return body
