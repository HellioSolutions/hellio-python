# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-07-07

### Added
- USSD apps now have **test** and **live** modes. `create_app` responses expose
  `id` (UUID string), `mode`, `test_secret` (`ussk_test_`), `live_secret`
  (`ussk_live_`), `is_live`, and `active` in place of the single `secret`.
- `client.ussd.set_mode(app_id, mode)` to switch an app between `test` and
  `live`, and `client.ussd.rotate_secret(app_id, mode)` to rotate the secret for
  a mode.
- `ExtensionRequiredError` (402, `extension_required`), raised when switching an
  app to live mode before an extension has been purchased.

### Changed
- App and extension ids are UUID strings; every id parameter (`update_app`,
  `delete_app`, `rent_extension`'s `app_id`, `release_extension`, `session`, and
  the new methods) is now typed `str`.
- `simulate` now takes the app to target: `simulate(app_id, session_id, msisdn,
  input="", new_session=False, service_code=None)`. `service_code` is optional
  and defaults to the shared short code server-side. Simulation always runs in
  the sandbox (test mode); an app you do not own returns 422 `unknown_app`.
- Renting an extension draws from the dedicated USSD balance; on insufficient
  funds it now returns 402 `insufficient_ussd_balance` (mapped to
  `InsufficientBalanceError`).
- Error mapping now honours the response `error` slug, so 402 responses resolve
  to `InsufficientBalanceError` or `ExtensionRequiredError` as appropriate.

## [1.1.0] - 2026-07-07

### Added
- USSD support via the `client.ussd` namespace: `pricing`, `availability`,
  `apps`, `create_app`, `update_app`, `delete_app`, `extensions`,
  `rent_extension`, `release_extension`, `sessions`, `session`, and `simulate`.
- `ConflictError` (409), raised when renting an extension that is no longer
  available (`extension_unavailable`).

### Changed
- Error messages now fall back to the response body's `error` field when no
  `message` is present.

## [1.0.0] - 2026-07-05

### Added
- Initial release of the official Hellio Messaging Python SDK.
- `Hellio` client with Bearer-token auth, configurable base URL and timeout,
  and environment-variable fallbacks (`HELLIO_API_TOKEN`, `HELLIO_BASE_URL`,
  `HELLIO_DEFAULT_SENDER`).
- Methods: `balance`, `pricing`, `sms`, `message`, `campaign`, `otp`,
  `verify_otp`, `verify`, `voice`, `voice_status`, `lookup`, `lookups`,
  `lookup_result`, `verify_email`, `webhooks`, `create_webhook`,
  `delete_webhook`.
- Recipient normalization (string, comma-separated string, or list).
- Typed exception hierarchy mapped by HTTP status: `HellioError`,
  `InvalidApiTokenError` (401), `InsufficientBalanceError` (402),
  `ValidationError` (422), `RateLimitError` (429).
- Injectable `httpx.Client` for testing.
- Full type hints and a `py.typed` marker.
