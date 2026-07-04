"""Typed exceptions for the Hellio Messaging SDK.

Every non-2xx API response raises a subclass of :class:`HellioError`, mapped by
HTTP status code. Each error carries the message (from the response body's
``message`` field or a default), the ``status_code``, and the parsed response
body so you can inspect validation ``errors`` and other details.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class HellioError(Exception):
    """Base error for all Hellio Messaging API failures.

    Attributes:
        message: Human-readable error message.
        status_code: HTTP status code returned by the API (if any).
        response: The parsed JSON response body (a dict).
    """

    def __init__(
        self,
        message: str = "Hellio API request failed.",
        status_code: Optional[int] = None,
        response: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response: Dict[str, Any] = response or {}

    @property
    def errors(self) -> Any:
        """Field-level validation details, when the API supplies them (422)."""
        return self.response.get("errors")


class InvalidApiTokenError(HellioError):
    """Raised on HTTP 401. The API token is missing, invalid, or revoked."""


class InsufficientBalanceError(HellioError):
    """Raised on HTTP 402. The account balance is too low for the request."""


class ValidationError(HellioError):
    """Raised on HTTP 422. One or more request fields failed validation."""


class RateLimitError(HellioError):
    """Raised on HTTP 429. The 120 requests/minute limit was exceeded."""


class ServiceUnavailableError(HellioError):
    """Raised on HTTP 503. The service was switched off by an admin (SMS, OTP,
    voice, WhatsApp, lookup, email) or the API is paused. Transient: retry later."""


__all__ = [
    "HellioError",
    "InvalidApiTokenError",
    "InsufficientBalanceError",
    "ValidationError",
    "RateLimitError",
    "ServiceUnavailableError",
]
