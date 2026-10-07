from __future__ import annotations

from typing import Any


class OneMaxError(Exception):
    pass


class TransportError(OneMaxError):
    pass


class ApiError(OneMaxError):
    def __init__(
        self,
        message: str,
        *,
        status: int,
        code: str,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.details = details or {}
        self.request_id = request_id

    def __str__(self) -> str:
        return f"{self.status} {self.code}: {self.message}"


class AuthenticationError(ApiError):
    pass


class AccessDisabledError(ApiError):
    pass


class NotFoundError(ApiError):
    pass


class ConflictError(ApiError):
    pass


class InvalidRequestError(ApiError):
    pass


class RateLimitError(ApiError):
    @property
    def retry_after(self) -> int | None:
        seconds = self.details.get("retry_after")
        return seconds if isinstance(seconds, int) and not isinstance(seconds, bool) else None


class ServerError(ApiError):
    pass


BY_STATUS: dict[int, type[ApiError]] = {
    400: InvalidRequestError,
    401: AuthenticationError,
    403: AccessDisabledError,
    404: NotFoundError,
    409: ConflictError,
    422: InvalidRequestError,
    429: RateLimitError,
}


def error_class(status: int) -> type[ApiError]:
    if status >= 500:
        return ServerError
    return BY_STATUS.get(status, ApiError)
