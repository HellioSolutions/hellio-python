"""USSD resource for the Hellio Messaging API.

Groups every ``/v1/ussd/*`` endpoint under a single namespace, exposed on the
client as :attr:`Hellio.ussd`. Covers pricing and availability, USSD apps
(callbacks), extension (short-code suffix) rentals, live/ended sessions, and a
simulator for testing a callback without dialling the real code.

Apps have a **test** and a **live** mode. A new app starts in ``test`` and
carries two secrets (``test_secret`` prefixed ``ussk_test_`` and ``live_secret``
prefixed ``ussk_live_``); the active secret is the one for the current ``mode``.
Simulation always runs in the sandbox (test mode): no charge and no extension
needed. Going live requires a purchased extension and draws USSD sessions from a
dedicated USSD balance, separate from your SMS credit and main wallet.

Requires an API token with the ``ussd`` ability. Like the rest of the SDK,
every method returns the decoded JSON response as a dict (payloads are under the
``data`` key) and raises a typed :class:`~hellio.errors.HellioError` on non-2xx
responses. Renting an unavailable extension raises
:class:`~hellio.errors.ConflictError` (409); too low a USSD balance raises
:class:`~hellio.errors.InsufficientBalanceError` (402, ``insufficient_ussd_balance``);
switching to live mode before an extension is purchased raises
:class:`~hellio.errors.ExtensionRequiredError` (402, ``extension_required``).
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
        """Create a USSD app. New apps start in ``test`` mode.

        Args:
            name: Display name for the app.
            callback_url: HTTPS endpoint Hellio POSTs session steps to.

        The returned ``data`` describes the app: ``id`` (UUID string), ``name``,
        ``callback_url``, ``mode`` (``"test"`` or ``"live"``), ``test_secret``
        (prefix ``ussk_test_``), ``live_secret`` (prefix ``ussk_live_``),
        ``is_live`` (bool), and ``active`` (bool).
        """
        return self._client._post(
            "ussd/apps", {"name": name, "callback_url": callback_url}
        )

    def update_app(
        self,
        id: str,
        name: Optional[str] = None,
        callback_url: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update a USSD app's name, callback URL, or active flag.

        Args:
            id: The app's UUID.
        """
        return self._client._put(
            f"ussd/apps/{id}",
            self._client._compact(
                {"name": name, "callback_url": callback_url, "active": active}
            ),
        )

    def delete_app(self, id: str) -> Dict[str, Any]:
        """Delete a USSD app by UUID."""
        return self._client._delete(f"ussd/apps/{id}")

    def set_mode(self, app_id: str, mode: str) -> Dict[str, Any]:
        """Switch a USSD app between ``test`` and ``live`` mode.

        Args:
            app_id: The app's UUID.
            mode: ``"test"`` or ``"live"``.

        Returns the updated app.

        Raises:
            ExtensionRequiredError: Switching to ``live`` before an extension
                has been purchased for the app (402, ``extension_required``).
        """
        return self._client._post(
            f"ussd/apps/{app_id}/mode", {"mode": mode}
        )

    def rotate_secret(self, app_id: str, mode: str) -> Dict[str, Any]:
        """Rotate a USSD app's signing secret for the given mode.

        Args:
            app_id: The app's UUID.
            mode: Which secret to rotate, ``"test"`` or ``"live"``.

        Returns the app with the freshly rotated ``test_secret`` or
        ``live_secret``. The previous secret for that mode stops working.
        """
        return self._client._post(
            f"ussd/apps/{app_id}/rotate-secret", {"mode": mode}
        )

    # ---------------------------------------------------------- extensions

    def extensions(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        """List rented extensions (cursor-paginated)."""
        return self._client._get(
            "ussd/extensions", self._client._compact({"cursor": cursor})
        )

    def rent_extension(
        self, code: Union[int, str], app_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Rent an extension (short-code suffix), optionally bound to an app.

        The rent is charged to the dedicated USSD balance, which is separate
        from your SMS credit and main wallet.

        Args:
            code: The extension code to rent.
            app_id: Optional UUID of the app to bind the extension to.

        Raises:
            ConflictError: The extension is no longer available (409).
            InsufficientBalanceError: The USSD balance is too low to cover the
                rent (402, ``insufficient_ussd_balance``).
        """
        return self._client._post(
            "ussd/extensions",
            self._client._compact({"code": code, "app_id": app_id}),
        )

    def release_extension(self, id: str) -> Dict[str, Any]:
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

    def session(self, id: str) -> Dict[str, Any]:
        """Return a single USSD session by id."""
        return self._client._get(f"ussd/sessions/{id}")

    # ------------------------------------------------------------ simulate

    def simulate(
        self,
        app_id: str,
        session_id: str,
        msisdn: str,
        input: str = "",
        new_session: bool = False,
        service_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Simulate a subscriber USSD step against an app's callback.

        Always runs in the sandbox (the app's test mode): no charge and no
        extension required. Simulating an app you do not own raises a
        :class:`~hellio.errors.ValidationError` (422, ``unknown_app``).

        Args:
            app_id: The UUID of the app to simulate against.
            session_id: Session reference; reuse it across steps of one session.
            msisdn: The subscriber's number.
            input: What the subscriber typed for this step.
            new_session: ``True`` for the first step of a fresh session.
            service_code: Optional dialled service code. Defaults to the shared
                short code server-side when omitted.

        Returns the app's reply: ``message``, ``action`` (``"continue"`` or
        ``"end"``), and a ``continue`` boolean.
        """
        return self._client._post(
            "ussd/simulate",
            self._client._compact(
                {
                    "app_id": app_id,
                    "session_id": session_id,
                    "msisdn": msisdn,
                    "input": input,
                    "new_session": new_session,
                    "service_code": service_code,
                }
            ),
        )


__all__ = ["Ussd"]
