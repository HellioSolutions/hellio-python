"""Hellio Messaging API v1 client.

Authenticates with a Bearer token and exposes one method per endpoint. Every
call returns the decoded JSON response as a dict (payloads are under ``data``);
non-2xx responses raise a typed :class:`~hellio.errors.HellioError`.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Union

import httpx

from .errors import (
    HellioError,
    InsufficientBalanceError,
    InvalidApiTokenError,
    RateLimitError,
    ValidationError,
)

Recipients = Union[str, Sequence[str]]

DEFAULT_BASE_URL = "https://api.helliomessaging.com/v1"
DEFAULT_TIMEOUT = 30.0


class Hellio:
    """Synchronous client for the Hellio Messaging API.

    Args:
        token: API token. Falls back to the ``HELLIO_API_TOKEN`` env var.
        base_url: API base URL. Falls back to ``HELLIO_BASE_URL`` env var, then
            to ``https://api.helliomessaging.com/v1``.
        timeout: Request timeout in seconds (default 30).
        default_sender: Default Sender ID for SMS. Falls back to the
            ``HELLIO_DEFAULT_SENDER`` env var.
        http_client: Optional pre-built ``httpx.Client`` to inject (useful for
            tests). When supplied, the client is used as-is and the caller owns
            its lifecycle.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        default_sender: Optional[str] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.token = token or os.environ.get("HELLIO_API_TOKEN", "")
        self.base_url = (
            base_url or os.environ.get("HELLIO_BASE_URL") or DEFAULT_BASE_URL
        ).rstrip("/")
        self.timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
        self.default_sender = default_sender or os.environ.get("HELLIO_DEFAULT_SENDER")

        self._owns_client = http_client is None
        self._http = http_client or httpx.Client(
            base_url=self.base_url + "/",
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    # ---------------------------------------------------------------- lifecycle

    def close(self) -> None:
        """Close the underlying HTTP client (only if this client created it)."""
        if self._owns_client:
            self._http.close()

    def __enter__(self) -> "Hellio":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()

    # ------------------------------------------------------------------ Account

    def balance(self) -> Dict[str, Any]:
        """Return the account balance."""
        return self._get("balance")

    def pricing(self, country: Optional[str] = None) -> Dict[str, Any]:
        """Return per-network SMS pricing.

        Pass an ISO-2 country code to narrow the results by country.
        """
        return self._get("pricing", {"country": country} if country else None)

    # ---------------------------------------------------------------------- SMS

    def sms(
        self,
        recipients: Recipients,
        message: str,
        sender: Optional[str] = None,
        gateway: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an SMS.

        Args:
            recipients: A single number, a comma-separated string, or a list.
            message: The message body.
            sender: Sender ID. Defaults to the client's ``default_sender``.
            gateway: Optional gateway override.
        """
        return self._post(
            "sms/send",
            self._compact(
                {
                    "recipients": self._to_list(recipients),
                    "sender": sender or self.default_sender,
                    "message": message,
                    "gateway": gateway,
                }
            ),
        )

    def message(self, id: Union[int, str]) -> Dict[str, Any]:
        """Return delivery status for a single message."""
        return self._get(f"messages/{id}")

    def campaign(self, id: Union[int, str]) -> Dict[str, Any]:
        """Return a campaign summary."""
        return self._get(f"campaigns/{id}")

    # ---------------------------------------------------------------------- OTP

    def otp(
        self,
        to: str,
        sender: Optional[str] = None,
        channel: str = "sms",
        purpose: Optional[str] = None,
        length: Optional[int] = None,
        expiry: Optional[int] = None,
        gateway: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a one-time passcode.

        Args:
            to: Phone number (sms/voice) or email address (email channel).
            sender: Sender ID. Required for sms/voice, ignored for email.
            channel: ``sms`` (default), ``voice``, or ``email``.
            purpose: Optional purpose label.
            length: Optional code length (4-10 digits).
            expiry: Optional validity window in minutes.
            gateway: Optional gateway override.
        """
        to_field = "email" if channel == "email" else "mobile_number"
        return self._post(
            "otp/send",
            self._compact(
                {
                    "channel": channel,
                    to_field: to,
                    "sender": sender,
                    "purpose": purpose,
                    "length": length,
                    "expiry": expiry,
                    "gateway": gateway,
                }
            ),
        )

    def verify_otp(
        self, to: str, code: str, channel: str = "sms"
    ) -> Dict[str, Any]:
        """Verify a one-time passcode and return the full API response."""
        to_field = "email" if channel == "email" else "mobile_number"
        return self._post(
            "otp/verify",
            self._compact({"channel": channel, to_field: to, "code": code}),
        )

    def verify(self, to: str, code: str, channel: str = "sms") -> bool:
        """Convenience: return ``True`` when the code is valid.

        A 422 validation error is treated as an invalid code and returns
        ``False`` rather than raising.
        """
        try:
            result = self.verify_otp(to, code, channel)
        except ValidationError:
            return False
        return bool(result.get("data", {}).get("verified", False))

    # -------------------------------------------------------------------- Voice

    def voice(
        self,
        recipients: Recipients,
        caller_id: str,
        text: Optional[str] = None,
        audio_url: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a voice broadcast.

        Provide ``text`` (read out with TTS) or ``audio_url`` (a hosted file).
        """
        return self._post(
            "voice/send",
            self._compact(
                {
                    "recipients": self._to_list(recipients),
                    "caller_id": caller_id,
                    "text": text,
                    "audio_url": audio_url,
                    "name": name,
                }
            ),
        )

    def voice_status(self, id: Union[int, str]) -> Dict[str, Any]:
        """Return the status of a voice broadcast."""
        return self._get(f"voice/{id}")

    # ------------------------------------------------------------- Number lookup

    def lookup(self, numbers: Recipients) -> Dict[str, Any]:
        """Submit numbers for HLR lookup (async; poll for results)."""
        return self._post("lookup", {"numbers": self._to_list(numbers)})

    def lookups(self) -> Dict[str, Any]:
        """List past lookup requests."""
        return self._get("lookups")

    def lookup_result(self, id: Union[int, str]) -> Dict[str, Any]:
        """Return the result of a single lookup request."""
        return self._get(f"lookup/{id}")

    # --------------------------------------------------------- Email verification

    def verify_email(self, emails: Recipients) -> Dict[str, Any]:
        """Verify one or more email addresses."""
        return self._post("email/verify", {"emails": self._to_list(emails)})

    # ----------------------------------------------------------------- Webhooks

    def webhooks(self) -> Dict[str, Any]:
        """List configured webhooks."""
        return self._get("webhooks")

    def create_webhook(
        self, url: str, events: Optional[Sequence[str]] = None
    ) -> Dict[str, Any]:
        """Create a webhook.

        Args:
            url: The endpoint that receives delivery reports.
            events: Optional list of event names to subscribe to.
        """
        events_list = list(events) if events else None
        return self._post(
            "webhooks", self._compact({"url": url, "events": events_list})
        )

    def delete_webhook(self, id: Union[int, str]) -> Dict[str, Any]:
        """Delete a webhook by id."""
        return self._delete(f"webhooks/{id}")

    # --------------------------------------------------------------- internals

    def _get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return self._request("GET", path, params=params)

    def _post(
        self, path: str, body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return self._request("POST", path, json=body)

    def _delete(self, path: str) -> Dict[str, Any]:
        return self._request("DELETE", path)

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        response = self._http.request(
            method, path.lstrip("/"), params=params, json=json
        )
        try:
            data = response.json()
        except ValueError:
            data = {}
        if not isinstance(data, dict):
            data = {"data": data}

        if 200 <= response.status_code < 300:
            return data

        message = data.get("message")
        if not isinstance(message, str) or not message:
            message = "Hellio API request failed."

        error_class = {
            401: InvalidApiTokenError,
            402: InsufficientBalanceError,
            422: ValidationError,
            429: RateLimitError,
        }.get(response.status_code, HellioError)

        raise error_class(message, response.status_code, data)

    @staticmethod
    def _to_list(value: Recipients) -> List[str]:
        """Normalize a string, comma-separated string, or list into a list."""
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return [str(item) for item in value]

    @staticmethod
    def _compact(data: Dict[str, Any]) -> Dict[str, Any]:
        """Drop keys whose value is ``None``."""
        return {key: val for key, val in data.items() if val is not None}


__all__ = ["Hellio"]
