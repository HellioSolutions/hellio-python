"""Tests for the Hellio client with a mocked HTTP layer (respx)."""

from __future__ import annotations

import httpx
import pytest
import respx

from hellio import (
    ConflictError,
    ExtensionRequiredError,
    Hellio,
    HellioError,
    InsufficientBalanceError,
    InvalidApiTokenError,
    RateLimitError,
    ValidationError,
)

BASE = "https://api.helliomessaging.com/v1"
APP_ID = "9b1f0e3a-4c2d-4a7b-8e1f-0a1b2c3d4e5f"


@pytest.fixture
def client() -> Hellio:
    return Hellio(token="test-token")


# ------------------------------------------------------------------ transport

def test_base_url_and_auth_header(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/balance").mock(
            return_value=httpx.Response(200, json={"data": {"balance": "195.0000"}})
        )
        result = client.balance()

    assert result == {"data": {"balance": "195.0000"}}
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer test-token"
    assert request.headers["accept"] == "application/json"
    assert str(request.url) == f"{BASE}/balance"


def test_default_base_url_has_single_slash_join() -> None:
    c = Hellio(token="t")
    assert c.base_url == BASE


# -------------------------------------------------------------------- account

def test_pricing_without_country(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/pricing").mock(return_value=httpx.Response(200, json={"data": []}))
        client.pricing()
    assert "country" not in dict(route.calls.last.request.url.params)


def test_pricing_with_country(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/pricing").mock(return_value=httpx.Response(200, json={"data": []}))
        client.pricing("GH")
    assert dict(route.calls.last.request.url.params) == {"country": "GH"}


# ------------------------------------------------------------------------ sms

def test_sms_single_recipient(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/sms/send").mock(
            return_value=httpx.Response(200, json={"data": {"id": 1}})
        )
        client.sms("233241234567", "Hello!", sender="HellioSMS")

    body = route.calls.last.request.read()
    import json as _json

    payload = _json.loads(body)
    assert payload == {
        "recipients": ["233241234567"],
        "sender": "HellioSMS",
        "message": "Hello!",
    }


def test_sms_uses_default_sender() -> None:
    c = Hellio(token="t", default_sender="DEFSEND")
    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/sms/send").mock(return_value=httpx.Response(200, json={"data": {}}))
        c.sms("233241234567", "Hi")
    import json as _json

    payload = _json.loads(route.calls.last.request.read())
    assert payload["sender"] == "DEFSEND"


def test_recipient_normalization(client: Hellio) -> None:
    assert client._to_list("233241234567") == ["233241234567"]
    assert client._to_list("233241234567, 233201234567") == [
        "233241234567",
        "233201234567",
    ]
    assert client._to_list(["233241234567", "233201234567"]) == [
        "233241234567",
        "233201234567",
    ]
    assert client._to_list(" , 233241234567 ,") == ["233241234567"]


# ------------------------------------------------------------------------ otp

def test_otp_sms_uses_mobile_number(client: Hellio) -> None:
    import json as _json

    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/otp/send").mock(return_value=httpx.Response(200, json={"data": {}}))
        client.otp("233241234567", "HellioSMS", length=6, expiry=10)

    payload = _json.loads(route.calls.last.request.read())
    assert payload == {
        "channel": "sms",
        "mobile_number": "233241234567",
        "sender": "HellioSMS",
        "length": 6,
        "expiry": 10,
    }


def test_otp_email_uses_email_field(client: Hellio) -> None:
    import json as _json

    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/otp/send").mock(return_value=httpx.Response(200, json={"data": {}}))
        client.otp("user@example.com", channel="email")

    payload = _json.loads(route.calls.last.request.read())
    assert payload == {"channel": "email", "email": "user@example.com"}


def test_verify_true(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        mock.post("/otp/verify").mock(
            return_value=httpx.Response(200, json={"data": {"verified": True}})
        )
        assert client.verify("233241234567", "123456") is True


def test_verify_false_on_validation_error(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        mock.post("/otp/verify").mock(
            return_value=httpx.Response(422, json={"message": "Invalid code"})
        )
        assert client.verify("233241234567", "000000") is False


def test_verify_otp_raises_non_validation_errors(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        mock.post("/otp/verify").mock(return_value=httpx.Response(401, json={}))
        with pytest.raises(InvalidApiTokenError):
            client.verify_otp("233241234567", "000000")


# --------------------------------------------------------------------- webhooks

def test_create_webhook_omits_empty_events(client: Hellio) -> None:
    import json as _json

    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/webhooks").mock(return_value=httpx.Response(200, json={"data": {}}))
        client.create_webhook("https://x.test/hook")

    payload = _json.loads(route.calls.last.request.read())
    assert payload == {"url": "https://x.test/hook"}


def test_delete_webhook(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        route = mock.delete("/webhooks/1").mock(return_value=httpx.Response(200, json={"data": {}}))
        client.delete_webhook(1)
    assert route.calls.last.request.method == "DELETE"


# ----------------------------------------------------------------------- ussd

def test_ussd_pricing(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/ussd/pricing").mock(
            return_value=httpx.Response(200, json={"data": {"short_code": "920"}})
        )
        result = client.ussd.pricing()
    assert result == {"data": {"short_code": "920"}}
    assert str(route.calls.last.request.url) == f"{BASE}/ussd/pricing"


def test_ussd_availability_sends_code(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/ussd/pricing/availability").mock(
            return_value=httpx.Response(200, json={"data": {"valid": True}})
        )
        client.ussd.availability(100)
    assert dict(route.calls.last.request.url.params) == {"code": "100"}


def test_ussd_apps_list_omits_cursor(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/ussd/apps").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        client.ussd.apps()
    assert "cursor" not in dict(route.calls.last.request.url.params)


def test_ussd_apps_list_passes_cursor(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/ussd/apps").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        client.ussd.apps(cursor="abc")
    assert dict(route.calls.last.request.url.params) == {"cursor": "abc"}


def test_ussd_create_app(client: Hellio) -> None:
    import json as _json

    app = {
        "id": APP_ID,
        "name": "Topup",
        "callback_url": "https://x.test/ussd",
        "mode": "test",
        "test_secret": "ussk_test_abc123",
        "live_secret": "ussk_live_def456",
        "is_live": False,
        "active": True,
    }
    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/ussd/apps").mock(
            return_value=httpx.Response(201, json={"data": app})
        )
        result = client.ussd.create_app("Topup", "https://x.test/ussd")

    assert result == {"data": app}
    assert result["data"]["mode"] == "test"
    assert result["data"]["test_secret"].startswith("ussk_test_")
    assert result["data"]["live_secret"].startswith("ussk_live_")
    payload = _json.loads(route.calls.last.request.read())
    assert payload == {"name": "Topup", "callback_url": "https://x.test/ussd"}


def test_ussd_update_app_uses_put_and_omits_none(client: Hellio) -> None:
    import json as _json

    with respx.mock(base_url=BASE) as mock:
        route = mock.put(f"/ussd/apps/{APP_ID}").mock(
            return_value=httpx.Response(200, json={"data": {"id": APP_ID}})
        )
        client.ussd.update_app(APP_ID, active=True)

    request = route.calls.last.request
    assert request.method == "PUT"
    assert _json.loads(request.read()) == {"active": True}


def test_ussd_delete_app(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        route = mock.delete(f"/ussd/apps/{APP_ID}").mock(
            return_value=httpx.Response(204)
        )
        client.ussd.delete_app(APP_ID)
    assert route.calls.last.request.method == "DELETE"


def test_ussd_set_mode_body(client: Hellio) -> None:
    import json as _json

    with respx.mock(base_url=BASE) as mock:
        route = mock.post(f"/ussd/apps/{APP_ID}/mode").mock(
            return_value=httpx.Response(
                200, json={"data": {"id": APP_ID, "mode": "live", "is_live": True}}
            )
        )
        result = client.ussd.set_mode(APP_ID, "live")

    assert result["data"]["mode"] == "live"
    assert _json.loads(route.calls.last.request.read()) == {"mode": "live"}


def test_ussd_set_mode_live_requires_extension(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        mock.post(f"/ussd/apps/{APP_ID}/mode").mock(
            return_value=httpx.Response(402, json={"error": "extension_required"})
        )
        with pytest.raises(ExtensionRequiredError) as info:
            client.ussd.set_mode(APP_ID, "live")

    assert info.value.status_code == 402
    assert info.value.message == "extension_required"


def test_ussd_rotate_secret_body(client: Hellio) -> None:
    import json as _json

    with respx.mock(base_url=BASE) as mock:
        route = mock.post(f"/ussd/apps/{APP_ID}/rotate-secret").mock(
            return_value=httpx.Response(
                200,
                json={"data": {"id": APP_ID, "test_secret": "ussk_test_new"}},
            )
        )
        result = client.ussd.rotate_secret(APP_ID, "test")

    assert result["data"]["test_secret"] == "ussk_test_new"
    assert _json.loads(route.calls.last.request.read()) == {"mode": "test"}


def test_ussd_extensions_list(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/ussd/extensions").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        client.ussd.extensions()
    assert str(route.calls.last.request.url) == f"{BASE}/ussd/extensions"


def test_ussd_rent_extension_body(client: Hellio) -> None:
    import json as _json

    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/ussd/extensions").mock(
            return_value=httpx.Response(201, json={"data": {"id": 3}})
        )
        client.ussd.rent_extension(100, app_id=APP_ID)

    assert _json.loads(route.calls.last.request.read()) == {
        "code": 100,
        "app_id": APP_ID,
    }


def test_ussd_rent_extension_conflict(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        mock.post("/ussd/extensions").mock(
            return_value=httpx.Response(409, json={"error": "extension_unavailable"})
        )
        with pytest.raises(ConflictError) as info:
            client.ussd.rent_extension(100)

    assert info.value.status_code == 409
    assert info.value.message == "extension_unavailable"


def test_ussd_rent_extension_insufficient_ussd_balance(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        mock.post("/ussd/extensions").mock(
            return_value=httpx.Response(
                402, json={"error": "insufficient_ussd_balance"}
            )
        )
        with pytest.raises(InsufficientBalanceError) as info:
            client.ussd.rent_extension(100)

    assert info.value.status_code == 402
    assert info.value.message == "insufficient_ussd_balance"


def test_ussd_release_extension(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        route = mock.delete("/ussd/extensions/ext-3").mock(
            return_value=httpx.Response(204)
        )
        client.ussd.release_extension("ext-3")
    assert route.calls.last.request.method == "DELETE"


def test_ussd_sessions_with_status(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/ussd/sessions").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        client.ussd.sessions(status="ended")
    assert dict(route.calls.last.request.url.params) == {"status": "ended"}


def test_ussd_session_get(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/ussd/sessions/sess_1").mock(
            return_value=httpx.Response(200, json={"data": {"id": "sess_1"}})
        )
        result = client.ussd.session("sess_1")
    assert result == {"data": {"id": "sess_1"}}
    assert str(route.calls.last.request.url) == f"{BASE}/ussd/sessions/sess_1"


def test_ussd_simulate_body(client: Hellio) -> None:
    import json as _json

    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/ussd/simulate").mock(
            return_value=httpx.Response(
                200,
                json={"data": {"message": "Hi", "action": "continue", "continue": True}},
            )
        )
        client.ussd.simulate(
            app_id=APP_ID,
            session_id="sess_1",
            msisdn="233241234567",
            input="1",
            new_session=True,
            service_code="*920*100#",
        )

    payload = _json.loads(route.calls.last.request.read())
    assert payload == {
        "app_id": APP_ID,
        "session_id": "sess_1",
        "msisdn": "233241234567",
        "input": "1",
        "new_session": True,
        "service_code": "*920*100#",
    }


def test_ussd_simulate_omits_service_code_when_none(client: Hellio) -> None:
    import json as _json

    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/ussd/simulate").mock(
            return_value=httpx.Response(200, json={"data": {"message": "Hi"}})
        )
        client.ussd.simulate(
            app_id=APP_ID,
            session_id="sess_1",
            msisdn="233241234567",
            new_session=True,
        )

    payload = _json.loads(route.calls.last.request.read())
    assert "service_code" not in payload
    assert payload == {
        "app_id": APP_ID,
        "session_id": "sess_1",
        "msisdn": "233241234567",
        "input": "",
        "new_session": True,
    }


def test_ussd_simulate_unknown_app(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        mock.post("/ussd/simulate").mock(
            return_value=httpx.Response(422, json={"error": "unknown_app"})
        )
        with pytest.raises(ValidationError) as info:
            client.ussd.simulate(
                app_id=APP_ID, session_id="sess_1", msisdn="233241234567"
            )

    assert info.value.status_code == 422
    assert info.value.message == "unknown_app"


# -------------------------------------------------------------- error mapping

@pytest.mark.parametrize(
    "status,exc",
    [
        (401, InvalidApiTokenError),
        (402, InsufficientBalanceError),
        (409, ConflictError),
        (422, ValidationError),
        (429, RateLimitError),
        (500, HellioError),
    ],
)
def test_error_mapping(client: Hellio, status: int, exc: type) -> None:
    with respx.mock(base_url=BASE) as mock:
        mock.get("/balance").mock(
            return_value=httpx.Response(status, json={"message": "boom"})
        )
        with pytest.raises(exc) as info:
            client.balance()

    err = info.value
    assert err.status_code == status
    assert err.message == "boom"


def test_validation_error_exposes_errors(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        mock.post("/sms/send").mock(
            return_value=httpx.Response(
                422,
                json={"message": "Invalid", "errors": {"recipients": ["required"]}},
            )
        )
        with pytest.raises(ValidationError) as info:
            client.sms("", "hi", sender="X")

    assert info.value.errors == {"recipients": ["required"]}


def test_default_error_message_when_body_empty(client: Hellio) -> None:
    with respx.mock(base_url=BASE) as mock:
        mock.get("/balance").mock(return_value=httpx.Response(500, json={}))
        with pytest.raises(HellioError) as info:
            client.balance()
    assert info.value.message == "Hellio API request failed."


# --------------------------------------------------------- injected http client

def test_injected_client_is_used() -> None:
    injected = httpx.Client(base_url=BASE + "/")
    c = Hellio(token="t", http_client=injected)
    with respx.mock(base_url=BASE) as mock:
        mock.get("/lookups").mock(return_value=httpx.Response(200, json={"data": []}))
        assert c.lookups() == {"data": []}
