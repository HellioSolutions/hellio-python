"""USSD resource for the Hellio Messaging API.

Groups every ``/v1/ussd/*`` endpoint under a single namespace, exposed on the
client as :attr:`Hellio.ussd`. Covers pricing and availability, USSD apps
(callbacks), extension (short-code suffix) rentals, live/ended sessions, and a
simulator for testing a callback without dialling the real code.

Requires an API token with the ``ussd`` ability. Like the rest of the SDK,
every method returns the decoded JSON response as a dict (payloads are under the
``data`` key) and raises a typed :class:`~hellio.errors.HellioError` on non-2xx
responses. Renting an unavailable extension raises
:class:`~hellio.errors.ConflictError` (409); an insufficient balance raises
:class:`~hellio.errors.InsufficientBalanceError` (402).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Union

if TYPE_CHECKING:
    from .client import Hellio


class Ussd:
    """USSD endpoints, reached through :attr:`Hellio.ussd`.

    Not instantiated directly; the client builds it and shares its HTTP layer.
    """

    def __init__(self, client: "Hellio") -> None:
        self._client = client

    # ------------------------------------------------------------- pricing

    def pricing(self) -> Dict[str, Any]:
        """Return USSD pricing: per-network session prices and extension rents."""
        return self._client._get("ussd/pricing")

    def availability(self, code: Union[int, str]) -> Dict[str, Any]:
        """Check whether an extension ``code`` is valid and available to rent.

        Returns ``valid``, ``available``, and the ``monthly_price`` (or ``None``).
        """
        return self._client._get("ussd/pricing/availability", {"code": code})

    # ---------------------------------------------------------------- apps

    def apps(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        """List USSD apps (cursor-paginated; pass ``cursor`` for the next page)."""
        return self._client._get(
            "ussd/apps", self._client._compact({"cursor": cursor})
        )

    def create_app(self, name: str, callback_url: str) -> Dict[str, Any]:
        """Create a USSD app.

        Args:
            name: Display name for the app.
            callback_url: HTTPS endpoint Hellio POSTs session steps to.
        """
        return self._client._post(
            "ussd/apps", {"name": name, "callback_url": callback_url}
        )

    def update_app(
        self,
        id: Union[int, str],
        name: Optional[str] = None,
        callback_url: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update a USSD app's name, callback URL, or active flag."""
        return self._client._put(
            f"ussd/apps/{id}",
            self._client._compact(
                {"name": name, "callback_url": callback_url, "active": active}
            ),
        )

    def delete_app(self, id: Union[int, str]) -> Dict[str, Any]:
        """Delete a USSD app by id."""
        return self._client._delete(f"ussd/apps/{id}")

    # ---------------------------------------------------------- extensions

    def extensions(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        """List rented extensions (cursor-paginated)."""
        return self._client._get(
            "ussd/extensions", self._client._compact({"cursor": cursor})
        )

    def rent_extension(
        self, code: Union[int, str], app_id: Optional[Union[int, str]] = None
    ) -> Dict[str, Any]:
        """Rent an extension (short-code suffix), optionally bound to an app.

        Raises:
            ConflictError: The extension is no longer available (409).
            InsufficientBalanceError: The balance is too low to cover the rent (402).
        """
        return self._client._post(
            "ussd/extensions",
            self._client._compact({"code": code, "app_id": app_id}),
        )

    def release_extension(self, id: Union[int, str]) -> Dict[str, Any]:
        """Release (stop renting) an extension by id."""
        return self._client._delete(f"ussd/extensions/{id}")

    # ------------------------------------------------------------ sessions

    def sessions(
        self, status: Optional[str] = None, cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """List USSD sessions (cursor-paginated).

        Args:
            status: Optional filter, e.g. ``"active"`` or ``"ended"``.
            cursor: Opaque cursor for the next page.
        """
        return self._client._get(
            "ussd/sessions",
            self._client._compact({"status": status, "cursor": cursor}),
        )

    def session(self, id: Union[int, str]) -> Dict[str, Any]:
        """Return a single USSD session by id."""
        return self._client._get(f"ussd/sessions/{id}")

    # ------------------------------------------------------------ simulate

    def simulate(
        self,
        msisdn: str,
        service_code: str,
        user_input: str = "",
        session_id: Optional[str] = None,
        new_session: bool = False,
    ) -> Dict[str, Any]:
        """Simulate a subscriber USSD step against an app callback.

        Args:
            msisdn: The subscriber's number.
            service_code: The dialled service code (extension dial string).
            user_input: What the subscriber typed for this step.
            session_id: Existing session reference; omit to start a new one.
            new_session: ``True`` for the first step of a fresh session.

        Returns the app's reply: ``message``, ``action`` (``"continue"`` or
        ``"end"``), and a ``continue`` boolean.
        """
        return self._client._post(
            "ussd/simulate",
            self._client._compact(
                {
                    "session_id": session_id,
                    "msisdn": msisdn,
                    "service_code": service_code,
                    "input": user_input,
                    "new_session": new_session,
                }
            ),
        )


__all__ = ["Ussd"]
