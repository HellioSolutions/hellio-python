# Hellio Messaging - Official Python SDK

[![tests](https://github.com/HellioSolutions/hellio-python/actions/workflows/tests.yml/badge.svg)](https://github.com/HellioSolutions/hellio-python/actions/workflows/tests.yml)
[![PyPI version](https://img.shields.io/pypi/v/helliomessaging.svg)](https://pypi.org/project/helliomessaging/)
[![Python versions](https://img.shields.io/pypi/pyversions/helliomessaging.svg)](https://pypi.org/project/helliomessaging/)
[![License](https://img.shields.io/pypi/l/helliomessaging.svg)](LICENSE)

Python client for the [Hellio Messaging](https://helliomessaging.com) API v1:
**SMS**, **OTP** (SMS / email / voice), **Voice broadcasts**, **USSD**,
**Number Lookup (HLR)**, **Email Verification**, and **Webhooks**. Fully
type-hinted and synchronous.

## Install
```bash
pip install helliomessaging
```
The import package is `hellio` (the main class is `Hellio`).

## Configure
Generate a token in your dashboard -> **Settings -> API -> Generate API token**,
then construct the client directly:
```python
from hellio import Hellio

client = Hellio(
    token="your-token-here",
    default_sender="HellioSMS",   # optional default Sender ID for SMS
)
```
Or rely on environment variables:
```dotenv
HELLIO_API_TOKEN=your-token-here
HELLIO_BASE_URL=https://api.helliomessaging.com/v1
HELLIO_DEFAULT_SENDER=HellioSMS
```
```python
client = Hellio()   # reads HELLIO_API_TOKEN, HELLIO_BASE_URL, HELLIO_DEFAULT_SENDER
```

Every call returns the decoded JSON response as a dict (payloads are under the
`data` key). You can also use the client as a context manager so the underlying
HTTP connection is closed for you:
```python
with Hellio(token="your-token-here") as client:
    client.balance()
```

## Usage

```python
from hellio import Hellio

client = Hellio(token="your-token-here", default_sender="HellioSMS")

# Account
client.balance()            # {'data': {'balance': '195.0000', 'available': '194.65', ...}}
client.pricing("GH")        # optional ISO-2 country filter
client.pricing()            # all networks

# SMS (recipients: string, comma list, or list)
client.sms("233241234567", "Hello!")
client.sms(["233241234567", "233201234567"], "Hi all", sender="HellioSMS")
client.message(1024)        # delivery status
client.campaign(1024)       # campaign summary

# OTP - sender (Sender ID) is REQUIRED for sms/voice and must be approved on your account.
# Optional length (4-10 digits) and expiry (minutes). Returns status "queued".
client.otp("233241234567", "HellioSMS")                          # SMS
client.otp("233241234567", "HellioSMS", channel="voice")         # Voice (TTS reads the code)
client.otp("233241234567", "HellioSMS", length=6, expiry=10)     # custom length / expiry
client.otp("user@example.com", channel="email")                  # Email (no sender)
client.verify("233241234567", "123456")                          # bool
client.verify_otp("user@example.com", "123456", channel="email") # full response

# Voice broadcast - text (we TTS it) or a hosted audio_url
client.voice("233241234567", "HELLIO", text="Your code is 1 2 3 4")
client.voice(["233241234567"], "HELLIO", audio_url="https://cdn.example.com/promo.mp3")
client.voice_status(42)

# Number lookup (HLR) - async; poll results
client.lookup(["233241234567"])
client.lookups()
client.lookup_result(5)

# Email verification
client.verify_email(["user@gmail.com", "bad@nodomain.invalid"])

# Webhooks (receive delivery reports)
client.create_webhook("https://your-app.com/hooks/hellio", ["message.delivered", "message.failed"])
client.webhooks()
client.delete_webhook(1)
```

## USSD
USSD lives under the `client.ussd` namespace. Needs a token with the `ussd`
ability. You rent an **extension** (a short-code suffix, e.g. `*920*100#`), point
it at a USSD **app** whose `callback_url` Hellio calls on every step, and can
inspect **sessions** or `simulate` a step without dialling the real code. List
endpoints are cursor-paginated (`data` array + `meta.next_cursor`).

```python
from hellio import Hellio

client = Hellio(token="your-token-here")

# Pricing and availability
client.ussd.pricing()                      # session prices per network + extension rents
client.ussd.availability(100)              # {'data': {'valid': True, 'available': True, 'monthly_price': '50.00'}}

# Apps (the callback endpoints Hellio POSTs session steps to)
client.ussd.apps()                         # list (pass cursor="..." for the next page)
app = client.ussd.create_app("Airtime Top-up", "https://your-app.com/ussd")
app_id = app["data"]["id"]
client.ussd.update_app(app_id, name="Airtime", active=True)
client.ussd.delete_app(app_id)

# Extensions (short-code suffixes you rent and bind to an app)
client.ussd.extensions()
ext = client.ussd.rent_extension(100, app_id=app_id)
client.ussd.release_extension(ext["data"]["id"])

# Sessions
client.ussd.sessions(status="ended")       # optional status filter
client.ussd.session("sess_ref_123")

# Simulate a subscriber step against your callback (no real dialling)
client.ussd.simulate(
    msisdn="233241234567",
    service_code="*920*100#",
    user_input="1",
    new_session=True,
)
# -> {'data': {'message': 'Welcome...', 'action': 'continue', 'continue': True}}
```

Renting an extension that has just been taken raises `ConflictError` (409); an
empty balance raises `InsufficientBalanceError` (402):

```python
from hellio import ConflictError, InsufficientBalanceError

try:
    client.ussd.rent_extension(100)
except ConflictError:
    ...  # someone else rented it first; try another code
except InsufficientBalanceError:
    ...  # top up
```

### Inbound callback
When a subscriber uses your extension, Hellio POSTs
`{ sessionId, msisdn, serviceCode, input, sequence, mode }` to the app's
`callback_url`, signed with an `X-Hellio-Signature` header
(`HMAC-SHA256(rawBody, app.secret)`). Verify the signature, then return
`{ message, action }` where `action` is `"continue"` or `"end"`:

```python
import hashlib
import hmac

def handle_ussd(raw_body: bytes, signature: str, secret: str) -> dict:
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("bad signature")
    # ... branch on the parsed payload ...
    return {"message": "Welcome to Airtime Top-up", "action": "continue"}
```

## Error handling
Non-2xx responses raise typed exceptions (all extend `HellioError`). Each error
carries `message`, `status_code`, and `response` (the parsed body); validation
errors also expose `errors`.

| Exception | Status |
|---|---|
| `InvalidApiTokenError` | 401 |
| `InsufficientBalanceError` | 402 |
| `ConflictError` | 409 |
| `ValidationError` (`.errors`) | 422 |
| `RateLimitError` | 429 |
| `HellioError` | other |

```python
from hellio import Hellio, InsufficientBalanceError

client = Hellio(token="your-token-here")

try:
    client.sms("233241234567", "Hi")
except InsufficientBalanceError:
    ...  # top up
```

`verify()` is a convenience wrapper: it returns `False` on a 422 validation
error (invalid code) instead of raising.

Rate limit: **120 requests/minute** per token.

## Testing against the SDK
The client accepts an injected `httpx.Client`, so you can mock the transport in
your own tests (for example with [respx](https://lundberg.github.io/respx/)):
```python
import httpx
from hellio import Hellio

client = Hellio(token="test", http_client=httpx.Client(base_url="https://api.helliomessaging.com/v1/"))
```

## License
MIT
